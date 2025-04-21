import json
import re
import requests
from datetime import datetime

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_current_month_range():
    now = datetime.now()
    start = now.replace(day=1)
    end = now
    return start, end

def is_this_month(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        start, end = get_current_month_range()
        return start <= date <= end
    except:
        return False

def fetch_tmdb(endpoint, type_label):
    start_date, end_date = get_current_month_range()
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    url = f"{BASE_URL}/discover/{endpoint}"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 50,
        "with_original_language": "en",
        "page": 1
    }

    # Applica i filtri corretti per tipo
    if endpoint == "movie":
        params["primary_release_date.gte"] = start_str
        params["primary_release_date.lte"] = end_str
    else:
        params["first_air_date.gte"] = start_str
        params["first_air_date.lte"] = end_str

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

        # Check extra: la data è davvero di questo mese?
        release_date = r.get("primary_release_date") if endpoint == "movie" else r.get("first_air_date")
        if not release_date or not is_this_month(release_date):
            continue

        poster_path = r.get("poster_path")
        if not poster_path:
            continue

        image = f"https://image.tmdb.org/t/p/w500{poster_path}"
        rating = round(r.get("vote_average", 0), 1)
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
        "films": fetch_tmdb("movie", "film"),
        "series": fetch_tmdb("tv", "serie")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ File data.json aggiornato solo con titoli del mese.")

if __name__ == "__main__":
    main()
