# import time
# import os

# from Utils.read_parquet import get_links


# """ Global declarations. """

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PARQUET_PATH = os.path.join(BASE_DIR, "Data\\logos.snappy.parquet")


# links = []
# results = []


# async def main_script():
    
#     """
#     Main script/Orchestrator that starts the program.
#     """

#     start_time = time.time()

#     links = get_links(PARQUET_PATH)

#     print("Read links from .parquet.")
#     # result = await scrape_html(links[:1000])
#     print(links)
#     print("---%s seconds---" % (time.time() - start_time))

#     # print(result)
