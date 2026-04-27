# scraper_linkedin.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

BASE_URL = "https://www.linkedin.com/jobs/jobs-in-senegal/?start={}"

def scrape_linkedin(max_pages: int = 5) -> pd.DataFrame:
    offres = []

    for page in range(max_pages):
        start = page * 25
        url = BASE_URL.format(start)
        print(f"  📄 Page {page + 1} — start={start}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            cards = soup.find_all("div", class_="base-search-card__info")

            if not cards:
                print("  ⛔ Plus de cartes trouvées, arrêt.")
                break

            for card in cards:
                titre = card.find("h3", class_="base-search-card__title")
                entreprise = card.find("h4", class_="base-search-card__subtitle")
                localisation = card.find("span", class_="job-search-card__location")
                date = card.find("time")

                offres.append({
                    "titre": titre.text.strip() if titre else None,
                    "entreprise": entreprise.text.strip() if entreprise else None,
                    "localisation": localisation.text.strip() if localisation else None,
                    "date_publication": date["datetime"] if date else None,
                    "source": "linkedin",
                })

            print(f"  ✅ {len(cards)} offres récupérées")
            time.sleep(2)  # pause polie

        except Exception as e:
            print(f"  ❌ Erreur page {page + 1} : {e}")
            break

    df = pd.DataFrame(offres)
    output = os.path.join(os.path.dirname(__file__), "data", "linkedin_raw.csv")
    df.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\n  💾 {len(df)} offres sauvegardées → linkedin_raw.csv")
    return df


if __name__ == "__main__":
    scrape_linkedin()