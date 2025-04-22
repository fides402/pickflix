
import json
import re
import requests

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def search_poster_tmdb(title):
    url = f"{BASE_URL}/search/multi"
    params = {
        "api_key": API_KEY,
        "query": title,
        "language": LANG,
        "include_adult": False
    }
    res = requests.get(url, params=params)
    if res.status_code == 200:
        results = res.json().get("results", [])
        if results:
            poster_path = results[0].get("poster_path")
            if poster_path:
                return f"{IMAGE_BASE}{poster_path}"
    return "https://via.placeholder.com/500x750?text=No+Image"

def load_staff_picks(filepath):
    picks = []
    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:
            if "–" not in line:
                continue
            title, rating = line.strip().split("–")
            title = title.strip()
            rating = rating.strip()
            image = search_poster_tmdb(title)
            picks.append({
                "title": title,
                "rating": rating,
                "image": image,
                "link": f"https://altadefinizionepremium.com/p/{slugify(title)}"
            })
    print(f"✅ IMDB Staff Picks caricati: {len(picks)} titoli")
    return picks

def fetch_tmdb(endpoint, label, min_vote=6.5, pages=1, max_items=50):
    items = []
    print(f"📡 Caricamento: {label}...")
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/{endpoint}"
        params = {
            "api_key": API_KEY,
            "language": LANG,
            "page": page
        }
        res = requests.get(url, params=params)
        if res.status_code != 200:
            print(f"⚠️ Errore {label} - Pagina {page}: {res.status_code}")
            continue
        for r in res.json().get("results", []):
            title = r.get("title") or r.get("name")
            vote = r.get("vote_average", 0)
            poster = r.get("poster_path")
            if not title or not poster or vote < min_vote:
                continue
            items.append({
                "title": title,
                "image": f"{IMAGE_BASE}{poster}",
                "link": f"https://altadefinizionepremium.com/p/{slugify(title)}",
                "rating": str(round(vote, 1))
            })
            if len(items) >= max_items:
                break
    return items[:max_items]

def main():
    data = {
        "staff_picks": load_staff_picks("movies_and_ratings.txt"),
        "trending_films": fetch_tmdb("trending/movie/week", "Film trend settimanali"),
        "trending_series": fetch_tmdb("trending/tv/week", "Serie trend settimanali"),
        "now_playing": fetch_tmdb("movie/now_playing", "Film ora al cinema", pages=3),
        "on_air": fetch_tmdb("tv/on_the_air", "Serie ora in onda")
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ File data.json creato con successo!")

if __name__ == "__main__":
    main()
