name: Scrape IMDb Picks

on:
  schedule:
    - cron: '0 8 * * *'  # Ogni giorno alle 8:00 UTC
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies (Selenium + Chrome)
        run: |
          sudo apt update
          sudo apt install -y chromium-browser
          pip install selenium

      - name: Run scraper script
        env:
          PATH: "/usr/lib/chromium-browser/:$PATH"
        run: |
          python scraper/actions.py

      - name: Commit and push updated data.json
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "actions@github.com"
          git add data.json
          git commit -m "update data.json from IMDb staff picks" || echo "No changes to commit"
          git push
