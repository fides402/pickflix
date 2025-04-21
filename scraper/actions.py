import requests
import json
import re

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def fetch_rottentomatoes(url, content_type):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Errore nel fetch {content_type}: {response.status_code}")
        return []

    items = response.json().get("results", [])
    result = []

    for item in items:
        title = item.get("title") or item.get("name")
        if not title:
            continue
        description = item.get("synopsis", "")
        image = item.get("posterImage", {}).get("url", "")
        slug = slugify(title)
        link = f"https://altadefinizionepremium.com/p/{slug}"

        result.append({
            "title": title,
            "description": description,
            "image": image,
            "link": link
        })

    return result

def main():
    data = {
        "films": fetch_rottentomatoes(
            "https://www.rottentomatoes.com/api/private/v2.0/browse?minTomato=0&maxTomato=100&services=all&genres=1&sortBy=most-popular&type=movie",
            "films"
        ),
        "series": fetch_rottentomatoes(
            "https://www.rottentomatoes.com/api/private/v2.0/browse?minTomato=0&maxTomato=100&services=all&genres=1&sortBy=most-popular&type=tv",
            "series"
        )
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Scraping completato: {len(data['films'])} film, {len(data['series'])} serie")

if __name__ == "__main__":
    main()
