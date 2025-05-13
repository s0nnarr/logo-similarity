from typing import Dict, List, Any
import json

def create_output(resolved_links: List[Dict[str, Any]], output_path="resolved_links.json"):

    with open(output_path, "w") as f:
        json.dump(resolved_links, f, indent=2)

