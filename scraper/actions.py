import csv
import json
import os

# Carica i film "staff picks" da un file TSV
def load_staff_picks(filename):
    picks = []
    if not os.path.exists(filename):
        print(f"[WARNING] File non trovato: {filename}")
        return picks

    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')

        for row in reader:
            if 'Title' not in row:
                print("[INFO] Riga ignorata: manca 'Title'")
                continue

            title = row.get("Title", "").strip()
            rating = row.get("Rating", "").strip() if "Rating" in row else None

            picks.append({
                "title": title,
                "rating": rating
            })

    return picks

# Funzione principale dello script
def main():
    staff_picks = load_staff_picks("movies_and_ratings.txt")

    # Salva il file JSON risultante
    with open("data.json", "w", encoding="utf-8") as outfile:
        json.dump(staff_picks, outfile, ensure_ascii=False, indent=2)

    print(f"[DONE] Salvati {len(staff_picks)} film in data.json")

# Avvia lo script se eseguito direttamente
if __name__ == "__main__":
    main()
