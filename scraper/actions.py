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

def fetch_discover(endpoint, date_key, start_date, end_date, label, min_vote=6.5):
    url = f"{BASE_URL}/discover/{endpoint}"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 20,
        "with_original_language": "en",
        f"{date_key}.gte": start_date,
        f"{date_key}.lte": end_date
    }

    print(f"📡 Fetching {label} ({start_date} – {end_date})...")
    res = requests.get(url, params=params)
    if res.status_code != 200:
        print(f"⚠️ Errore: {res.status_code}")
        return []

    return parse_results(res.json().get("results", []), min_vote)

def fetch_now(endpoint, label, min_vote=6.5):
    url = f"{BASE_URL}/{endpoint}"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "page": 1
    }

    print(f"📡 Fetching {label}...")
    res = requests.get(url, params=params)
    if res.status_code != 200:
        print(f"⚠️ Errore: {res.status_code}")
        return []

    return parse_results(res.json().get("results", []), min_vote)

def parse_results(results, min_vote):
    items = []
    for r in results:
        title = r.get("title") or r.get("name")
        vote = r.get("vote_average", 0)
        poster = r.get("poster_path")
        if not title or not poster or vote < min_vote:
            continue
        items.append({
            "title": title,
            "image": f"https://image.tmdb.org/t/p/w500{poster}",
            "link": f"https://altadefinizionepremium.com/p/{slugify(title)}",
            "rating": str(round(vote, 1))
        })
    return items

def main():
    month_start, month_end = get_month_range()
    year_start, year_end = get_last_year_range()

    data = {
        "films": fetch_discover("movie", "primary_release_date", month_start, month_end, "Film del mese"),
        "series": fetch_discover("tv", "first_air_date", month_start, month_end, "Serie del mese"),
        "top_year": fetch_discover("movie", "primary_release_date", year_start, year_end, "Top dell’anno", min_vote=7.5),
        "now_playing": fetch_now("movie/now_playing", "Film ora al cinema"),
        "on_air": fetch_now("tv/on_the_air", "Serie ora in onda")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ data.json aggiornato con tutte le categorie")

if __name__ == "__main__":
    main()
