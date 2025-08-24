# Logo Similarity Detection 

## Overview

This project provides a robust solution for logo similarity detection using classic computer vision algorithms for the similarity calculation, format support. It is primarily designed for large datasets. Will add image preprocessing for better results (as traditional computer vision algorithms are more sensible to noise and variations). 

The challenge was to avoid machine-learning algorithms (K-means or DBSCAN).

## Installation

1. Clone the repository:
```bash
git clone https://github.com/s0nnarr/logo-similarity.git
cd logo-similarity
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
pip list # Check the installed packages.
```

## Documentation

- Fetches domains from a .parquet file.
- Resolves the fetched domains and stores the resolved IPs in a .json file.
    - (Obsolete in the last version, the initial plan was to pre-resolve the domains for faster execution.)
- Sends a GET request to every domain with both http:// and https:// protocols, having a headless browser as a fallback mechanism. This step expects the website's HTML content.
- Receives the HTML content for each website and parses it using a confidence system to extract potential logo candidates.
- Downloads highest value logo candidates.
- Extracts downloaded logos features. (Color histogram, grayscale histogram, shape features, circularity, average area, average perimeter, average fill ratio, aspect ratio).
- Compares each logo and calculates a similarity score. If the score is above a certain threshold (0.75 by default), then it is added to the group.
- Finally, stores a normalized version of the information inside of a .json file, in Output.


