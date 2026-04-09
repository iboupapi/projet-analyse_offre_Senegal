"""
scraper_optioncarriere.py — Scraper optioncarriere.sn
Structure :
  - Chaque offre : article.job.clicky
  - Titre        : h2 a
  - Entreprise   : p.company (texte ou lien)
  - Ville        : ul.location li (après l'icône svg)
  - Date         : span.badge (contient "Il y a X...")
  - Lien         : article[data-url]
Pagination : https://www.optioncarriere.sn/emploi?l=S%C3%A9n%C3%A9gal&p=N
394 offres, ~20/page → ~20 pages
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

BASE_URL = "https://www.optioncarriere.sn/emploi?l=S%C3%A9n%C3%A9gal&p={page}"


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
    url = BASE_URL.format(page=page_number)
    print(f"\n   Page {page_number} → {url}")

    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.job.clicky"))
        )
    except Exception:
        print("       Timeout — fin de pagination ou page vide")
        return []

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select("article.job.clicky")
    print(f"      {len(cards)} offre(s) trouvée(s)")

    offres = []
    for card in cards:

        # --- Titre ---
        titre_tag = card.select_one("h2 a")
        titre = titre_tag.get_text(strip=True) if titre_tag else "N/A"

        # --- Lien : attribut data-url sur l'article ---
        lien = card.get("data-url", "N/A")
        if lien and lien.startswith("/"):
            lien = "https://www.optioncarriere.sn" + lien

        # --- Entreprise : p.company ---
        entreprise_tag = card.select_one("p.company")
        if entreprise_tag:
            # Retirer les liens internes pour garder juste le texte
            entreprise = entreprise_tag.get_text(strip=True)
        else:
            entreprise = "N/A"

        # --- Ville : ul.location li (ignorer le SVG) ---
        ville = "N/A"
        location_lis = card.select("ul.location li")
        for li in location_lis:
            # Supprimer les balises SVG pour garder le texte
            for svg in li.find_all("svg"):
                svg.decompose()
            txt = li.get_text(strip=True)
            if txt:
                ville = txt
                break

        # --- Date : span.badge contenant "Il y a" ---
        date = "N/A"
        for badge in card.select("span.badge"):
            txt = badge.get_text(strip=True)
            if "Il y a" in txt or "Aujourd" in txt or "hier" in txt.lower():
                date = txt
                break

        # --- Contrat : non affiché sur cette page ---
        contrat = "N/A"

        if titre != "N/A":
            offres.append({
                "titre":      titre,
                "entreprise": entreprise,
                "ville":      ville,
                "contrat":    contrat,
                "date":       date,
                "lien":       lien,
                "source":     "optioncarriere.sn",
            })
            print(f"     ✓ {titre[:50]} | {entreprise[:20]} | {ville} | {date}")

    return offres


def scrape_optioncarriere(nb_pages: int = 20) -> pd.DataFrame:
    print("\n" + "="*55)
    print("   SCRAPER OPTIONCARRIERE.SN")
    print("="*55)
    print(f"   Cible : ~394 offres sur {nb_pages} pages")

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
        print("\n  🔒 Driver fermé")

    df = pd.DataFrame(toutes_offres) if toutes_offres else pd.DataFrame(
        columns=["titre", "entreprise", "ville", "contrat", "date", "lien", "source"]
    )
    df = df.drop_duplicates(subset=["titre", "entreprise"]).reset_index(drop=True)

    print(f"\n   {len(df)} offres uniques — optioncarriere.sn")
    return df


if __name__ == "__main__":
    df = scrape_optioncarriere(nb_pages=20)

    if df.empty:
        print("  Aucune offre trouvée")
    else:
        CSV_PATH = "data/optioncarriere_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"\n Sauvegardé → {CSV_PATH}")
        print(f"\n Stats :")
        print(f"  Offres totales : {len(df)}")
        print(f"  Villes uniques : {df['ville'].nunique()}")
        print(f"\n  Top villes :\n{df['ville'].value_counts().head().to_string()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "entreprise", "ville", "date"]].head(10).to_string())