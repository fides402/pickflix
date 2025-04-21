import json
import re
import requests
from datetime import datetime

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_month_range():
    today = datetime.today()
    start = today.replace(day=1)
    end = today
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

def fetch_tmdb_month(endpoint, date_key, label):
    start_date, end_date = get_month_range()

    url = f"{BASE_URL}/discover/{endpoint}"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 20,
        "with_original_language": "en",
        "page": 1,
        f"{date_key}.gte": start_date,
        f"{date_key}.lte": end_date
    }

    print(f"📡 Fetching {label} ({start_date} → {end_date})...")

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"⚠️ Errore {label.upper()}: {response.status_code}")
        return []

    results = response.json().get("results", [])
    items = []

    for r in results:
        title = r.get("title") or r.get("name")
        vote = r.get("vote_average", 0)
        poster = r.get("poster_path")

        if not title or not poster or vote < 7:
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
        "films": fetch_tmdb_month("movie", "primary_release_date", "Film del mese"),
        "series": fetch_tmdb_month("tv", "first_air_date", "Serie del mese")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ data.json aggiornato con FILM e SERIE del mese con voto ≥ 7")

if __name__ == "__main__":
    main()
