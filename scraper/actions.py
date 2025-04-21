import json
import re
import requests

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def fetch_tmdb(endpoint, type_label):
    url = f"{BASE_URL}/trending/{endpoint}/week"
    params = {
        "api_key": API_KEY,
        "language": LANG
    }

    print(f"📡 Fetching {type_label}...")

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"⚠️ Errore {type_label.upper()}: {response.status_code}")
        return []

    results = response.json().get("results", [])
    items = []

    for r in results:
        title = r.get("title") or r.get("name")
        if not title:
            continue
        description = r.get("overview", "")
        poster_path = r.get("poster_path")
        image = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        slug = slugify(title)
        link = f"https://altadefinizionepremium.com/p/{slug}"

        items.append({
            "title": title,
            "description": description,
            "image": image,
            "link": link
        })

    return items

def main():
    data = {
        "films": fetch_tmdb("movie", "films"),
        "series": fetch_tmdb("tv", "series")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Scraping completato: {len(data['films'])} film, {len(data['series'])} serie")

if __name__ == "__main__":
    main()
