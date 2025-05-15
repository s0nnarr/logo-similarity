import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PARQUET_FILENAME = "logos.snappy.parquet"
JSON_FILENAME = "resolved_links.json"

PARQUET_PATH = os.path.join(BASE_DIR, "Data", PARQUET_FILENAME)
OUTPUT_PATH = os.path.join(BASE_DIR, "Output")

IMG_PATH = os.path.join(OUTPUT_PATH, "Images")
JSON_PATH = os.path.join(OUTPUT_PATH, JSON_FILENAME)

