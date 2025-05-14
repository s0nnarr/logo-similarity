from typing import Dict, List, Any
import json
import os

def create_output(resolved_links: List[Dict[str, Any]], output_path=""):

    with open(output_path, "w") as f:
        json.dump(resolved_links, f, indent=2)

