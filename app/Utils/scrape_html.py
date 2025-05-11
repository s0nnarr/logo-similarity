import asyncio
import httpx 


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

LIMITS = httpx.Limits (
    max_connections=1000,
    max_keepalive_connections=100
)

async def scrape_html(links):    

    """
    Async HTML scraper from a list of links.
    
    Params:
        links: list of links.
    
    Returns:
        List of dictionaries containing each website's response as an object.
    """


    if links:
        print("Links received.")

    async with httpx.AsyncClient(headers=HEADERS, verify=False, follow_redirects=True, limits=LIMITS, timeout=20) as client:

        reqs = [client.get(link, timeout=20) for link in links]
        results = await asyncio.gather(*reqs, return_exceptions=True)

    return results
