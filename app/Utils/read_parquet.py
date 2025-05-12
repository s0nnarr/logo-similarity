import pandas as pd
import socket

def get_links(path):
    domains = pd.read_parquet(path)["domain"].dropna().tolist()
    # links = ["http://" + domain for domain in domains]
    links = []

    for domain in domains:
        try:
            resolved_ip = socket.gethostbyname(domain)
            links.append({"domain": domain, "resolved_ip": resolved_ip})
        except socket.gaierror:
            print("Error resolving DNS.")
            continue
        
    return links


