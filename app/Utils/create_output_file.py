from typing import Dict, List, Any


def create_output(resolved_links: List[Dict[str, Any]]):

    with ("resolved_links.txt", "a") as f:
        for link in resolved_links:
            f.write(f"{link}\n")
