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
import ssl
import random


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

def filename_sanitizer(domain: str) -> str:

    """
    Sanitizing domain name for a safer use.
    """

    if domain.startswith(("https://", "http://")):
        parsed = urlparse(domain)
        domain = parsed.netloc 
    invalid_chars = r'[<>:"/\\|?*\s]'
    sanitized_filename = re.sub(invalid_chars, "_", domain)
    sanitized_filename = sanitized_filename.strip("._")
    if not sanitized_filename:
        sanitized_filename = "unknown"
    if len(sanitized_filename) >= 100:
        sanitized_filename = sanitized_filename[:100]
    return sanitized_filename


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



async def try_alternative_protocols(logo_url: str, domain: str, session: aiohttp.ClientSession, headers: dict):
    """Try both HTTPS and HTTP if one fails"""
    urls_to_try = []
    
    if logo_url.startswith('https://'):
        urls_to_try.append(logo_url)
        urls_to_try.append(logo_url.replace('https://', 'http://'))
    elif logo_url.startswith('http://'):
        urls_to_try.append(logo_url)
        urls_to_try.append(logo_url.replace('http://', 'https://'))
    else:
        urls_to_try.append(logo_url)
    
    for url in urls_to_try:
        try:
            # Try with SSL verification first, then without
            ssl_configs = [True, False]
            
            for ssl_verify in ssl_configs:
                try:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20, connect=8),
                        allow_redirects=True,
                        ssl=ssl_verify
                    ) as res:
                        if res.status == 200:
                            content = await res.read()
                            if is_valid_content(content):
                                return content, url
                        elif res.status in [301, 302, 303, 307, 308]:
                            # Handle redirects manually if needed
                            continue
                except (ssl.SSLError, aiohttp.ClientSSLError):
                            if ssl_verify:
                                continue  # Try without SSL verification
                            else:
                                break  # Both SSL configs failed
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    break  # Try next URL
        except Exception:
            continue
    
    return None, None

async def download_img(logo_href: str, domain: str, session: aiohttp.ClientSession, img_size=(128, 128), output_file_path="", retries=3):
    """
        Image downloader logic.
    """
    sanitized_domain = filename_sanitizer(domain)


    try:
        logo_url = resolve_logo_url(domain, logo_href)
        if not logo_url:
            return None
            
        extension = get_img_extension(logo_url)
        filename = f"{sanitized_domain}{extension}"
        file_path = os.path.join(output_file_path, filename)
        
        # Handle inline SVG
        if "<svg" in logo_url or "</svg" in logo_url:
            try: 
                svg_xml = logo_url
                svg_bytes = svg_xml.encode("utf-8")
                png_bytes = svg_conversion(svg_bytes, img_size)
                img = Image.open(BytesIO(png_bytes))
                img_resized = resize_with_ar(img, img_size)

                filename = f"{sanitized_domain}.png"
                file_path = os.path.join(output_file_path, filename)
                
                os.makedirs(output_file_path, exist_ok=True)
                img_resized.save(file_path)
                
                return {
                    "domain": domain,
                    "logo_url": logo_url,
                    "size": os.path.getsize(file_path),
                }
            except Exception as err:
                print(f"Error processing inline SVG for {domain}: {err}")
                return None

        # Handle data:image URLs
        if logo_url.startswith("data:image"):
            try:
                header, data = logo_url.split(",", 1)
                p_extension = re.search(r"data:image/(\w+)", header)
                extension = p_extension.group(1) if p_extension else "png"

                img_data = None
                if "base64" in header:
                    img_data = base64.b64decode(data)
                else:
                    img_data = urllib.parse.unquote_to_bytes(data)
                
                if img_data is None:
                    return None
                
                filename = f"{sanitized_domain}.{extension}"
                file_path = os.path.join(output_file_path, filename)
                os.makedirs(output_file_path, exist_ok=True)

                if extension.lower() == "svg":
                    png_bytes = svg_conversion(img_data, size=img_size)
                    filename = f"{sanitized_domain}.png"
                    file_path = os.path.join(output_file_path, filename)
                    with open(file_path, "wb") as f:
                        f.write(png_bytes)
                else:
                    img = Image.open(BytesIO(img_data))
                    img_resized = resize_with_ar(img, img_size)

                    if img_resized.mode == "RGBA" and not filename.lower().endswith((".png", ".webp")):
                        filename = f"{sanitized_domain}.png"
                        file_path = os.path.join(output_file_path, filename)
                    img_resized.save(file_path)

                return {
                    "domain": domain,
                    "logo_url": logo_url,
                    "size": os.path.getsize(file_path),
                }
            except Exception as e:
                print(f"Error processing data:image for {domain}: {e}")
                return None
                
        headers = headers_randomizer(domain)
      
        # Try downloading with multiple strategies
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    delay = min(2 ** attempt + random.uniform(0, 1), 10)
                    await asyncio.sleep(delay)
                
                content, final_url = await try_alternative_protocols(logo_url, domain, session, headers)
                
                if content is not None:
                    break
                    
            except Exception as e:
                if attempt == retries:
                    print(f"All attempts failed for {domain}: {e}")
                    return None
                continue
        
        if content is None:
            return None
        
        if not is_valid_content(content):
            return None

        os.makedirs(output_file_path, exist_ok=True)

        try:
            if is_svg_content(content):
                png_bytes = svg_conversion(content, size=img_size)
                file_path = os.path.splitext(file_path)[0] + ".png"
                with open(file_path, "wb") as f:
                    f.write(png_bytes)
            else:
                img = Image.open(BytesIO(content))
                img_resized = resize_with_ar(img, img_size)

                if img_resized.mode == "RGBA" and not file_path.lower().endswith((".png", ".webp")):
                    file_path = os.path.splitext(file_path)[0] + ".png"
                img_resized.save(file_path)

            return {
                "domain": domain,
                "logo_url": final_url or logo_url,
                "size": os.path.getsize(file_path),
            }
        
        except Exception as err:
            print(f"Error processing image for {domain}: {err}")
            return None
            
    except Exception as err:
        print(f"Generic error for {domain}: {err}") 
        return None


async def image_downloader(logo_urls: List[Dict[str, str]], output_file_path=""):
    
    print(f"\nDownloading {len(logo_urls)} images...\n")

    os.makedirs(output_file_path, exist_ok=True)
    batch_size = 100 
    
    connector = aiohttp.TCPConnector(
        limit=15,  
        limit_per_host=3,
        ssl=False, 
        enable_cleanup_closed=True,
        ttl_dns_cache=300,
        use_dns_cache=True,
        keepalive_timeout=30,
        family=0, 
    )
    
    timeout = aiohttp.ClientTimeout(
        total=25,
        connect=8,
        sock_read=10
    ) 

    all_downloaded = []
    failed_count = 0
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        ) as client:

        for i in range(0, len(logo_urls), batch_size):
            batch = logo_urls[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(logo_urls) + batch_size - 1)//batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            tasks = [
                download_img(pair["logo_url"], pair["domain"], client, output_file_path=output_file_path)
                for pair in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            batch_downloaded = []
            batch_failed = 0
            
            for r in batch_results:
                if isinstance(r, Exception):
                    batch_failed += 1
                elif r is not None:
                    batch_downloaded.append(r)
                else:
                    batch_failed += 1
            
            all_downloaded.extend(batch_downloaded)
            failed_count += batch_failed
            
            success_rate = (len(all_downloaded) / (i + len(batch))) * 100
            print(f"Batch {batch_num} completed: {len(batch_downloaded)}/{len(batch)} successful")
            print(f"Overall progress: {len(all_downloaded)}/{i + len(batch)} ({success_rate:.1f}% success rate)")
            
            if success_rate < 20:
                await asyncio.sleep(2)
            elif success_rate < 50:
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.5)


    return all_downloaded