import os
from duckduckgo_search import DDGS

def test_search(query):
    print(f"Testing search for: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=5))
            if results:
                for r in results:
                    print(f"- Found: {r.get('image')}")
            else:
                print("- No results found.")
    except Exception as e:
        print(f"- Error: {e}")

test_search("naruto official artwork high quality pinterest")
test_search("naruto")
