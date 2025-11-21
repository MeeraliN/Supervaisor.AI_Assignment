import requests, json, concurrent.futures
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

Image.MAX_IMAGE_PIXELS = None

def fetch_dim(url):
    """Worker function to get size of one image"""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            w, h = Image.open(BytesIO(r.content)).size
            return url, f"{w}x{h}"
    except: pass
    return url, "N/A"

def collect_urls(data, url_set):
    """Finds all image URLs recursively"""
    if isinstance(data, list): 
        for x in data: collect_urls(x, url_set)
    elif isinstance(data, dict):
        for v in data.values():
            collect_urls(v, url_set)
            if isinstance(v, str) and "http" in v and ("image" in v or "assets" in v):
                url_set.add(v)

def inject_data(data, cache):
    """Rebuilds JSON using cached dimensions"""
    if isinstance(data, list): return [inject_data(x, cache) for x in data]
    if isinstance(data, dict):
        new_d = {}
        for k, v in data.items():
            new_d[k] = inject_data(v, cache)
            if isinstance(v, str) and v in cache:
                new_d[f"dimension of {k}"] = cache[v]
        return new_d
    return data

print("Processing Myntra...")

try:
    # 1. Scrape Main JSON
    html = requests.get("https://www.myntra.com/shoes", headers={"User-Agent": "Mozilla/5.0"}).text
    script = [s.text for s in BeautifulSoup(html, 'html.parser').find_all('script') if 'window.__myx =' in s.text][0]
    raw_data = json.loads(script.split("window.__myx =", 1)[1].strip().rstrip(";"))
    products = raw_data.get('searchData', {}).get('results', {}).get('products', [])

    # 2. Gather all URLs
    all_urls = set()
    collect_urls(products, all_urls)

    # 3. Download Dimensions in Parallel (FAST)
    dim_cache = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        results = executor.map(fetch_dim, all_urls)
        dim_cache = dict(results)

    # 4. Create Final JSON
    final_data = inject_data(products, dim_cache)
    
    with open("Myntra.json", "w") as f:
        json.dump(final_data, f, indent=4)

    print("Done. Myntra.json created.")

except Exception as e:
    print(f"Error: {e}")
