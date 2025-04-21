import requests
import csv
import re

API_KEY = "YOUR_TMDB_API_KEY"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def search_tmdb(title):
    params = {
        "api_key": API_KEY,
        "query": title,
        "language": "it-IT"
    }
    response = requests.get(f"{BASE_URL}/search/multi", params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            return results[0].get("poster_path")
    return None

def load_staff_picks(filepath):
    picks = []
    with open(filepath, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            title = row["Title"].strip()
            rating = row["Rating"].strip()
            poster_path = search_tmdb(title)
            image_url = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Image"
            picks.append({
                "title": title,
                "rating": rating,
                "image": image_url,
                "link": f"https://altadefinizionepremium.com/p/{slugify(title)}"
            })
    return picks
