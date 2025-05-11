import pandas as pd


def get_links(path):
    domains = pd.read_parquet(path)["domain"].dropna().tolist()
    links = ["http://" + domain for domain in domains]
    return links

