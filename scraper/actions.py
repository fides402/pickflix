import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://www.imdb.com/it/imdbpicks/staff-picks/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def is_series(title, description):
    keywords = ['episodi', 'stagione', 'serie']
    return any(k in description.lower() or k in title.lower() for k in keywords)

def scrape():
    r = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(r.content, "html.parser")

    picks = soup.select(".ipc-poster-card")
    data = {"films": [], "series": []}

    for pick in picks:
        title_tag = pick.select_one(".ipc-title__text")
        desc_tag = pick.find_next("div", class_="ipc-html-content-inner-div")
        img_tag = pick.select_one("img")

        if not title_tag or not img_tag:
            continue

        title = title_tag.text.strip()
        description = desc_tag.text.strip() if desc_tag else ""
        image = img_tag.get("src")
        slug = slugify(title)
        link = f"https://altadefinizionepremium.com/p/{slug}"

        entry = {
            "title": title,
            "description": description,
            "image": image,
            "link": link
        }

        if is_series(title, description):
            data["series"].append(entry)
        else:
            data["films"].append(entry)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape()
