"""
scraper_senjob.py — Scraper senjob.com
2 types d'offres :
  - Sponsorisées : <tr class="leadsCycleBg rollover">
  - Normales     : <tr style="...border-bottom:1px dotted #86B82E...">
Pagination : https://senjob.com/sn/offres-d-emploi.php?page=N (8 pages)
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

BASE_URL = "https://senjob.com/sn/offres-d-emploi.php"

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


def parser_offre(tr) -> dict:
    """Extraire les données d'un <tr> d'offre (sponsorisée ou normale)."""

    lien_tag = tr.find("a", href=lambda h: h and "jobseekers" in h)
    if not lien_tag:
        return None

    # --- Titre ---
    titre = lien_tag.get_text(strip=True)

    # --- Lien absolu ---
    lien = lien_tag["href"]
    if lien.startswith("/"):
        lien = "https://senjob.com" + lien

    # --- Ville : td avec glyphicon-map-marker ---
    ville = "N/A"
    map_icon = tr.find("span", class_="glyphicon-map-marker")
    if map_icon:
        ville_td = map_icon.find_parent("td")
        if ville_td:
            ville = ville_td.get_text(strip=True)

    # --- Date publication : <span style="display:none;"> après glyphicon-calendar ---
    date = "N/A"
    cal_icon = tr.find("span", class_="glyphicon-calendar")
    if cal_icon:
        date_td = cal_icon.find_parent("td")
        if date_td:
            hidden = date_td.find("span", style=lambda s: s and "display:none" in s)
            if hidden:
                date = hidden.get_text(strip=True)

    # --- Date expiration : <span style="display:none;"> après glyphicon-time ---
    expire = "N/A"
    time_icon = tr.find("span", class_="glyphicon-time")
    if time_icon:
        expire_td = time_icon.find_parent("td")
        if expire_td:
            hidden = expire_td.find("span", style=lambda s: s and "display:none" in s)
            if hidden:
                expire = hidden.get_text(strip=True)

    return {
        "titre":           titre,
        "entreprise":      "N/A",
        "ville":           ville,
        "contrat":         "N/A",
        "date":            date,
        "date_expiration": expire,
        "lien":            lien,
        "source":          "senjob.com",
    }


def scrape_page(driver, page_number: int) -> list:
    url = f"{BASE_URL}?page={page_number}" if page_number > 1 else BASE_URL
    print(f"\n  Page {page_number} → {url}")

    driver.get(url)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Type 1 — Offres sponsorisées
    sponsored = soup.select("tr.leadsCycleBg.rollover")

    # Type 2 — Offres normales (style avec couleur verte #86B82E)
    normales = [
        tr for tr in soup.find_all("tr")
        if "86B82E" in tr.get("style", "")
        and tr.find("a", href=lambda h: h and "jobseekers" in h)
    ]

    print(f"      Sponsorisées : {len(sponsored)} | Normales : {len(normales)}")

    offres = []
    for tr in sponsored + normales:
        offre = parser_offre(tr)
        if offre and offre["titre"]:
            offres.append(offre)
            print(f"     ✓ {offre['titre'][:50]} | {offre['ville']} | {offre['date']}")

    print(f"      {len(offres)} offres extraites")
    return offres


def scrape_senjob(nb_pages: int = 8) -> pd.DataFrame:
    print("\n" + "="*55)
    print("   SCRAPER SENJOB.COM")
    print("="*55)

    driver = get_driver()
    toutes_offres = []

    try:
        for page in range(1, nb_pages + 1):
            offres = scrape_page(driver, page)
            toutes_offres.extend(offres)
            print(f"   Total cumulé : {len(toutes_offres)} offres")
            time.sleep(2)
    finally:
        driver.quit()
        print("\n   Driver fermé")

    df = pd.DataFrame(toutes_offres) if toutes_offres else pd.DataFrame(
        columns=["titre", "entreprise", "ville", "contrat", "date", "date_expiration", "lien", "source"]
    )
    df = df.drop_duplicates(subset=["titre"]).reset_index(drop=True)

    print(f"\n   {len(df)} offres uniques — senjob.com")
    return df


if __name__ == "__main__":
    df = scrape_senjob(nb_pages=8)  # 8 pages disponibles

    if df.empty:
        print("  Aucune offre trouvée")
    else:
        CSV_PATH = "data/senjob_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"\n Sauvegardé → {CSV_PATH}")
        print(f"\n Stats :")
        print(f"  Offres totales : {len(df)}")
        print(f"  Villes uniques : {df['ville'].nunique()}")
        print(f"\n  Top villes :\n{df['ville'].value_counts().head().to_string()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "ville", "date"]].head(10).to_string())