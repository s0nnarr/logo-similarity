from urllib.parse import urlparse, urljoin
import urllib.parse
from PIL import Image, ImageOps 
from io import BytesIO
from typing import List, Dict

from Utils.headers import headers_randomizer

import aiohttp
import os
import asyncio
import re
import base64
import logging
import cairosvg


# logging.basicConfig(level=logging.DEBUG)

def resolve_logo_url(base_url: str, img_href: str) -> str:

    """
        Resolved domain logo to absolute downloadable logo url.
    """


    if not img_href or img_href.strip() == '':
        return ""
    
    img_href = img_href.strip().strip('"\'')
    
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url
    
    parsed_base_url = urlparse(base_url)
    domain = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"

    if parsed_base_url.path or parsed_base_url.params or parsed_base_url.query or parsed_base_url.fragment:
        base_url = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"

    if img_href.startswith("data:image/"):
        return img_href

    if img_href.startswith("<svg"):
        return img_href
    
    if img_href.startswith("javascript:") or img_href == "#":
        return ""
    
    if img_href.startswith("//"):
        return f"{parsed_base_url.scheme}:{img_href}"
    if img_href.startswith(("http://", "https://")):
        return img_href

    logo_url = urljoin(domain, img_href)
    parsed_logo_url = urlparse(logo_url)
    
    if not parsed_logo_url.scheme:
        logo_url = f"https://{logo_url}"    

    return logo_url


def get_img_extension(url: str) -> str:
    """ 
        Gets the file extension.
    
    """
    # Check "Content-Types" in res.headers
    url = url.lower()
    if ".jpg" in url or ".jpeg" in url:
        return ".jpg"
    elif ".png" in url:
        return ".png"
    elif ".svg" in url:
        return ".svg"
    elif ".webp" in url:
        return ".webp"

    return ".png"

def resize_with_ar(img: Image.Image, target_size: tuple) -> Image.Image:
    """
    Resizes the image, containing the aspect ratio and handling transparency.
    """
    try:
        if img.mode in ("RGBA", "LA", "P"):
            if img.mode == "P" and "transparency" in img.info:
                img = img.convert("RGBA")
            background_color = (0, 0, 0, 0)
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            background_color = (255, 255, 255)
        resized_img = ImageOps.contain(
            img,
            target_size,
            method=Image.Resampling.LANCZOS
        )
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            final_img = Image.new("RGBA", target_size, background_color)
        else:
            final_img = Image.new("RGB", target_size, background_color)

        x = (target_size[0] - resized_img.width) // 2
        y = (target_size[1] - resized_img.height) // 2

        if resized_img.mode == "RGBA" or "transparency" in resized_img.info:
            final_img.paste(resized_img, (x, y), resized_img)
        else:
            final_img.paste(resized_img, (x, y))

        return final_img
    except Exception as err:
        print(f"Error resizing the image. ERR: {err}")
        return img

def svg_conversion(svg_bytes: bytes, size=(128, 128)) -> bytes :
    """
    Converts SVGs to .PNG.
    SVGs cannot be converted to perceptual hashes.
    """
    
    try:
        png_bytes = cairosvg.svg2png(
            bytestring=svg_bytes,
            output_width=size[0],
            output_height=size[1],
            background_color="white" 
        )
    except Exception as err:
        print(f"Error converting svg to .png. ERR: {err}")

        # Trying without background color.
        try: 
            png_bytes = cairosvg.svg2png(
                bytestring=svg_bytes,
                output_width=size[0],
                output_height=size[1]
            )
        except Exception as err2:
            print(f"Error converting .svg on second try. {err2}")
            raise err2
    
    return png_bytes


def is_svg_content(content: bytes) -> bool:
    if not content:
        return False 
    return b"<svg" in content[:300].lower() and b"xmlns" in content[:300].lower()
    
def is_valid_content(content: bytes) -> bool:
    if len(content) < 10:
        return False 

    return (
            content.startswith(b"\x89PNG") or
            content.startswith(b"\xff\xd8\xff") or
            content.startswith(b"GIF87a") or content.startswith(b"GIF89a") or
            content.startswith(b"RIFF") or 
            content.startswith(b"<svg") or 
            is_svg_content(content)
    )

async def download_img(logo_href: str, domain: str, session: aiohttp.ClientSession, img_size=(128, 128), output_file_path="", retries=2):
    """
        Logic for downloading an image and resizing it to 64x64 (default) from logo_url.

        Params:
            logo_url: Resolved logo url.
            domain: Logo's domain.
            session: Shared TCP session across all img downloads.
            img_size: Image resize values. (default 64x64)
            output_file_path: Path where the file will be saved.

        Returns: 

    """

    try:
        logo_url = resolve_logo_url(domain, logo_href)
        extension = get_img_extension(logo_url)
        filename = f"{domain}{extension}"
        file_path = os.path.join(output_file_path, filename)
        
        if "<svg" in logo_url or "</svg" in logo_url:
            try: 
                svg_xml = logo_url
                svg_bytes = svg_xml.encode("utf-8") # string -> bytes.
                png_bytes = svg_conversion(svg_bytes, img_size)
                img = Image.open(BytesIO(png_bytes))
                img_resized = resize_with_ar(img, img_size)
                filename = f"{domain}.png"
                file_path = os.path.join(output_file_path, filename)
              
                img_resized.save(file_path)
                
                return {
                    "domain": domain,
                    "logo_url": logo_url,
                    "size": os.path.getsize(file_path),
                }
            except Exception as err:
                print(f"Error setting SVG bytes on domain {domain}.")

        # Handling data:image files
        try:
            if logo_url.startswith("data:image"):
                header, data = logo_url.split(",", 1)
                p_extension = re.search(r"data:image/(\w+)", header)
                extension = p_extension.group(1) if p_extension else "png"

                img_data = None
                if "base64" in header:
                    img_data = base64.b64decode(data)

                else:
                    # Handling URL encoded situation.
                    img_data = urllib.parse.unquote_to_bytes(data)
                
                if img_data is None:
                    print(f"Failed to decode data:image for {domain}")
                    return None
                
                filename = f"{domain}.{extension}"
                file_path = os.path.join(output_file_path, filename)
                os.makedirs(output_file_path, exist_ok=True)

                try: 
                    if extension.lower() == "svg":
                        png_bytes = svg_conversion(img_data, size=img_size)
                        filename = f"{domain}.png"
                        file_path = os.path.join(output_file_path, filename)
                        with open(file_path, "wb") as f:
                            f.write(png_bytes)
             
                    else:
                        img = Image.open(BytesIO(img_data))
                        img_resized = resize_with_ar(img, img_size)

                        if img_resized.mode == "RGBA" and not filename.lower().endswith((".png", ".webp")):
                            filename = f"{domain}.png"
                            file_path = os.path.join(output_file_path, filename)
                        img_resized.save(file_path)


                except Exception as err:
                    print(f"Error processing data:image: {err}")
                    with open(file_path, "wb") as f:
                        f.write(img_data)
                        # Save raw data.
                
                return {
                    "domain": domain,
                    "logo_url": logo_url,
                    "size": os.path.getsize(file_path),
                }
            
     
        except Exception as e:
            print(f"Error downloading data:image file: {e}")
        
        headers = headers_randomizer(domain)

        for attempt in range(retries + 1):     
            content = None  
            try:
                print(f"Trying to download: {logo_url}, attempt: {attempt} ")
                if attempt > 0:
                    await asyncio.sleep(1.5 * attempt)

                async with session.get(logo_url, headers=headers, timeout=10, allow_redirects=True) as res:
                    if res.status != 200:
                        print(f"Failed to download logo from: {logo_url}: HTTP Status: {res.status} ")
                        if attempt < retries:
                            continue
                        return None
                    
                    content = await res.read()
                    break

            except (aiohttp.ClientError, aiohttp.ClientConnectionError) as net_err:
                print(f"Network error downloading: {logo_url}: {net_err}")
                if attempt < retries:
                    print("Retrying...")
                    continue
                return None
            
            except asyncio.TimeoutError:
                print(f"Timeout downloading image {logo_url}") 
                if attempt < retries:
                    print("Retrying...")
                    continue
                return None
            
            if content is None:
                return None # all retries failed.
            
            if not is_valid_content(content):
                return None

            os.makedirs(output_file_path, exist_ok=True)

            try:
                if is_svg_content(content):
                    # SVG -> PNG
                    png_bytes = svg_conversion(content, size=img_size)
                    file_path = os.path.splitext(file_path)[0] + ".png"
                    with open(file_path, "wb") as f:
                        f.write(png_bytes)
                    return {
                        "domain": domain,
                        "logo_url": logo_url,
                        "size": os.path.getsize(file_path),
                    }

                else:
                    try:
                        img = Image.open(BytesIO(content))
                        img_resized = resize_with_ar(img, img_size)

                        if img_resized.mode == "RGBA" and not file_path.lower().endswith((".png", ".webp")):
                            file_path = os.path.splitext(file_path)[0] + ".png"
                        img_resized.save(file_path)

                    except Exception as pil_err:
                        print(f"PIL error processing {logo_url}: {pil_err}")
                        return None
                    return {
                        "domain": domain,
                        "logo_url": logo_url,
                        "size": os.path.getsize(file_path),
                    }
            
            
            except Exception as err:
                print(f"Error processing image {logo_url}: {err}")
                return None
            
    except Exception as err:
        print(f"Generic error: {err}") 
        return None
 

async def image_downloader(logo_urls: List[Dict[str, str]], output_file_path=""):
    
    print("\nDownloading all images...\n")

    os.makedirs(output_file_path, exist_ok=True)
    batch_size=500
    
    connector = aiohttp.TCPConnector(
        limit=10,
        ssl=False,
        force_close=True,
        enable_cleanup_closed=True
    )
    timeout = aiohttp.ClientTimeout(
        total=60
    ) 

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        
        ) as client:

        for i in range(0, len(logo_urls), batch_size):
            batch = logo_urls[i:i+batch_size]
            to_download = [
                download_img(pair["logo_url"], pair["domain"], client, output_file_path=output_file_path)
                for pair in batch
            ]
        
        res = await asyncio.gather(*to_download)
        downloaded = [r for r in res if r is not None]
        print(f"Downloaded {len(downloaded)} logos.")

        return downloaded
    

        

    