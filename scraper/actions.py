import json
import re
import requests
from datetime import datetime, timedelta

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

def get_last_year_range():
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    return one_year_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')

def fetch_tmdb_discover(endpoint, date_key, label, date_start, date_end, min_vote=6.5):
    url = f"{BASE_URL}/discover/{endpoint}"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 50,
        "with_original_language": "en",
        "page": 1,
        f"{date_key}.gte": date_start,
        f"{date_key}.lte": date_end
    }

    print(f"📡 Fetching {label} ({date_start} → {date_end})...")

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

        if not title or not poster or vote < min_vote:
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
    start_month, end_month = get_month_range()
    start_year, end_year = get_last_year_range()

    data = {
        "films": fetch_tmdb_discover("movie", "primary_release_date", "Film del mese", start_month, end_month, min_vote=6.5),
        "series": fetch_tmdb_discover("tv", "first_air_date", "Serie del mese", start_month, end_month, min_vote=6.5),
        "top_year": fetch_tmdb_discover("movie", "primary_release_date", "Top dell’anno", start_year, end_year, min_vote=7.5)
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ data.json aggiornato con film/serie del mese e top dell’anno")

if __name__ == "__main__":
    main()
