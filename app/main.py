from Utils.read_parquet import get_links
from Utils.scrape_html import scrape_html

import asyncio
import httpx
import time

""" Global declarations. """

links = []
results = []

async def main():
    start_time = time.time()

    links = get_links("data/logos.snappy.parquet")


    print("Read links from .parquet.")
    result = await scrape_html(links)
    print("---%s seconds---" % (time.time() - start_time))

    print(result)


if __name__ == '__main__':
    asyncio.run(main())

