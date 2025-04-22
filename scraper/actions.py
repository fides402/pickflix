import csv
import json
import os

# Funzione per caricare una categoria da file TSV
def load_category(filename):
    items = []
    if not os.path.exists(filename):
        print(f"[INFO] File non trovato: {filename} — categoria ignorata.")
        return items

    with open(filename, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            title = row.get("Title", "").strip()
            if not title:
                continue  # Salta righe senza titolo

            rating = row.get("Rating", "").strip() if "Rating" in row else None
            items.append({
                "title": title,
                "rating": rating
            })

    return items

# Funzione principale
def main():
    data = {
        "staff_picks": load_category("movies_and_ratings.txt"),
        "trending_films": load_category("trending_movies.txt"),
        "trending_series": load_category("trending_series.txt")
    }

    with open("data.json", "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=2)

    print("[✓] File 'data.json' aggiornato con successo!")

# Esegui solo se è lo script principale
if __name__ == "__main__":
    main()
