from bs4 import BeautifulSoup
from typing import Dict, Any, Tuple, List, Optional
from urllib.parse import urljoin, urlparse

import asyncio
import re
import json

from bs4 import BeautifulSoup
from urllib.parse import urljoin
class LogoExtractor:
    def __init__(self):
        self.domains_without_logos = set()
        self.logo_keywords = {
            "logo": 5, "brand": 4, "logotype": 3, 
            "emblem": 2, "trademark": 2, "symbol": 2,
            "site-logo": 4, "site-brand": 3, "site-identity": 2,
            "header-logo": 3, "navbar-brand": 3, "company-logo": 3,
            "main-logo": 3, "brand-logo": 3, "icon": 1
        }
    
        self.blacklisted_keywords = {
            "background": -4, "banner": -2, "hero": -3, "product": -1, 
            "footer": -1, "sample": -2, "carousel": -2, "slide": -1,
            "thumbnail": -2, "avatar": -2, "profile": -1, "photo": -1,
            "gallery": -2, "covert": -2, "teaser": -1, "headline": -1
        }

        self.common_logo_paths = { 
            '/logo.png', '/logo.jpg', '/logo.svg', '/logo.gif', '/logo.webp',
            '/images/logo.png', '/images/logo.jpg', '/images/logo.svg',
            '/assets/logo.png', '/assets/logo.jpg', '/assets/logo.svg',
            '/img/logo.png', '/img/logo.jpg', '/img/logo.svg',
            '/static/logo.png', '/static/logo.jpg', '/static/logo.svg',
            '/wp-content/themes/*/logo.png', '/wp-content/uploads/*/logo.png',
            '/sites/default/files/logo.png'
        }

    def score_text_content(self, domain: str, text: str):
        if not text or not isinstance(text, str):
            return 0
        
        text = text.lower()
        # Confidence score
        conf = 0 

        domain_parts = domain.split(".")
        if len(domain_parts) > 1:
            domain_name = domain_parts[0].lower()
            # Domain name in text
            if domain_name in text and ('logo' in text or 'brand' in text):
                conf += 3
            # Company's name patterns.
            if re.search(r'logo of|\'s logo|logo$', text):
                conf += 2
            # Branded text patterns
            if f"{domain_name} logo" in text or f"{domain_name} brand" in text:
                conf += 4
        if 'site logo' in text or 'company logo' in text or 'brand logo' in text:
            conf += 2

        return conf 
    
    def confidence_url(self, url: str) -> int:
        if not url:
            return 0
        
        url = url.lower()
        conf = 0
        filename = url.split("/")[-1]

        for kw, w in self.logo_keywords.items():
            if kw in filename:
                conf += w
        
        for kw, w in self.blacklisted_keywords.items():
            if kw in filename:
                conf += w
            # Weight is negative, so conf += w actually subtracts that weight.
        # Searching common file patterns.
        if re.search(r"(^|[-_/])logo([-_.]|$)", filename):
            conf += 3
        if re.search(r"(^|[-_/])brand([-_.]|$)", filename):
            conf += 2
        
        # Considering image dimensions.
        if re.search(r"\d+x\d+", filename):
            match = re.search(r"(\d+)x(\d+)", filename)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                if 10 <= width <= 300 and 10 <= height <= 150:
                    conf += 1
                else:
                    conf -= 1 
        
        # Considering file extension.
        if url.endswith('svg'):
            conf += 2
        if url.endswith(('.png', '.webp')):
            conf += 1
        elif url.endswith(('.jpg', '.jpeg')):
            conf -= 0.5
        
        path_parts = urlparse(url).path.split("/")
        for part in path_parts:
            if "logo" in part or "brand" in part:
                conf += 1
            if "header" in part or "nav" in part:
                conf += 1
            if "asset" in part or "image" in part:
                conf += 0.5
   
        if "banner" in url or "hero" in url:
            conf -= 2
        if "footer" in url or "bottom" in url:
            conf -= 1
        
        return conf
    
    def confidence_element(self, tag, soup, domain: str):
        """
            Defines how likely an element is to be a logo.
        """
        conf = 0
        src = None

        for attr in ["class", "id", "name"]:
            if tag.has_attr(attr):
                attr_val = " ".join(tag[attr]) if isinstance(tag[attr], list) else tag[attr]
                attr_val = attr_val.lower()

                for kw, w in self.logo_keywords.items():
                    if kw in attr_val:
                        conf += w
                
                for kw, w in self.blacklisted_keywords.items():
                    if kw in attr_val:
                        conf += w

        if attr in ["alt", "title"]:
            if tag.has_attr(attr):
                text_confidence = self.score_text_content(domain, tag[attr])
                conf += text_confidence
        
        if tag.has_attr("aria-label"):
            aria_text = tag["aria-label"].lower()
            if "logo" in aria_text or "brand" in aria_text:
                conf += 2
                domain_name = domain.split(".")[0].lower()
                if domain_name in aria_text:
                    conf += 2
        
        src = None
        if tag.name == "img":
            for src_attr in ["src", "data-src", "data-original", "data-lazy-src", "data-srcset"]:
                if tag.has_attr(src_attr):
                    src = tag[src_attr]
                    if src_attr != "src":
                        conf += 0.5
                    break

            if src:
                conf += self.confidence_url(src)
        elif tag.name == "svg":
            src = str(tag) # Capture raw SVG
        
        if tag.has_attr("srcset"):
            srcset = tag["srcset"]
            highest_res = ""
            highest_width = 0
            
            for src_item in srcset.split(","):
                parts = src_item.strip().split(" ")
                if len(parts) >= 2:
                    curr_src = parts[0]
                    # Parse the width descriptor
                    width_str = parts[1]
                    try:
                        if width_str.endswith("w"):
                            width_float = float(width_str[:-1])
                            width = int(round(width_float))
                            if width > highest_width and width < 500:
                                # Capping the logo at 500px width
                                highest_width = width 
                                highest_res = curr_src
                    except ValueError as err:
                        print(f"Error parsing srcset width: {err}")
                        pass
            if highest_res:
                src = highest_res
                conf += self.confidence_url(src)
        if tag.has_attr("width") and tag.has_attr("height"):
            try:
                width = int(tag["width"]) if isinstance(tag["width"], str) and tag["width"].isdigit() else 0
                height = int(tag["height"]) if isinstance(tag["height"], str) and tag["height"].isdigit() else 0

                if 20 <= width <= 250 and 20 <= height <= 120:
                    conf += 2
                
                elif 10 <= width <= 400 and 10 <= height <= 200:
                    conf -= 2
                elif width < 10 or height < 10:
                    conf -= 1

                aspect_ratio = width / height if height > 0 else 0
                if 1 <= aspect_ratio <= 4:
                    conf += 1
            except (ValueError, ZeroDivisionError) as err:
                print(f"Error parsing width/height: {err}")
                pass

        # Position in document - usually in the top / header part of the page.
        parents = []
        parent = tag.parent
        while parent and parent.name and len(parents) < 5:
            parents.append(parent)
            parent = parent.parent

        in_header = any(p.name == "header" or 
                        (p.has_attr("class") and any("header" in c.lower() for c in p["class"]))
                        for p in parents)
        
        in_nav = any(p.name == "nav" or 
                    (p.has_attr("class") and any("nav" in c.lower() for c in p["class"]))
                    for p in parents)

        if in_header:
            conf += 3
        if in_nav:
            conf += 2
        
        # Check if the logo links to the homepage:
        link_parent = tag.find_parent("a")
        if link_parent and link_parent.has_attr("href"):
            href = link_parent["href"] 
            if href == "/" or href == f"https://{domain}" or href == f"http://{domain}":
                conf += 3
            elif href.endswith("/") or href.count("/") <= 3:
                conf += 1

        # Position in DOM
        try:
            dom_position = len(list(soup.find_all())) - len(list(tag.find_all()))
            if dom_position < 100:
                conf += 1
        except Exception:
            pass

        return conf, src

    def find_images_in_containers(self, soup, domain: str):
        """
        Finds images withing container elements that have className or ids related to logos.
        """
        results = []
        container_elements = []

        container_selectors = [
            {"class": lambda c: c and any(kw in c.lower() for kw in ["logo", "brand", "identity", "site-id"])},
            {"id": lambda i:i and any(kw in i.lower() for kw in ["logo", "brand", "identity", "site-id"])},
        ]
        for selector in container_selectors:
            container_elements.extend(soup.find_all(**selector))

        # Look for nested images.
        for container in container_elements:
            # Initialize container confidence based on the container attrs
            container_confidence, _ = self.confidence_element(container, soup, domain)
            img_tags = container.find_all("img")
            if img_tags:
                for img in img_tags:
                    img_confidence, src = self.confidence_element(img, soup, domain)
                    total_confidence = img_confidence + container_confidence + 2
                    if src:
                        results.append((total_confidence, src))
            
            for tag in container.find_all(style=True):
                style = tag["style"]
                bg_match = re.search(r'background(-image)?:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
                if bg_match:
                    bg_url = bg_match.group(2)
                    url_confidence = self.confidence_url(bg_url)
                    total_confidence = url_confidence + container_confidence + 2
                    if total_confidence > 0:
                        results.append((total_confidence, bg_url))

            # Check if the container itself contains a bg image.
            if container.has_attr("style"):
                style = container["style"]
                bg_match = re.search(r'background(-image)?:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
                if bg_match:
                    bg_url = bg_match.group(2)
                    url_confidence = self.confidence_url(bg_url)
                    total_confidence = url_confidence + container_confidence + 3
                    if total_confidence > 0:
                        results.append((total_confidence, bg_url))
        return results

    def find_logos_in_anchors(self, soup, domain: str):
        """
        Find logo candidates that likely link to the homepage.
        """
        results = []
        homepage_links = []
        for a_tag in soup.find_all("a"):
            if a_tag.has_attr("href"):
                href = a_tag["href"]
                if href == "/" or href == "#" or href == f"https://{domain}" or href == f"http://{domain}" or href.endswith("/"):
                    homepage_links.append(a_tag)
        for link in homepage_links:
            link_confidence = 0
            if link.has_attr("class"):
                classes = " ".join(link["class"]) if isinstance(link["class"], list) else link["class"]
                if any(kw in classes.lower() for kw in ["logo", "brand"]):
                    link_confidence += 4
            if link.has_attr("id"):
                link_id = link["id"].lower()
                if any(kw in link_id for kw in ["logo", "brand"]):
                    link_confidence += 4
            img_tags = link.find_all("img")
            for img in img_tags:
                img_confidence, src = self.confidence_element(img, soup, domain)
                if src:
                    total_confidence = img_confidence + link_confidence + 2
                    results.append((total_confidence, src))

            svg_tags = link.find_all("svg")
            for svg in svg_tags:
                svg_confidence, src = self.confidence_element(svg, soup, domain)
                if src:
                    total_confidence = svg_confidence + link_confidence + 2
                    results.append((total_confidence, src))

        return results
    
    def find_logos_from_css(self, soup, domain: str):
        """
        Finding logos with common css attributes.
        """
        results = []
        logo_selectors = [
            '.logo', '.site-logo', '.navbar-brand', '.brand-logo', 
            '.header-logo', '#logo', '#site-logo', '#header-logo',
            '.logo-wrapper img', '.brand-wrapper img', '.site-branding img',
            '.site-title img', '.site-identity img', '.logo-container img',
            'header .logo', 'nav .logo', '.masthead .logo',
            '.header-inner .logo', '.navbar .logo', '.site-header .logo'
        ]
        for selector in logo_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    confidence, src = self.confidence_element(element, soup, domain)
                    confidence += 2
                    if src:
                        if element.name == "svg":
                            results.append((confidence, src))
                        elif element.name == "img" and (element.has_attr("src") or element.has_attr("data-src")):
                            img_src = element.get("src") or element.get('data-src', "")
                            results.append((confidence, img_src))
            except Exception as err:
                print(f"Error getting logo from CSS selector: {err}")
        return results

    def extract_logo(self, domain: str, html: str) -> Optional[str]:
        """
            Extracts the most likely logo from a webpage.
            Returns the URL of the logo if something feasible is found.
            
        """

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as err:
            print(f"Error parsing HTML for domain {domain}: {err}")
            return None
        
        candidates = []
        # First priority: Favicons and meta tags.
        def get_icon_size(tag): # "×"
            sizes = tag.get("sizes", "").replace("×", "x").lower()
            match = re.match(r"(\d+)[x](\d+)", sizes)
            
            # More "defensive" approach using regex instead of weird unicode symbol.


            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return 0
            return 0

        try:
            manifest_link = soup.find("link", {"rel": "manifest"})
            if manifest_link and manifest_link.has_attr("href"):
                candidates.append(("manifest", 2, manifest_link["href"]))

            apple_icons = soup.find_all("link", {"rel": lambda r: r and "apple-touch-icon" in r})
            if apple_icons:
                try:
                    for icon in sorted(apple_icons,
                                    key=get_icon_size,
                                    reverse=True):
                        if icon.has_attr("href"):
                            candidates.append(("apple-icon", 5, icon["href"]))
                            break
                except Exception as err:
                    print(f"Error extracting apple_icons on domain {domain}. ERR: {err}")
            favicons = soup.find_all("link", {"rel": lambda r: r and ("icon" in r and "apple" not in r)})
            if favicons:
                try: 
                    for icon in sorted(favicons,
                                        key=get_icon_size,
                                        reverse=True):
                        if icon.has_attr("href"):
                            candidates.append(("favicon", 3, icon["href"]))
                            break
                except Exception as err:
                    print(f"Error extracting favicon on domain {domain}. ERR: {err}")
            ms_image = soup.find("meta", {"name": "msapplication-TileImage"})
            if ms_image and ms_image.has_attr("content"):
                candidates.append(("ms-tile", 3, ms_image["content"]))
            
            og_image = soup.find("meta", {"property": "og:image"})
            if og_image and og_image.has_attr("content"):
                candidates.append(("og-image", 1, og_image["content"]))
       
            twitter_image = soup.find('meta', {'name': 'twitter:image'})
            if twitter_image and twitter_image.has_attr('content'):
                candidates.append(('twitter-image', 1, twitter_image["content"]))
            
            schema_tags = soup.find_all('script', {'type': 'application/ld+json'})
            for tag in schema_tags:
                raw_json = tag.string
                if not raw_json or not raw_json.strip():
                    continue

                try:
                    decoder = json.JSONDecoder()
                    schema_data, _ = decoder.raw_decode(raw_json.strip())
                except (json.decoder.JSONDecodeError, AttributeError) as err:
                    print(f"Error parsing schema data. ERR: {err}")
                    continue
                try:
                        # Check for organization logo
                    if isinstance(schema_data, dict):
                        logo_url = None
                        if 'logo' in schema_data and isinstance(schema_data['logo'], str):
                            logo_url = schema_data['logo']
                        elif 'organization' in schema_data and isinstance(schema_data['organization'], dict) and 'logo' in schema_data['organization']:
                            logo_url = schema_data['organization']['logo']
                        elif '@graph' in schema_data and isinstance(schema_data['@graph'], list):
                            for item in schema_data['@graph']:
                                if isinstance(item, dict) and 'logo' in item:
                                    if isinstance(item['logo'], str):
                                        logo_url = item['logo']
                                        break
                                    elif isinstance(item['logo'], dict) and 'url' in item['logo']:
                                        logo_url = item['logo']['url']
                                        break
                        
                        if logo_url:
                            candidates.append(('schema-logo', 6, logo_url))
                except (json.JSONDecodeError, AttributeError) as err:
                    print(f"Error parsing schema data with json5: {err}")
                    pass
                    
        except Exception as err:
            print(f"Error trying to extract logo on domain {domain} : {err}")
        try:
            svg_tags = soup.find_all("svg")
            for svg in svg_tags:
                confidence, src = self.confidence_element(svg, soup, domain)
                if confidence > 0:
                    candidates.append(("svg", confidence, src))
            
            img_tags = soup.find_all("img")
            for img in img_tags:
                confidence, src = self.confidence_element(img, soup, domain)
                if src and confidence > 0:
                    if "avatar" not in src.lower() and "profile" not in src.lower():
                        candidates.append(("img", confidence, src))
            
            for tag in soup.find_all(style=True):
                style = tag["style"]
                bg_match = re.search(r'background(-image)?:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
                if bg_match:
                    bg_url = bg_match.group(2)
                    url_confidence = self.confidence_url(bg_url)
                    elem_confidence, _ = self.confidence_element(tag, soup, domain)
                    total_confidence = url_confidence + elem_confidence
                    if total_confidence > 0:
                        candidates.append(("bg-image", total_confidence, bg_url))
            # Handling container results.
            try:
                container_results = self.find_images_in_containers(soup, domain)
                if container_results:
                    if isinstance(container_results, list):
                        for item in container_results:
                            try:
                                if isinstance(item, tuple) and len(item) >= 2:
                                    confidence, url = item[0], item[1]
                                    if isinstance(confidence, (int, float)) and isinstance(url, str):
                                        candidates.append(("container-logo", confidence, url))
                            except Exception as err:
                                print(f"Invalid items in container results: {err}")
                    elif isinstance(container_results, tuple) and len(container_results) >= 2:
                        # Single tuple returned.
                        confidence, url = container_results[0], container_results[1]
                        if isinstance(confidence, (int, float)) and isinstance(url, str):
                            candidates.append(("container-logo", confidence, url))
            except Exception as err:
                print(f"Error finding images in containers for {domain}. ERR: {err}")

            # Handling anchor results.
            try:
                anchor_results = self.find_logos_in_anchors(soup, domain)
                if anchor_results:
                    if isinstance(anchor_results, list):
                        for item in anchor_results:
                            try:
                                if isinstance(item, tuple) and len(item) >= 2:
                                    confidence, url = item[0], item[1]
                                    if isinstance(confidence, (int, float)) and isinstance(url, str):
                                        candidates.append(("anchor-logo", confidence, url))
                            except Exception as err:
                                print(f"Invalid images in anchors for {domain}. ERR: {err}")
                    elif isinstance(anchor_results, tuple) and len(anchor_results) >= 2:
                        confidence, url = anchor_results[0], anchor_results[1]
                        if isinstance(confidence, (int, float)) and isinstance(url, str):
                            candidates.append(("anchor-logo", confidence, url))
            except Exception as err:
                print(f"Error finding images in anchors for {domain}. ERR: {err}")
            
            # Handling css results.
            try:
                css_results = self.find_logos_from_css(soup, domain)
                if css_results:
                    if isinstance(css_results, list):
                        for item in css_results:
                            try:
                                if isinstance(item, tuple) and len(item) >= 2:
                                    confidence, url = item[0], item[1]
                                    if isinstance(confidence, (int, float)) and isinstance(url, str):
                                        candidates.append(("css-logo", confidence, url))
                            except Exception as err:
                                print(f"Invalid images in css for {domain}. ERR: {err}")
                    elif isinstance(css_results, tuple) and len(css_results) >= 2:
                        confidence, url = css_results[0], css_results[1]
                        if isinstance(confidence, (int, float)) and isinstance(url, str):
                            candidates.append(("css-logo", confidence, url))
            except Exception as err:
                print(f"Error finding images in css for {domain}. ERR: {err}")
    
            for path in self.common_logo_paths:
                candidates.append(("common-path", 2, path))
        
        except Exception as err:
            print(f"Error getting a img from HTML tags. Domain: {domain}; Err: {err}")

        # Ensure all candidates are properly formatted before sorting.
        valid_candidates = []
        for candidate in candidates:
            try:
                if isinstance(candidate, tuple) and len(candidate) == 3:
                    candidate_type, confidence, src = candidate
                    valid_candidates.append((candidate_type, confidence, src))
                else:
                    print(f"Skipping malformed / corrupt candidate: {candidate}")
            except Exception as err:
                print(f"Error processing candidates. ERR: {err}")
            

        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        for candidate_type, confidence, src in valid_candidates:
            try:
                if src and src.strip():
                    # For SVG, the content is final
                    if candidate_type == "svg" and src.startswith("<svg"):
                        print(f"Found candidate {candidate_type} for {domain} with confidence value {confidence}")
                        return src
                    print(f"Found candidate {candidate_type} for {domain} with confidence value {confidence}")
                    return src
            except Exception as err:
                print(f"Error processing candidate {candidate_type}. ERR: {err}")
        print(f"No logo found for domain {domain}")
        return None


async def extract_site_logo(res_object: Dict[str, Any]):

    """
    Extracts the logo from a website's HTML.

    """
    if not res_object.get("success", False):
        print(f"Skipping {res_object.get("domain", "unknown domain")}")
        return None
    
    extractor = LogoExtractor()
    domain = res_object["domain"]
    html_content = res_object["html"]
    
    try:
        logo_href = await asyncio.to_thread(extractor.extract_logo, domain, html_content)
        if logo_href:
            return {
                "domain": domain,
                "logo_url": logo_href      
            }
        else:
            print(f"[ERR] No logo found on domain: {domain}")
            return None
    except Exception as e:
        print(f"Failed to extract logo from {res_object["domain"]}: {e}")
        return None

# async def extract_batch():
    

#https://www.stanbicbank.co.zw/zimbabwe/personal/ways-to-bank/Online-banking -> deal with sketch style logos.
# add specific href searches that lead to domain's homepage. If href matches the search, then also search any child elements that might have the keywords in the src/class/alt/etc
