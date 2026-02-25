import requests
from bs4 import BeautifulSoup
import re
import json

def bing_image_search(query):
    print(f"Searching Bing for: {query}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    url = f"https://www.bing.com/images/search?q={query}&form=HDRSC2&first=1"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Bing stores image info in 'm' attribute of 'adlt' or 'iusc' class elements
        results = []
        for a in soup.find_all("a", class_="iusc"):
            m = a.get("m")
            if m:
                m_data = json.loads(m)
                img_url = m_data.get("murl")
                if img_url:
                    results.append(img_url)
        
        if results:
            for i, r in enumerate(results[:5]):
                print(f"- {i+1}: {r}")
            return results
        else:
            print("- No results found.")
            return []
    except Exception as e:
        print(f"- Error: {e}")
        return []

bing_image_search("naruto official artwork")
