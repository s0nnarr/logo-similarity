from urllib.parse import urlparse, urljoin
from PIL import Image 
from io import BytesIO
from typing import List, Dict

import hashlib
import aiohttp
import os

def logo_url_resolution(base_url: str, img_href: str) -> str:
    if img_href.startswith("//"):
        parsed_base_url = urlparse(base_url)
        protocol = parsed_base_url.scheme 
        return f"{protocol}:{img_href}"
    elif img_href.startswith("http://") or img_href.startswith("https://"):
        return img_href
    else:
        # Relative path.
        return urljoin(base_url, img_href)

def get_img_extension(url: str) -> str:
    """ 
        Gets the file extension.
    
    """
    lowercase_url = url.lower()
    if ".jpg" or ".jpeg" in lowercase_url:
        return ".jpg"
    elif ".png" in lowercase_url:
        return ".png"
    elif ".svg" in lowercase_url:
        return ".svg"
    elif ".webp" in lowercase_url:
        return ".webp"
    else:
        return ".png"
    

async def download_img(logo_url: str, output_file_path: str, session: aiohttp.ClientSession, img_size=(64, 64)):
    """
        Logic for downloading an image and resizing it to 64x64 (default) from logo_url.

        Params:
            logo_url: Resolved logo url.
            output_file_path: Path where the file will be saved.

        Returns: 


    """


    try:
        parsed_url = urlparse(logo_url)
        domain = parsed_url.hostname
        extension = get_img_extension(logo_url)
        filename = f"{domain}{extension}"
        file_path = os.path.join(output_file_path, filename)

        async with session.get(logo_url, timeout=10) as res:
            if res.status != 200:
                print(f"Failed to download logo from: {domain} ")
                return None
            
        content = await res.read()

        try:
            img = Image.open(BytesIO(content))
            img = img.convert("RGB")
            img_resized = img.resize(img_size, Image.Resampling.LANCZOS)
            # Resizing to 64x64
            os.makedirs(output_file_path, exist_ok=True) # Move to download_all_img
            img_resized.save(file_path)
            img_hash = hashlib.md5(img_resized).hexdigest()

            return {
                "domain": domain,
                "logo_url": logo_url,
                "size": len(img_resized),
                "img_hash": img_hash
            }
        
        except:
            print(f"Exception saving img: {filename}")
            return False
        
    except:
        print(f"Exception parsing logo url.") 
        return False

async def download_all_images(logo_urls: List[Dict[str, str]]):
    
    print("Downloading all images...")

    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=30) 

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
        ) as client:

        tasks = []

        for pair in logo_urls:
            domain = pair["domain"]
            logo_url = pair["logo_url"]
            # ... Unfinished




        

    