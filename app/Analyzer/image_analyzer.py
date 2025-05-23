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
from config import OUTPUT_PATH



class ImageAnalyzer:
    """
    Main class for a logo analyzer.
    This groups logos by similarities, using traditional computer vision algorithms.
    """
    
    def __init__(self, input_dir: str = ".", threshold: float = 0.75, output_dir: str = OUTPUT_PATH):
        """
        Params:
            input_dir: Location where the images have been downloaded by the scraper.
            threshold: The threshold that considers logos similar. (0.0 to 1.0)

            Note: the higher the threshold (closer to 1.0), the more strict the similarity check is. 
            0.60-0.75 by default is fairly balanced.
        """

        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.threshold = threshold
        self.logos = [] # (path, features)
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
    
        print(f"Found {len(logo_files)} potential logos.")
        return logo_files
    
    
    def extract_features(self, img_path: str) -> Dict[str, Any]:
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
                    # Checking for an ellipse / circular shape. 
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
    
    def json_save(self, result, output_path="."):
        """
        Saves clustering results to .json 
        """
        output_file = "logo_similarity_groups.json"
        file_path = os.path.join(output_path, output_file)

        with open(file_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Results saved to {file_path}.")


    def calculate_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """
        Calculates similarity between two feature dictionaries.
        """

        if not features1 or not features2:
            return 0.0
        
        similarities = []
        color_sim = cv2.compareHist(features1["color_hist"], features2["color_hist"], cv2.HISTCMP_CORREL)
        similarities.append(max(0, color_sim))

        # We append max(0, sim) to ensure there are no negative values.

        grayscale_sim = cv2.compareHist(features1["gray_hist"], features2["gray_hist"], cv2.HISTCMP_CORREL)
        similarities.append(max(0, grayscale_sim))

        shape_features1 = [features1["avg_area"], features1["avg_perimeter"], features1["avg_circularity"]]
        shape_features2 = [features2["avg_area"], features2["avg_perimeter"], features2["avg_circularity"]]

        if max(shape_features1 + shape_features2) > 0:
            max_val = max(shape_features1 + shape_features2)
            shape_features1 = [f / max_val for f in shape_features1]
            shape_features2 = [f / max_val for f in shape_features2]

            shape_sim = 1 - np.linalg.norm(np.array(shape_features1) - np.array(shape_features2)) / np.sqrt(len(shape_features1))
            similarities.append(max(0, shape_sim))

        hu_sim = 1 - np.linalg.norm(features1["hu_moments"] - features2["hu_moments"]) / np.sqrt(len(features1["hu_moments"]))
        similarities.append(max(0, hu_sim))

        aspect_diff = abs(features1["aspect_ratio"] - features2["aspect_ratio"])
        aspect_sim = 1 / (1 + aspect_diff)
        similarities.append(aspect_sim)

        fill_diff = abs(features1["fill_ratio"] - features2["fill_ratio"])
        fill_sim = 1 - fill_diff 
        similarities.append(max(0, fill_sim))

        line_count_diff = abs(features1["num_lines"] - features2["num_lines"])
        line_count_sim = 1 / (1 + line_count_diff * 0.1)
        similarities.append(line_count_sim)

        color_diff = np.linalg.norm(features1["avg_color"] - features2["avg_color"])
        color_avg_sim = 1 / (1 + color_diff / 255) # Normalize by using max color value 
        similarities.append(color_avg_sim)

        weights = [
            0.25, # Color histogram
            0.15, # Grayscale histogram
            0.15, # Shapes (perimeter, area, circularity)
            0.15, # Number of lines
            0.1,  # Hu moments
            0.05, # Aspect ratio
            0.05, # Fill ratio
            0.1,  # Average color.
        ]

        # Prioritizing color, histograms and shapes.
        weighted_sim = sum(w * s for w, s in zip(weights, similarities))
        return min(1.0, max(0.0, weighted_sim))

    def build_sim_matrix(self) -> np.ndarray:
        """
        Builds a similarity matrix for all logos. 
        """
        n = len(self.logos)
        similarity_matrix = np.zeros((n, n))
        print(f"Building similarity matrix for {n} logos ...")
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    sim = self.calculate_similarity(self.logos[i][1], self.logos[j][1])
                    similarity_matrix[i][j] = sim 
                    similarity_matrix[j][i] = sim

        return similarity_matrix
    
    def lookup_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates simplified features for fast pre-filtering.
        """

        return {
            "aspect_ratio_bucket": round(features["aspect_ratio"] * 4) / 4, # Nearest 0.25
            "fill_ratio_bucket": round(features["fill_ratio"] * 10) / 10, # Nearest 0.1
            "avg_color_bucket": tuple(round(c / 32) * 32 for c in features["avg_color"]), # Colors
            "num_lines_bucket": min(features["num_lines"] // 5, 10), # Line count buckets
            "dominant_color": np.argmax(features["color_hist"]), # Dominant color in hist.
            "shape_signature": (
                round(features["avg_circularity"] * 4) / 4, "large" if features["max_area"] > 1000 else "small"
            )
        }
    
    def quick_filter(self, target_features: Dict[str, Any], candidates_indices: List[int], tolerance: Dict[str, float] = None) -> List[int]:
        """
        Pre-filtering based on simple features before expensive similarity calculation.
        """

        if tolerance is None:
            tolerance = {
                "aspect_ratio": 0.5,
                "fill_ratio": 0.3,
                "color_distance": 100,
                "line_count": 10
            }

        target_lookup = self.lookup_features(target_features)
        filtered_candidates = []

        for i in candidates_indices:
            candidate_features = self.logos[i][1]
            candidate_lookup = self.lookup_features(candidate_features)

            # Quick checks
            if abs(candidate_lookup["aspect_ratio_bucket"] - target_lookup["aspect_ratio_bucket"]) > tolerance["aspect_ratio"]:
                continue 
            if abs(candidate_lookup["fill_ratio_bucket"] - target_lookup["fill_ratio_bucket"]) > tolerance["fill_ratio"]:
                continue 
            if np.linalg.norm(np.array(candidate_lookup["avg_color_bucket"]) - np.array(target_lookup["avg_color_bucket"])) > tolerance["color_distance"]:
                continue 
            if abs(candidate_lookup["num_lines_bucket"] - target_lookup["num_lines_bucket"]) > tolerance["line_count"]:
                continue

            filtered_candidates.append(i)
        return filtered_candidates
    
    def group_similar_logos(self) -> List[List[int]]:
        """
        Grouping algorithm for logos. Groups by similarity.

        Hash pre-filtering -> Feature pre-filtering -> Full comparison.
            
        """
        n = len(self.logos)
        groups = []
        assigned = [False] * n

        for i in range(n):
            if assigned[i]:
                continue 

            current_group = [i]
            assigned[i] = True 
            target_features = self.logos[i][1]

            for j in range(i + 1, n):
                # Checking the rest of unassigned logos
                if assigned[j]:
                    continue 
            
                sim = self.calculate_similarity(target_features, self.logos[j][1])
                if sim >= self.threshold:
                    current_group.append(j)
                    assigned[j] = True
            groups.append(current_group)
        return groups

    def normalize_information(self, groups: List[List[int]]) -> Dict[str, Any]:

        group_info = []
        for i, group in enumerate(groups):
            group_info.append({
                "group_num": i,
                "domains": [os.path.splitext(self.logos[logo][0].name)[0] for logo in group]
            })
        return group_info

    def run_analyzer(self):
        """
        Complete pipeline executor.
        
        """    
        print("Starting logo similarity analysis...")
        logo_files = self.load_files()
        if not logo_files:
            print("No image files found!")
            return 
        
        print("Extracting image features...")
        for img_path in logo_files:
            features = self.extract_features(img_path)
            if features is not None:
                self.logos.append((img_path, features))
        
        groups = self.group_similar_logos()
        self.logo_groups = groups
        grouped_domains = self.normalize_information(self.logo_groups)
        self.json_save(grouped_domains, output_path=self.output_dir)
        


"""
    Potential pipeline:
    Take first image, put it in similarity_array.
    Take second image, compare it with the array.
    Take third image, compare it with the array.

    After enough images, make a mean of the array.
"""


    
