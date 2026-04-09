"""
scraper_senego.py — Scraper annonces.senego.com/category/jobs
Structure :
  - Chaque offre : div.col.item-list
  - Titre        : h5 > a.link-body-emphasis
  - Ville        : li > a[href*="search?l="]
  - Date         : li > i.fa-regular.fa-clock (texte suivant)
  - Lien         : a[href*="/annonces.senego.com/"]
Pagination : https://annonces.senego.com/category/jobs?page=N (32 pages, ~384 offres)
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

BASE_URL = "https://annonces.senego.com/category/jobs"


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

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.col.item-list"))
        )
    except Exception:
        print("       Timeout — fin de pagination")
        return []

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select("div.col.item-list")
    print(f"      {len(cards)} offre(s) trouvée(s)")

    offres = []
    for card in cards:

        # --- Titre ---
        titre_tag = card.select_one("h5 a.link-body-emphasis")
        titre = titre_tag.get_text(strip=True) if titre_tag else "N/A"

        # --- Lien ---
        lien = titre_tag.get("href", "N/A") if titre_tag else "N/A"

        # --- Date : texte après <i class="fa-regular fa-clock"> ---
        date = "N/A"
        clock_icon = card.select_one("i.fa-regular.fa-clock")
        if clock_icon:
            # Le texte est le nœud suivant l'icône
            date_txt = clock_icon.next_sibling
            if date_txt:
                date = str(date_txt).strip()

        # --- Ville : lien avec search?l= ---
        ville = "N/A"
        ville_tag = card.select_one("a[href*='search?l=']")
        if ville_tag:
            ville = ville_tag.get_text(strip=True)

        # --- Catégorie / contrat : lien vers category ---
        contrat = "N/A"
        cat_tag = card.select_one("a[href*='category']")
        if cat_tag:
            contrat = cat_tag.get_text(strip=True)

        if titre != "N/A":
            offres.append({
                "titre":      titre,
                "entreprise": "N/A",  # non affiché sur senego annonces
                "ville":      ville,
                "contrat":    contrat,
                "date":       date,
                "lien":       lien,
                "source":     "senego.com",
            })
            print(f"     ✓ {titre[:50]} | {ville} | {date}")

    return offres


def scrape_senego(nb_pages: int = 32) -> pd.DataFrame:
    print("\n" + "="*55)
    print("   SCRAPER SENEGO ANNONCES")
    print("="*55)
    print(f"   Cible : ~384 offres sur {nb_pages} pages")

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
    df = df.drop_duplicates(subset=["titre", "ville"]).reset_index(drop=True)

    print(f"\n   {len(df)} offres uniques — senego.com")
    return df


if __name__ == "__main__":
    df = scrape_senego(nb_pages=32)

    if df.empty:
        print("  Aucune offre trouvée")
    else:
        CSV_PATH = "data/senego_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"\n Sauvegardé → {CSV_PATH}")
        print(f"\n Stats :")
        print(f"  Offres totales : {len(df)}")
        print(f"  Villes uniques : {df['ville'].nunique()}")
        print(f"\n  Top villes :\n{df['ville'].value_counts().head().to_string()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "ville", "date"]].head(10).to_string())