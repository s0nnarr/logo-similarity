from urllib.parse import urlparse, urljoin
from PIL import Image 
from io import BytesIO
from typing import List, Dict

from Utils.scrape_html import headers_randomizer

import hashlib
import aiohttp
import os
import asyncio
import logging
import cairosvg

# common_paths = [
#             '/logo.png', '/logo.jpg', '/logo.svg', '/logo.gif',
#             '/images/logo.png', '/images/logo.jpg', '/images/logo.svg',
#             '/assets/logo.png', '/assets/logo.jpg', '/assets/logo.svg',
#             '/img/logo.png', '/img/logo.jpg', '/img/logo.svg',
#             '/static/logo.png', '/static/logo.jpg', '/static/logo.svg'
#         ]

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
    
    if img_href.startswith("javascript:") or img_href == "#":
        return ""
    
    if img_href.startswith("//"):
        return f"{parsed_base_url.scheme}{img_href}"
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

        headers_content = headers_randomizer(domain)
        headers = {

            "User-Agent": headers_content["User-Agent"],
            "Accept": "image/avif,image/jpeg,image/jpg,image/png,image/apng,image/gif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": headers_content["Accept-Language"],
            "Referer": f"https://{domain}",
            "Connection": "keep-alive"
        }
        
        
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
            

            try:
                img = Image.open(BytesIO(content))
                img = img.convert("RGB")
                img_resized = img.resize(img_size, Image.Resampling.LANCZOS)
                # Resizing to 64x64
                os.makedirs(output_file_path, exist_ok=True) # Move to download_all_img
                img_resized.save(file_path)
                img_hash = hashlib.md5(img_resized.tobytes()).hexdigest()
                # And hashing the resized image for near-duplicate detection.
                
                return {
                    "domain": domain,
                    "logo_url": logo_url,
                    "size": os.path.getsize(file_path),
                    "img_hash": img_hash
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
            to_download.append(download_img(logo_url, domain, client, output_file_path,))
            print("Pair: ", pair)
        
        res = await asyncio.gather(*to_download)
        downloaded = [r for r in res if r is not None]
        print(f"Downloaded {len(downloaded)} logos.")

        return downloaded
    

# if not content.startswith(b'\x89PNG') and not content.startswith(b'\xff\xd8'):
#     print("Response isn't an image.")
#     return None
#  implement? some sites return placeholders with res.status(200)

        

    