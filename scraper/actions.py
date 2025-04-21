import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def is_series(title, description):
    keywords = ['season', 'episodes', 'series', 'tv']
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

    titles = driver.find_elements(By.CSS_SELECTOR, "h3.ipc-title__text")
    descriptions = driver.find_elements(By.CSS_SELECTOR, "p.sc-kdBSHD.jUsAye.item--description")
    images = driver.find_elements(By.CSS_SELECTOR, "img.ipc-image")

    count = min(len(titles), len(descriptions), len(images))

    for i in range(count):
        try:
            title = titles[i].text.strip()
            description = descriptions[i].text.strip()
            image = images[i].get_attribute("src")
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
            print(f"[SKIP] Error extracting item {i}: {e}")
            continue

    driver.quit()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Scraping completato: {len(data['films'])} film, {len(data['series'])} serie")

if __name__ == "__main__":
    scrape()
