from typing import Dict, List, Any


def create_output(resolved_links: List[Dict[str, Any]], output_path="resolved_links.txt"):

    with open(output_path, "w") as f:
        for link in resolved_links:
            f.write(f"{link}\n")
