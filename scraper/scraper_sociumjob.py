"""
scraper_sociumjob.py — Scraper sociumjob.com/jobs
Structure :
  - Chaque offre  : div.w-full.space-y-6
  - Titre         : h3.job-title
  - Contrat       : div > p > span (après icône contract.svg)
  - Ville         : p.ml-1.overflow-hidden.truncate (après icône pin.svg)
  - Date          : time
  - Lien          : parent <a> de la carte
Pagination : Bouton "Voir plus d'offres" (infinite scroll)
             → 20 offres par clic, max 117 offres (5 clics suffisent)
             → Détection du plateau : arrêt si le nombre d'offres
               ne change plus entre deux clics
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

BASE_URL = "https://sociumjob.com/jobs"


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


def charger_toutes_les_offres(driver) -> BeautifulSoup:
    """
    Charge toutes les offres en cliquant sur 'Voir plus d'offres'
    jusqu'à ce que le nombre d'offres n'augmente plus (plateau).

    Stratégie anti-boucle infinie :
    - Si le nombre d'offres n'augmente pas pendant 2 clics consécutifs
      → on considère que tout est chargé et on s'arrête.
    """
    print(f"\n  📄 Chargement de {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(5)

    nb_precedent = 0
    nb_stable = 0       # Compteur de clics sans changement
    MAX_STABLE = 2      # Arrêt après 2 clics sans nouvelles offres
    clic = 0

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        nb_actuel = len(soup.select("div.w-full.space-y-6"))

        if nb_actuel == nb_precedent:
            nb_stable += 1
            if nb_stable >= MAX_STABLE:
                print(f"  🔚 Plateau atteint : {nb_actuel} offres (arrêt après {clic} clics)")
                break
        else:
            nb_stable = 0
            nb_precedent = nb_actuel

        # Chercher et cliquer sur le bouton "Voir plus"
        try:
            btn = driver.find_element(
                By.XPATH, "//*[contains(text(), \"Voir plus d'offres\")]"
            )
            driver.execute_script("arguments[0].click();", btn)
            clic += 1
            print(f"  🔄 Clic {clic} → {nb_actuel} offres chargées")
            time.sleep(3)
        except Exception:
            print(f"  🔚 Bouton introuvable après {clic} clics — fin du chargement")
            break

    return BeautifulSoup(driver.page_source, "html.parser")


def parser_offres(soup: BeautifulSoup) -> list:
    """
    Extrait les données de toutes les cartes d'offres.

    Structure HTML d'une carte sociumjob :
        <a href="/jobs/...">
          <div class="w-full space-y-6">
            <h3 class="job-title">Titre</h3>
            <div> <img alt="contract"> <p><span>Type contrat</span></p> </div>
            <div>
              <div> <img alt="pin"> <p>Ville</p> </div>
              <div> <img alt="clock"> <p><time>Date</time></p> </div>
            </div>
          </div>
        </a>
    """
    cards = soup.select("div.w-full.space-y-6")
    print(f"  🔍 {len(cards)} offre(s) à parser")

    offres = []
    for card in cards:

        # --- Titre ---
        titre_tag = card.select_one("h3.job-title")
        titre = titre_tag.get_text(strip=True) if titre_tag else "N/A"

        # --- Contrat : span après l'icône contract ---
        contrat = "N/A"
        contract_img = card.find("img", {"alt": "contract"})
        if contract_img:
            span = contract_img.find_next("span")
            if span:
                contrat = span.get_text(strip=True)

        # --- Ville : paragraphe après l'icône pin ---
        ville = "N/A"
        pin_img = card.find("img", {"alt": "pin"})
        if pin_img:
            ville_p = pin_img.find_next("p")
            if ville_p:
                ville = ville_p.get_text(strip=True)

        # --- Date : balise <time> ---
        date = "N/A"
        time_tag = card.select_one("time")
        if time_tag:
            date = time_tag.get_text(strip=True)

        # --- Lien : remonter jusqu'au parent <a> ---
        lien = "N/A"
        parent_a = card.find_parent("a")
        if parent_a and parent_a.get("href"):
            href = parent_a["href"]
            lien = href if href.startswith("http") else "https://sociumjob.com" + href

        # --- Entreprise : non affiché sur la liste ---
        entreprise = "N/A"

        if titre != "N/A":
            offres.append({
                "titre":      titre,
                "entreprise": entreprise,
                "ville":      ville,
                "contrat":    contrat,
                "date":       date,
                "lien":       lien,
                "source":     "sociumjob.com",
            })
            print(f"  ✓ {titre[:50]} | {ville} | {contrat} | {date}")

    return offres


def scrape_sociumjob() -> pd.DataFrame:
    print("\n" + "="*55)
    print("  🌐 SCRAPER SOCIUMJOB.COM")
    print("="*55)

    driver = get_driver()

    try:
        soup = charger_toutes_les_offres(driver)
    finally:
        driver.quit()
        print("\n  🔒 Driver fermé")

    offres = parser_offres(soup)

    df = pd.DataFrame(offres) if offres else pd.DataFrame(
        columns=["titre", "entreprise", "ville", "contrat", "date", "lien", "source"]
    )
    # df = df.drop_duplicates(subset=["titre", "ville"]).reset_index(drop=True)

    print(f"\n  ✅ {len(df)} offres uniques — sociumjob.com")
    return df


if __name__ == "__main__":
    df = scrape_sociumjob()

    if df.empty:
        print("⚠️  Aucune offre trouvée")
    else:
        CSV_PATH = "data/sociumjob_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        print(f"\n✅ Sauvegardé → {CSV_PATH}")
        print(f"\n📊 Stats :")
        print(f"  Offres totales : {len(df)}")
        print(f"  Villes uniques : {df['ville'].nunique()}")
        print(f"  Contrats       : {df['contrat'].value_counts().head().to_dict()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "ville", "contrat", "date"]].head(10).to_string())