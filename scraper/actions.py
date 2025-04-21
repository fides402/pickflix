import json
import re
import requests
from datetime import datetime

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_date_range():
    now = datetime.now()
    start_date = now.replace(day=1).strftime("%Y-%m-%d")
    if now.month == 12:
        end_date = now.replace(year=now.year + 1, month=1, day=1).strftime("%Y-%m-%d")
    else:
        end_date = now.replace(month=now.month + 1, day=1).strftime("%Y-%m-%d")
    return start_date, end_date

def fetch_tmdb(endpoint, type_label, date_key):
    start_date, end_date = get_date_range()
    url = f"{BASE_URL}/discover/{endpoint}"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 50,
        "page": 1,
        f"{date_key}.gte": start_date,
        f"{date_key}.lt": end_date,
        "with_original_language": "en"
    }

    print(f"📡 Fetching {type_label} usciti tra {start_date} e {end_date}...")

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"⚠️ Errore {type_label.upper()}: {response.status_code}")
        return []

    results = response.json().get("results", [])
    items = []

    for r in results[:20]:
        title = r.get("title") or r.get("name")
        if not title:
            continue
        description = r.get("overview", "")
        poster_path = r.get("poster_path")
        image = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        slug = slugify(title)
        link = f"https://altadefinizionepremium.com/p/{slug}"
        rating = round(r.get("vote_average", 0), 1)

        items.append({
            "title": title,
            "description": description,
            "image": image,
            "link": link,
            "rating": str(rating)
        })

    return items

def main():
    data = {
        "films": fetch_tmdb("movie", "film", "primary_release_date"),
        "series": fetch_tmdb("tv", "serie", "first_air_date")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Scraping completato: {len(data['films'])} film, {len(data['series'])} serie")

if __name__ == "__main__":
    main()
