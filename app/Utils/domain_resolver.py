import asyncio
import socket
import aiodns
from typing import List, Dict, Any

async def resolve_domain(domain: str) -> Dict[str, Any]:
    resolver = aiodns.DNSResolver()

    try:
        res = await resolver.gethostbyname(domain, socket.AF_INET)
        return {"domain": domain, "resolved_ip": res.addresses[0] if res.addresses else None}
    except Exception as e:
        print(f"Failed to resolve: {domain}. {e}")
        return {"domain": domain, "resolved_ip": None}
    
async def resolve_all_domains(domains: List[str]) -> List[Dict[str, Any]]:
    """
    Resolving DNS to IPv4 for faster scraping.
    
    Args:
        domains: List with unresolved domains.

    Return:
        res: List with IPv4 resolved domains.

    """
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

        # We'll handle any exceptions in the results.
        processed_results = []
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"Err in batch: {str(result)}")
                continue 
            processed_results.append(result)
        batch_results.extend(processed_results)
        await asyncio.sleep(1)

    resolved_ips = [r for r in batch_results if r["resolved_ip"] is not None] 
    # At this point we've returned the successful resolve of domains.
    return resolved_ips