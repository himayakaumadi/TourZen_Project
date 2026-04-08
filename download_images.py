import os
import requests

PLACES = {
    "dambulla.png": "Dambulla_cave_temple",
    "nuwara_eliya.png": "Nuwara_Eliya",
    "arugam_bay.png": "Arugam_Bay",
    "minneriya.png": "Minneriya_National_Park",
    "polonnaruwa.png": "Polonnaruwa",
    "adams_peak.png": "Adam's_Peak",
    "unawatuna.png": "Unawatuna"
}

IMG_DIR = r"c:\Users\DELL\Downloads\tourzen_app\static\images"
HEADERS = {'User-Agent': 'TourZenScript/1.0 (contact@tourzen.local)'}

def fetch_wiki_image(title, filename):
    url = f"https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=pageimages&format=json&pithumbsize=1000"
    try:
        res = requests.get(url, headers=HEADERS).json()
        pages = res.get('query', {}).get('pages', {})
        for page_id, page_info in pages.items():
            if 'thumbnail' in page_info:
                img_url = page_info['thumbnail']['source']
                print(f"Downloading {title} from {img_url}")
                img_data = requests.get(img_url, headers=HEADERS, timeout=10).content
                filepath = os.path.join(IMG_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                return True
        print(f"Failed to find thumbnail for {title}")
        return False
    except Exception as e:
        print(f"Error fetching {title}: {e}")
        return False

for filename, title in PLACES.items():
    fetch_wiki_image(title, filename)
