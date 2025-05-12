from bs4 import BeautifulSoup

def extract_logo(domain: str, html: str) -> str | None:
    try:
        soup = BeautifulSoup(html, "html.parser")
        img = (
            soup.find("img", alt=lambda v: v and "logo" in v.lower()) or
            soup.find("img", class_=lambda v: v and "logo" in v.lower()) or
            soup.find("img", id=lambda v: v and "logo" in v.lower())
        )
        if img and img.get("src"):
            return urljoin(f"{domain}", img["src"])
    except:
        print(f"Error parsing HTMl on domain {domain}.")
    return None
