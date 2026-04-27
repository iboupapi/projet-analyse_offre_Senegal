"""
scraper_expatdakar.py — Scraper expat-dakar.com/emploi
Structure :
  - Chaque offre : div.listing-card
  - Titre        : div.listing-card__header__title
  - Ville        : div.listing-card__header__location
  - Date         : div.listing-card__header__date
  - Contrat      : div.listing-card__header__tags
Pagination : https://www.expat-dakar.com/emploi?page=N
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

BASE_URL = "https://www.expat-dakar.com/emploi"


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def scrape_page(driver, page_number: int) -> list:
    url = f"{BASE_URL}?page={page_number}" if page_number > 1 else BASE_URL
    print(f"\n   Page {page_number} → {url}")

    driver.get(url)

    # Fermer popup notification si présent
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Désactiver') or contains(text(),'désactiver')]"))
        ).click()
        print("      Popup fermé")
    except Exception:
        pass

    # Attendre les cartes
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-card"))
        )
    except Exception:
        print("       Timeout — page vide ou fin de pagination")
        return []

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select("div.listing-card")
    print(f"      {len(cards)} offre(s) trouvée(s)")

    offres = []
    for card in cards:
        # Titre
        titre_tag = card.select_one("div.listing-card__header__title")
        titre = titre_tag.get_text(strip=True) if titre_tag else "N/A"

        # Ville
        ville_tag = card.select_one("div.listing-card__header__location")
        ville = ville_tag.get_text(strip=True) if ville_tag else "N/A"

        # Date
        date_tag = card.select_one("div.listing-card__header__date")
        date = date_tag.get_text(strip=True) if date_tag else "N/A"

        # Contrat (tags)
        contrat_tag = card.select_one("div.listing-card__header__tags")
        contrat = contrat_tag.get_text(strip=True) if contrat_tag else "N/A"

        # Entreprise
        entreprise_tag = card.select_one("div.listing-card__header-content")
        entreprise = "N/A"
        if entreprise_tag:
            # L'entreprise est souvent après le titre
            spans = entreprise_tag.find_all("span")
            for span in spans:
                txt = span.get_text(strip=True)
                if txt and txt != titre and len(txt) < 60:
                    entreprise = txt
                    break

        # Lien
        lien_tag = card.select_one("a")
        lien = lien_tag.get("href", "N/A") if lien_tag else "N/A"
        if lien and lien.startswith("/"):
            lien = "https://www.expat-dakar.com" + lien

        if titre != "N/A":
            offres.append({
                "titre":      titre,
                "entreprise": entreprise,
                "ville":      ville,
                "contrat":    contrat,
                "date":       date,
                "lien":       lien,
                "source":     "expat-dakar.com",
            })
            print(f"     ✓ {titre[:50]} | {ville} | {date}")

    return offres


def scrape_expatdakar(nb_pages: int = 10) -> pd.DataFrame:
    print("\n" + "="*55)
    print("   SCRAPER EXPAT-DAKAR.COM")
    print("="*55)

    driver = get_driver()
    toutes_offres = []

    try:
        for page in range(1, nb_pages + 1):
            offres = scrape_page(driver, page)

            if not offres:
                print(f"\n   Fin de pagination à la page {page}")
                break

            toutes_offres.extend(offres)
            print(f"   Total cumulé : {len(toutes_offres)} offres")
            time.sleep(2)
    finally:
        driver.quit()
        print("\n   Driver fermé")

    df = pd.DataFrame(toutes_offres) if toutes_offres else pd.DataFrame(
        columns=["titre", "entreprise", "ville", "contrat", "date", "lien", "source"]
    )
    # df = df.drop_duplicates(subset=["titre", "ville"]).reset_index(drop=True)

    print(f"\n   {len(df)} offres uniques — expat-dakar.com")
    return df


if __name__ == "__main__":
    df = scrape_expatdakar(nb_pages=10)

    if df.empty:
        print("  Aucune offre trouvée")
    else:
        CSV_PATH = "data/expatdakar_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"\n Sauvegardé → {CSV_PATH}")
        print(f"\n Stats :")
        print(f"  Offres totales : {len(df)}")
        print(f"  Villes uniques : {df['ville'].nunique()}")
        print(f"  Contrats       : {df['contrat'].value_counts().head().to_dict()}")
        print(f"\n  Top villes :\n{df['ville'].value_counts().head().to_string()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "ville", "contrat", "date"]].head(10).to_string())