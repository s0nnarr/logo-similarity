from Utils.read_parquet import get_links
from Utils.scrape_html import scrape_html
from Scripts import main_script

import os
import asyncio
import httpx
import time

""" Global declarations. """

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_PATH = os.path.join(BASE_DIR, "Data/logos.snappy.parquet")


links = []
results = []


async def main():
    start_time = time.time()

    links = get_links(PARQUET_PATH)

    print("Read links from .parquet.")
    # result = await scrape_html(links[:1000])
    print("---%s seconds---" % (time.time() - start_time))

    # print(result)


if __name__ == '__main__':
    asyncio.run(main())

