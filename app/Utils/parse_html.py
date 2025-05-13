from bs4 import BeautifulSoup
from typing import Dict, Any, List

def extract_logo(domain: str, html: str) -> str | None:
    url = "" # Logo URL

    try:
        soup = BeautifulSoup(html, "html.parser")
        img = (
            soup.find("img", alt=lambda v: v and "logo" in v.lower()) or
            soup.find("img", class_=lambda v: v and "logo" in v.lower()) or
            soup.find("img", id=lambda v: v and "logo" in v.lower())
        )
        if img and img.get("src"):
            return img.get("src") # Returns img href
    except Exception as e:
        print(f"Error parsing HTMl on domain {domain}: {e}.")
    return None

async def extract_site_logo(res_object: Dict[str, Any]):
    if not res_object["success"]:
        return None
    
    domain = res_object["domain"]

    try:
        logo_href = extract_logo(res_object["domain"], res_object["html"])
        if logo_href:
            return {
                "domain": domain,
                "logo_url": logo_href
            }
    except Exception as e:
        print(f"Failed to extract logo from {res_object["domain"]}: {e}")
        return None