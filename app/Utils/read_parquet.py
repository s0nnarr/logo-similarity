import pandas as pd


def get_links(path):
    """
        This fetches the links from a .parquet file.
        Args:
            path: .parquet file path.
    """

    try:
        links = pd.read_parquet(path)["domain"].dropna().tolist()
        res = []

        for link in links:
            if isinstance(link, str) and '.' in link:
                res.append(link)
                # Ensuring domains are valid. 

        return res
    except Exception as e:
        print(f"Error loading links from .parquet file. Error: {e}")
        return []





