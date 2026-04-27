from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

BASE_URL = "https://www.senejobs.com/mod-search.html"


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


def charger_page(driver) -> BeautifulSoup:
    """
    Charge simplement la page mod-search.html.
    Pas de pagination dynamique sur SeneJobs.
    """
    print(f"\n  📄 Chargement de {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(4)

    return BeautifulSoup(driver.page_source, "html.parser")


def parser_offres(soup: BeautifulSoup) -> list:
    """
    Extrait les offres depuis les blocs .job-wrap

    Structure HTML SeneJobs :
        <div class="job-wrap">
            <a href="emploi-xxx.html">Titre</a>
            <div class="results-job-description">Résumé</div>
            <a href="entreprise-xxx.html">Entreprise</a>
        </div>
    """
    cards = soup.select(".job-wrap")
    print(f"  🔍 {len(cards)} offre(s) détectées")

    offres = []

    for card in cards:

        # --- Titre ---
        titre = "N/A"
        lien = "N/A"
        titre_tag = card.select_one("a[href*='emploi-']")
        if titre_tag:
            titre = titre_tag.get_text(strip=True)
            href = titre_tag.get("href", "")
            lien = href if href.startswith("http") else "https://www.senejobs.com/" + href

        # --- Entreprise ---
        entreprise = "N/A"
        ent_tag = card.select_one("a[href*='entreprise-']")
        if ent_tag:
            entreprise = ent_tag.get_text(strip=True)

        # --- Description ---
        desc_tag = card.select_one(".results-job-description")
        description = desc_tag.get_text(strip=True) if desc_tag else "N/A"

        # --- Ville / Contrat / Date ---
        # SeneJobs ne les affiche pas dans la liste
        ville = "N/A"
        contrat = "N/A"
        date = "N/A"

        if titre != "N/A":
            offres.append({
                "titre":      titre,
                "entreprise": entreprise,
                "ville":      ville,
                "contrat":    contrat,
                "date":       date,
                "description": description,
                "lien":       lien,
                "source":     "senejobs.com",
            })

            print(f"  ✓ {titre[:50]} | {entreprise}")

    return offres


def scrape_senejobs() -> pd.DataFrame:
    print("\n" + "="*55)
    print("  🌐 SCRAPER SENEJOBS.COM")
    print("="*55)

    driver = get_driver()

    try:
        soup = charger_page(driver)
    finally:
        driver.quit()
        print("\n  🔒 Driver fermé")

    offres = parser_offres(soup)

    df = pd.DataFrame(offres) if offres else pd.DataFrame(
        columns=["titre", "entreprise", "ville", "contrat", "date", "description", "lien", "source"]
    )
    # df = df.drop_duplicates(subset=["titre", "entreprise"]).reset_index(drop=True)

    print(f"\n  ✅ {len(df)} offres uniques — senejobs.com")
    return df


if __name__ == "__main__":
    df = scrape_senejobs()

    if df.empty:
        print("⚠️  Aucune offre trouvée")
    else:
        CSV_PATH = "data/senejobs_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"\n✅ Sauvegardé → {CSV_PATH}")
        print(f"\n📊 Stats :")
        print(f"  Offres totales : {len(df)}")
        print(f"  Entreprises    : {df['entreprise'].nunique()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "entreprise"]].head(10).to_string())
