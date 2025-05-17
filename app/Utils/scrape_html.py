import asyncio
import httpx 
import multiprocessing
import random
import ssl
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse 
from Utils.headers import headers_randomizer



async def fetch_and_retry(client: httpx.AsyncClient, domain: str, ip: Optional[str], max_retries: int = 3) -> Dict[str, Any]:
    """
    Fetch a single domain with retry logic.
    """
    if not domain.startswith(("http://", "https://")):
        next_link = [f"https://{domain}", f"http://{domain}"]
    else:
        next_link = [domain]
    
    res_object = {
        "domain": domain,
        "success": False,
        "status_code": None,
        "html": None,
        'error': None,
        "url": None
    }
 
    visited_links = set()

    for attempt in range(max_retries):
        for link in list(next_link):
            if link in visited_links:
                continue
                # Skips visited links to avoid redirection loop.
            visited_links.add(link)
            try:
                headers = headers_randomizer(domain)
                parsed_link = urlparse(link)
                domain = parsed_link.netloc or parsed_link.path

                if ip:
                    # Use IP directly if provided.
                    if link.startswith("https://"):
                        modified_link = link
                        headers["Host"] = domain
                    else:
                        modified_link = link.replace(domain, ip)
                        # For HTTP we can use IPv4 directly instead of hostname.
                else:
                    modified_link = link
                
                await asyncio.sleep(random.uniform(0.1, 0.5))
                req = await client.get(
                    modified_link,
                    headers=headers,
                    timeout=20,
                    follow_redirects=True
                )

                if req.status_code == 200:
                    res_object["success"] = True
                    res_object["status_code"] = req.status_code
                    res_object["html"] = req.text
                    res_object["url"] = req.url
                    return res_object
                
                if req.status_code in (301, 302, 307, 308) and "location" in req.headers:
                    redirect_link = req.headers["location"]
                    if redirect_link.startswith("http://", "https://"):
                        next_link.append(redirect_link)

                res_object["status_code"] = req.status_code
            except httpx.ConnectTimeout:
                res_object["error"] = "Connection timeout."
                continue
            except httpx.ConnectError as err:
                print(f"Connection error on domain: {domain}. ERR: {err}")
                res_object["error"] = "Connection error."
            except httpx.HTTPStatusError as err:
                print(f"HTTP status error on domain: {domain}. ERR: {err}")
                res_object["error"] = "HTTP status error"
            except httpx.InvalidURL as err:
                print(f"Invalid URL on domain {domain}. ERR: {err}")
                res_object["error"] = "Invalid URL."
            except httpx.NetworkError as err:
                print(f"Network error on domain {domain}. ERR: {err}")
                res_object["error"] = "Network error"
            except ssl.SSLError as err:
                print(f"SSL error on domain {domain}. ERR: {err}")
                res_object["error"] = "SSL error"
          
                if attempt < max_retries - 1:
                    # Fallback to http if https doesn't succeed.
                    http_url = f"http://{domain}"
                    if link.startswith("https://") and http_url not in visited_links and http_url not in next_link:
                        next_link.append(http_url)
                    await asyncio.sleep((attempt + 1) * 2)
        
            except httpx.ReadTimeout as err:
                print(f"Read timeout error on domain {domain}. ERR: {err}")
            except Exception as err:
                print(f"Unexpected error fetching HTML on domain: {domain}. ERR: {err}")
                res_object["error"] = "Unexpected error fetching HTML."
        if attempt < max_retries - 1:
            await asyncio.sleep((2 ** attempt) & random.uniform(1, 2))
    return res_object

async def create_ssl_context() -> ssl.SSLContext:
    """
    Creates a custom SSL context for a broader server approach.
    """
    context = ssl.create_default_context()

    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.options &= ~ssl.OP_NO_SSLv3
    context.options &= ~ssl.OP_NO_SSLv2
    context.options &= ~ssl.OP_NO_TLSv1_1

    context.minimum_version = ssl.TLSVersion.TLSv1

    # Setting the cipher to include older ones.
    context.set_ciphers("ALL:@SECLEVEL=1")
    return context

async def scrape_html(resolved_links: List[Dict[str, Any]]) -> List[Dict[Any, str]]:    

    """
    Async HTML scraper from a list of links.
    
    Params:
        links: list of resolved domains.
    
    Returns:
        List of dictionaries containing each website's response as an object.
    """
    concurrency = 200 # Changed from 1000
    keepalive = 40 # Changed from 300

    if not resolved_links:
        return []
    
    print(f"Starting scraper. (Concurrency: {concurrency})")
    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=keepalive
    )
    ssl_context = await create_ssl_context()
    transport = httpx.AsyncHTTPTransport(
        verify=ssl_context,
        retries=1
    )
    semaphore = asyncio.Semaphore(concurrency)
    res = []

    async with httpx.AsyncClient(
        transport=transport,
        follow_redirects=True,
        limits=limits,
        timeout=20
    ) as async_client:
        
        async def bounded_fetch(resolved_link_pair: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                domain = resolved_link_pair["domain"]
                resolved_ip = resolved_link_pair["resolved_ip"]
                await asyncio.sleep(random.uniform(0.1, 0.5))
                return await fetch_and_retry(async_client, domain, resolved_ip)
        
        batch_size = 500
        for i in range(0, len(resolved_links), batch_size):
            batch = resolved_links[i:i+batch_size]
            completed_batch = [bounded_fetch(resolved_link_pair) for resolved_link_pair in batch]
            batch_results = await asyncio.gather(*(completed_batch))
            res.extend(batch_results)
            
            await asyncio.sleep(random.uniform(0.1, 0.5))

    return res

            


    


