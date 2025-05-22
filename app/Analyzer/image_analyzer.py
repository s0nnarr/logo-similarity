import os
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from collections import defaultdict
from scipy.spatial.distance import pdist, squareform
from typing import List, Dict, Tuple, Any, Set
from pathlib import Path
import json
import imagehash
import argparse


class ImageAnalyzer:
    """
    Main class for a logo analyzer.
    This groups logos by similarities, using traditional computer vision algorithms.
    """
    
    def __init__(self, input_dir: str = ".", threshold: float = 0.75):
        """
        Params:
            input_dir: Location where the images have been downloaded by the scraper.
            threshold: The threshold that considers logos similar. (0.0 to 1.0)

            Note: the higher the threshold (closer to 1.0), the more strict the similarity check is. 
            0.60-0.75 by default is fairly balanced.
        """

        self.input_dir = Path(input_dir)
        self.threshold = threshold
        self.logos = [] # (path, features) tuples
        self.similarity_graph = None 
        self.logo_groups = []

        self.img_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", 
        }
    
    def load_files(self) -> List[Path]:
        """
        Finds the specified path input_dir and traverses the directory.
        """
        logo_files = []

        for root, _, files in os.walk(self.input_dir):
            for file in files:
                file_path = Path(root) / file 
                if file_path.suffix.lower() in self.img_extensions:
                    logo_files.append(file_path)
    
        print(f"[ImageAnalyzer] Found {len(logo_files)} potential logos.")
        return logo_files
    
    def hash_checker(self, path1, path2, threshold=5):
        # Lower threshold to be more strict.
        hash1 = imagehash.phash(Image.open(path1))
        hash2 = imagehash.phash(Image.open(path2))

        diff = abs(hash1 - hash2)
        return diff <= threshold
    
    def extract_features(self, img_path: Path) -> Dict[str, Any]:
        """
        Extract features from an image, and return them in a dictionary [img_path, img_features].
        """

        try:
            img = cv2.imread(img_path)
            if img is None:
                print(f"Could not read image {img_path}")
                return None 
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Converting to grayscale. This negligates color channels and mostly uses intensity.


            color_hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            color_hist = cv2.normalize(color_hist, color_hist).flatten()

            grayscale_hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
            grayscale_hist = cv2.normalize(grayscale_hist, grayscale_hist).flatten()

            # We'll then detect the edges to understand shape features.
         

            edges = cv2.Canny(gray, 50, 150)

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # Only gets external contours.

            contour_features = []
            for contour in contours:
                if len(contour) >= 5: 
                    # Checking for an ellipse. 
                    # Needs at least 5 points to fit inside an ellipse.
                    area = cv2.contourArea(contour)
                    if area > 50:
                        perimeter = cv2.arcLength(contour, True)
                        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0 # 4pi * A / p^2
                        contour_features.append((area, perimeter, circularity))
            
            avg_area = max_area = avg_perimeter = avg_circularity = 0
            if contour_features:
                areas = [c[0] for c in contour_features]
                perimeters = [c[1] for c in contour_features]
                circularities = [c[2] for c in contour_features]

                avg_area = np.mean(areas)
                max_area = np.max(areas)
                avg_perimeter = np.mean(perimeters)
                avg_circularity = np.mean(circularities)

            # Hough transform to count the number of edges and lines.
            lines = None
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=20, maxLineGap=5)
            num_lines = 0 if lines is None else len(lines)

            # Shape description with image moments
            moments = cv2.moments(gray)
            hu_moments = cv2.HuMoments(moments).flatten()

            # Aspect ratio and area ratio
            height, width = img.shape[:2]
            aspect_ratio = width / height
            filled_area = np.sum(gray > 0)
            total_area = gray.size
            fill_ratio = filled_area / total_area 

            avg_color = np.mean(img, axis=(0, 1))

            return {
                "color_hist": color_hist,
                "gray_hist": grayscale_hist,
                "avg_area": avg_area,
                "max_area": max_area,
                "avg_perimeter": avg_perimeter,
                "avg_circularity": avg_circularity,
                "num_lines": num_lines,
                "hu_moments": hu_moments,
                "aspect_ratio": aspect_ratio,
                "fill_ratio": fill_ratio,
                "avg_color": avg_color
            } 


        except Exception as err:
            print(f"Error extracting image features from {img_path}. ERR: {err}")
            return None
    
    def json_save(self, result, output_file="website_groups.json"):
        """
        Saves clustering results to .json 
        """
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)


    # def calculate_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:


"""
    Potential pipeline:
    Take first image, put it in similarity_array.
    Take second image, compare it with the array.
    Take third image, compare it with the array.

    After enough images, make a mean of the array.
"""


    
