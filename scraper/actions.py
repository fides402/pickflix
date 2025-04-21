import json
import re
import requests

API_KEY = "85395f1f04d886e7ad3581f64d886026"
BASE_URL = "https://api.themoviedb.org/3"
LANG = "it-IT"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def fetch_tmdb(endpoint, label, min_vote=6.5, pages=1):
    items = []
    print(f"📡 Fetching {label} ({pages} page(s))...")

    for page in range(1, pages + 1):
        url = f"{BASE_URL}/{endpoint}"
        params = {
            "api_key": API_KEY,
            "language": LANG,
            "page": page
        }

        res = requests.get(url, params=params)
        if res.status_code != 200:
            print(f"⚠️ Errore ({label}, page {page}): {res.status_code}")
            continue

        results = res.json().get("results", [])
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

        if len(items) >= 50:
            break

    return items[:50]

def main():
    data = {
        "trending_films": fetch_tmdb("trending/movie/week", "Film trend settimanali"),
        "trending_series": fetch_tmdb("trending/tv/week", "Serie trend settimanali"),
        "now_playing": fetch_tmdb("movie/now_playing", "Film ora al cinema", pages=3),
        "on_air": fetch_tmdb("tv/on_the_air", "Serie ora in onda")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ File data.json aggiornato con 50 film ora al cinema e altre categorie")

if __name__ == "__main__":
    main()
