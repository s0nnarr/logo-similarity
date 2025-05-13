import asyncio
import httpx 
import multiprocessing
import random
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse 

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.2420.65 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.57 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-A528B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
]

accept_languages = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "es-ES,es;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7"
]




def headers_randomizer(domain: str) -> Dict[str, str]:
    return {
        "User-Agent" : random.choice(user_agents),
        "Accept-Language": random.choice(accept_languages),
        "Host": domain,
    }

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
    
    for attempt in range(max_retries):
        for link in next_link:
            try:
                parsed_link = urlparse(link)
                domain = parsed_link.netloc or parsed_link.path
                headers = headers_randomizer(domain)

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
                
                req = await client.get(
                    modified_link,
                    headers=headers,
                    timeout=20
                )

                if req.status_code == 200:
                    res_object["success"] = True,
                    res_object["status_code"] = req.status_code,
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

            
            except Exception as e:
                res_object["error"] = "Unexpected error fetching HTML."
        if attempt < max_retries - 1:
            await asyncio.sleep(attempt + 1)
    
    return res_object


async def scrape_html(resolved_links: List[Dict[str, Any]]) -> List[Dict[Any, str]]:    

    """
    Async HTML scraper from a list of links.
    
    Params:
        links: list of resolved domains.
    
    Returns:
        List of dictionaries containing each website's response as an object.
    """
    concurrency = 1000
    keepalive = 100

    if not resolved_links:
        return []
    
    print(f"Starting scraper. (Concurrency: {concurrency})")
    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=keepalive
    )

    semaphore = asyncio.Semaphore(concurrency)
    res = []
   
    async with httpx.AsyncClient(
        verify=False,
        follow_redirects=True,
        limits=limits,
        timeout=20
    ) as async_client:
        
        async def bounded_fetch(resolved_link_pair: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                domain = resolved_link_pair["domain"]
                resolved_ip = resolved_link_pair["resolved_ip"]
                await asyncio.sleep(0.2)
                return await fetch_and_retry(async_client, domain, resolved_ip)
        
        batch_size = 500
        for i in range(0, len(resolved_links), batch_size):
            batch = resolved_links[i:i+batch_size]
            completed_batch = [bounded_fetch(resolved_link_pair) for resolved_link_pair in batch]
            batch_results = await asyncio.gather(*(completed_batch))
            res.extend(batch_results)
            print(f"Finished batch {i} {batch_size}")
            
            await asyncio.sleep(0.4)

    return res

            


    


