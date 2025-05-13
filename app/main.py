import time
import os
import asyncio

from Utils.read_parquet import get_links
from Utils.domain_resolver import resolve_all_domains
from Utils.scrape_html import scrape_html
from Utils.create_output_file import create_output

""" Global declarations. """

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_PATH = os.path.join(BASE_DIR, "Data\\logos.snappy.parquet")
OUTPUT_PATH = os.path.join(BASE_DIR, "Output\\resolved_links.txt")

links = []
resolved_ips = []

async def main():
    
    """
    Main script/Orchestrator that starts the program.
    """

    start_time = time.time()
    domains = get_links(PARQUET_PATH)
    print("Length of domains: ")
    print(len(domains))
    resolved_ips = await resolve_all_domains(domains)
    counter = 1
  
    if resolved_ips:
        print("Resolved IPs loaded.")
        # Locally caching to a file.
        create_output(resolved_ips, OUTPUT_PATH)
        for ip in resolved_ips:
            counter += 1
        print(counter)

    

    html_contents = await scrape_html(resolved_ips)
    # print(html_contents)
    print("---%s seconds---" % (time.time() - start_time))


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(main())
