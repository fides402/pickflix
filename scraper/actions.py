import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def is_series(title, description):
    keywords = ['episode', 'season', 'series', 'tv']
    return any(k in description.lower() or k in title.lower() for k in keywords)

def scrape():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = '/usr/bin/chromium-browser'

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.imdb.com/imdbpicks/staff-picks/")
    time.sleep(5)

    data = {"films": [], "series": []}
    cards = driver.find_elements(By.CSS_SELECTOR, ".ipc-poster-card")

    for card in cards:
        try:
            title = card.find_element(By.CSS_SELECTOR, ".ipc-title__text").text.strip()
            image = card.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
            desc_elem = card.find_elements(By.CSS_SELECTOR, ".ipc-poster-card__description")
            description = desc_elem[0].text.strip() if desc_elem else ""
            slug = slugify(title)
            link = f"https://altadefinizionepremium.com/p/{slug}"

            item = {
                "title": title,
                "description": description,
                "image": image,
                "link": link
            }

            if is_series(title, description):
                data["series"].append(item)
            else:
                data["films"].append(item)

        except Exception as e:
            print(f"[skip] Card failed: {e}")
            continue

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    driver.quit()

if __name__ == "__main__":
    scrape()
