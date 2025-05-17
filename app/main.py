import time
import os
import asyncio
import json

from Utils.read_parquet import get_links
from Utils.domain_resolver import resolve_all_domains
from Utils.scrape_html import scrape_html
from Utils.outputter import create_output
from Utils.parse_html import extract_site_logo
from Utils.download_images import image_downloader

from config import * # Global declarations.


links = []
resolved_ips = []
domain_logos = []

async def main():
    
    """

    Main script / Orchestrator that starts the program.
    
    """

    start_time = time.time()

    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            resolved_ips = json.load(f) 
            print("Loaded resolved links from .json file.")
            # Fetching already resolved domains.
        f.close()
    else:

        domains = get_links(PARQUET_PATH)
        print("Number of links: ", len(domains))
        resolved_ips = await resolve_all_domains(domains[:200])
        # print(resolved_ips)
    counter = 1
    if resolved_ips:
        create_output(resolved_ips, JSON_PATH)
        for ip in resolved_ips:
            counter += 1
        print(f"Resolved IPs: {counter}")

    # print(resolved_ips[:50])
    # Parse

    html_contents = await scrape_html(resolved_ips)
    for res_object in html_contents:
        if res_object["success"] == False:
            print(f"{res_object["domain"]}\n")
    print(f"Length of html_contents: {len(html_contents)}")

    # logo_tasks = [extract_site_logo(res_object) for res_object in html_contents]
    # logo_results = await asyncio.gather(*(logo_tasks))

    # domain_logos = [result for result in logo_results if result is not None]  


    # print("Found: ", domain_logos)
    print("\n=== SUMMARY ===")
    print(f"Resolved: {len(resolved_ips)}")
    print(f"Scraped: {len(html_contents)}")
    print(f"Logos Found: {len(domain_logos)}")
    # downloaded_logos = await image_downloader(domain_logos, IMG_PATH)
    print("---%s seconds---" % (time.time() - start_time))


if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(main())
