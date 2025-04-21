def fetch_on_air_series():
    url = f"{BASE_URL}/tv/on_the_air"
    params = {
        "api_key": API_KEY,
        "language": LANG,
        "page": 1
    }

    print(f"📡 Fetching serie TV attualmente in onda...")

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"⚠️ Errore ON_AIR: {response.status_code}")
        return []

    results = response.json().get("results", [])
    items = []

    for r in results:
        vote = r.get("vote_average", 0)
        if vote < 7:
            continue

        title = r.get("name")
        poster_path = r.get("poster_path")
        if not title or not poster_path:
            continue

        image = f"https://image.tmdb.org/t/p/w500{poster_path}"
        slug = slugify(title)
        link = f"https://altadefinizionepremium.com/p/{slug}"
        rating = round(vote, 1)

        items.append({
            "title": title,
            "image": image,
            "link": link,
            "rating": str(rating)
        })

    return items
