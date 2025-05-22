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
        # Handle
    
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
    return ImageOps(img, target_size, method=Image.Resampling.LANCZOS, color=(0,0,0,0) if img.mode == "RGBA" else (255, 255, 255))

def svg_conversion(svg_bytes: bytes, size=(64,64)) -> Image.Image :
    """
    Converts SVGs to .PNG.
    SVGs cannot be converted to perceptual hashes.
    """
    
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=size[0], output_height=size[1])
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    return img


async def download_img(logo_href: str, domain: str, session: aiohttp.ClientSession, img_size=(64, 64), output_file_path="", retries=2):
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
        filename = f"{domain.replace('.', '_')}{extension}"
        file_path = os.path.join(output_file_path, filename)

        print("Domain: ", domain)

        headers = headers_randomizer(domain)
        
        # Handling data:image files
        try:
            if logo_url.startswith("data:image"):
                header, data = logo_url.split(",", 1)
                p_extension = re.search(r"data:image/(\w+)", header)
                extension = p_extension.group(1) if p_extension else "png"

                if "base64" in header:
                    img_data = base64.b64decode(data)

                else:
                    # Handling URL encoded situation.
                    img_data = urllib.parse.unquote_to_bytes(data)
                
                filename = f"{domain}.{extension}"
                file_path = os.path.join(output_file_path, filename)

                with open(file_path, "wb") as f:
                    f.write(img_data)
                return {
                    "domain": domain,
                    "logo_url": logo_url,
                    "size": os.path.getsize(file_path),
                }

        except Exception as e:
            print(f"Error downloading data:image file: {e}")
        
        for attempt in range(retries + 1):       
            try:
                print(f"Trying to download: {logo_url}, attempt: {attempt} ")
                if attempt > 0:
                    await asyncio.sleep(1.5 * attempt)

                async with session.get(logo_url, headers=headers, timeout=10, allow_redirects=True) as res:
                    if res.status != 200:
                        print(f"Failed to download logo from: {domain}: HTTP Status: {res.status} ")
                        if attempt < retries:
                            continue
                        return None
                    
                    if res.status == 200: 
                        content = await res.read()

            except (aiohttp.ClientError, aiohttp.ClientConnectionError) as net_err:
                print(f"Network error downloading: {logo_url}: {net_err}")
                if attempt < retries:
                    print("Retrying...")
                    continue
                return None
            
            except aiohttp.Timeout:
                print(f"Timeout downloading image {logo_url}") 
                if attempt < retries:
                    print("Retrying...")
                    continue
                return None
            
            if 'content' not in locals():
                return None # all retries failed.
            

            os.makedirs(output_file_path, exist_ok=True)
            try:
                if extension.lower() == ".svg":
                    # SVG -> PNG
                    img = svg_conversion(content, size=img_size)
                    img.save(output_file_path)
                    
                    return {
                        "domain": domain,
                        "logo_url": logo_url,
                        "size": os.path.getsize(file_path),
                    }

                else:
 
                    img = Image.open(BytesIO(content))
                    if img.mode == "RGBA" or (img.mode == "P" and "transparency" in img.info):
                        img_alpha = img.convert("RGBA")
                        img_resized = resize_with_ar(img_alpha, img_size)
                    else:
                        img = img.convert("RGB")
                        img_resized = resize_with_ar(img, img_size)

                    if img_resized.mode == "RGBA" and not file_path.lower().endswith((".png", ".webp")):
                        file_path = os.path.splitext(file_path)[0] + ".png"

                    img_resized.save(file_path)
                
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
    
    print("Downloading all images...")

    os.makedirs(output_file_path, exist_ok=True)

    connector = aiohttp.TCPConnector(
        limit=10,
        ssl=False,
        force_close=True,
        enable_cleanup_closed=True
    )
    timeout = aiohttp.ClientTimeout(
        total=20
    ) 

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        ) as client:

        to_download = []

        # Implement batch logic => 500 obj per batch.
        for pair in logo_urls:
            domain = pair["domain"]
            logo_url = pair["logo_url"]
            to_download.append(download_img(logo_url, domain, client, output_file_path=output_file_path))
            print("Pair: ", pair)
        
        res = await asyncio.gather(*to_download)
        downloaded = [r for r in res if r is not None]
        print(f"Downloaded {len(downloaded)} logos.")

        return downloaded
    

# if not content.startswith(b'\x89PNG') and not content.startswith(b'\xff\xd8'):
#     print("Response isn't an image.")
#     return None
#  implement? some sites return placeholders with res.status(200)

        

    