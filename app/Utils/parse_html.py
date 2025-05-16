from bs4 import BeautifulSoup
from typing import Dict, Any, List

def extract_logo(domain: str, html: str) -> str | None:
    url = "" # Logo URL
    potential_logo_names = [
        "logo", "icon",
        "brand", "trademark",
        "emblem", "favicon"
    ]

    try:

  
        soup = BeautifulSoup(html, "html.parser")
        img = (
            soup.find("img", alt=lambda v: v and any(name in v.lower() for name in potential_logo_names)) or
            soup.find("img", class_=lambda v: v and any(name in v.lower() for name in potential_logo_names)) or
            soup.find("img", id=lambda v: v and any(name in v.lower() for name in potential_logo_names))
        )
        if img and img.get("src"):
            return img.get("src") # Returns img href
        

        # Doesn't return with 100% confidence.
        svg_list = soup.find_all("svg") 
        for svg in svg_list:
            classes = svg.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            svg_id = svg.get("id", "")
            title_tag = svg.find("title")
            title_text = title_tag.text if title_tag else ""
            text_candidates = classes + [svg_id, title_text]
            candidates = [str(c).lower() for c in text_candidates if c]

            if any(name in candidate for candidate in candidates for name in potential_logo_names):
                return str(svg)
         
        use = soup.find("use", href=True) or soup.find("use", {"xlink:href":True})
        if use:
            href = use.get("href") or use.get("xlink:href")
            if href:
                return href
        
        favicon = soup.find("link", rel=lambda v: v and "logo" in v.lower())
        if favicon and favicon.get("href"):
            return favicon["href"]
        
        meta_tag = soup.find("meta", property="og:image")
        if meta_tag and meta_tag.get("content"):
            return meta_tag["content"]
        
        a_tags = soup.find_all("a")
        for a_tag in a_tags:
            attrs = " ".join([
                " ".join(a_tag.get("class", [])) if isinstance(a_tag.get("class"), list) else a_tag.get("class", "")
            ]).lower()

            if any(name in attrs for name in potential_logo_names):
                img = a_tag.find("img")
                if img and img.get("src"):
                    return img.get("src")
                
                svg = a_tag.find("svg")
                if svg:
                    return str(svg)

    except Exception as e:
        print(f"Error parsing HTML on domain {domain}: {e}.")
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
    
    # common_paths = [
#             '/logo.png', '/logo.jpg', '/logo.svg', '/logo.gif',
#             '/images/logo.png', '/images/logo.jpg', '/images/logo.svg',
#             '/assets/logo.png', '/assets/logo.jpg', '/assets/logo.svg',
#             '/img/logo.png', '/img/logo.jpg', '/img/logo.svg',
#             '/static/logo.png', '/static/logo.jpg', '/static/logo.svg'
#         ]

#https://www.stanbicbank.co.zw/zimbabwe/personal/ways-to-bank/Online-banking -> deal with sketch style logos.
