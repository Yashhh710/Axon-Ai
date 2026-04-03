import cv2
import numpy as np
from PIL import Image
import os
from duckduckgo_search import DDGS

class ImageAnalyzer:
    def __init__(self, image_path):
        self.path = image_path
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")
        
        # Load using both libraries for different capabilities
        self.pil_img = Image.open(image_path)
        self.cv_img = cv2.imread(image_path)

    def get_basic_info(self):
        """Returns metadata like size, format, and mode."""
        return {
            "Filename": os.path.basename(self.path),
            "Dimensions": self.pil_img.size,  # (Width, Height)
            "Format": self.pil_img.format,
            "Color Mode": self.pil_img.mode,
            "Filesize (KB)": round(os.path.getsize(self.path) / 1024, 2)
        }

    def get_color_analysis(self):
        """Calculates average brightness and identifies if it's dark or light."""
        gray = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        status = "Dark" if avg_brightness < 127 else "Bright"
        
        return {
            "Average Brightness": round(avg_brightness, 2),
            "Lighting Quality": status
        }

    def detect_complexity(self):
        """Uses Canny Edge Detection to see how detailed the image is."""
        gray = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_density = (np.sum(edges > 0) / edges.size) * 100
        
        return {
            "Edge Density (%)": round(edge_density, 2),
            "Visual Complexity": "High" if edge_density > 5 else "Low"
        }

    def run_full_analysis(self):
        print(f"\n--- Technical Analysis Report: {os.path.basename(self.path)} ---")
        info = {**self.get_basic_info(), **self.get_color_analysis(), **self.detect_complexity()}
        for key, value in info.items():
            print(f"{key}: {value}")
        return info

def test_search(query):
    print(f"\nTesting search for: {query}")
    try:
        with DDGS() as ddgs:
            results = ddgs.images(keywords=query, max_results=2)
            for r in results:
                img = r.get("image") or r.get("thumbnail")
                print(f"- Found: {img}")
    except Exception as e:
        print(f"- Search Error: {e}")

if __name__ == "__main__":
    # To use the analyzer, provide a valid path
    # test_img = "test.jpg"
    # if os.path.exists(test_img):
    #     analyzer = ImageAnalyzer(test_img)
    #     analyzer.run_full_analysis()
    
    test_search("High resolution neural network concept art")
