import asyncio
import socket
import aiodns
import httpcore
from typing import List, Dict, Any, Tuple
import httpx


async def resolve_domain(domain: str, timeout=10) -> Dict[str, Any]:
    resolver = aiodns.DNSResolver()
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']
    # 8.8.8.8 -> Google DNS
    # 1.1.1.1 -> Cloudflare DNS

    try:
        # res = await resolver.gethostbyname(domain, socket.AF_INET)
        res = await asyncio.wait_for(
            resolver.gethostbyname(domain, socket.AF_INET),
            timeout=timeout
        )
        return {
            "domain": domain,
            "resolved_ip": res.addresses[0] if res.addresses else None,
            "status": "success"
            }
    
    except Exception as e:
        print(f"Failed to resolve: {domain}. {e}")
        return {"domain": domain, "resolved_ip": None}
    
async def resolve_all_domains(domains: List[str]) -> List[Dict[str, Any]]:
    """
    Resolving DNS to IPv4 for faster scraping.
    
    Args:
        domains: List with unresolved domains.

    Return
        res: List with IPv4 resolved domains.

    """
    total_domains = len(domains)
    print(f"Starting resolution for {total_domains}")

    max_concurrent = 100
    semaphore = asyncio.Semaphore(max_concurrent)

    async def resolve_bounded(domain: str) -> Dict[str, Any]:
        async with semaphore:
            return await resolve_domain(domain)

    # We'll process in batches to avoid overwhelming the system.
    batch_size = 500
    results = []
    
    for i in range(0, len(domains), batch_size):
        batch = domains[i:i+batch_size]
        batch_results = await asyncio.gather(
            *(resolve_bounded(domain) for domain in batch),
            return_exceptions=True
        )

        results.extend(batch_results)
        await asyncio.sleep(1)

    resolved_ips = [r for r in results if r["resolved_ip"] is not None] 
    return resolved_ips