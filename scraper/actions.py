import json
import re
import requests

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def fetch_trending(endpoint, label):
    url = f"{BASE_URL}/trending/{endpoint}/week"
    params = {
        "api_key": API_KEY,
        "language": LANG
    }

    print(f"📡 Trending {label}...")

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"⚠️ Errore trending {label}: {response.status_code}")
        return []

    results = response.json().get("results", [])
    items = []

    for r in results:
        title = r.get("title") or r.get("name")
        vote = r.get("vote_average", 0)
        poster = r.get("poster_path")

        if not title or not poster or vote < 6.5:
            continue

        image = f"https://image.tmdb.org/t/p/w500{poster}"
        rating = round(vote, 1)
        slug = slugify(title)
        link = f"https://altadefinizionepremium.com/p/{slug}"

        items.append({
            "title": title,
            "image": image,
            "link": link,
            "rating": str(rating)
        })

    return items

def main():
    data = {
        "films": fetch_trending("movie", "Film"),
        "series": fetch_trending("tv", "Serie TV")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ data.json aggiornato con trending film/serie ≥ 6.5")

if __name__ == "__main__":
    main()
