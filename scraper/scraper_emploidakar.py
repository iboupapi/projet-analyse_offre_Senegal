"""
============================================================
scraper_emploidakar.py
------------------------------------------------------------
Objectif  : Extraire les offres d'emploi publiées sur
            emploidakar.com (section Sénégal).
Technique : Selenium + BeautifulSoup.
            Le site charge ses offres via JavaScript (WP Job
            Manager + AJAX) : requests seul ne suffit pas.
            On pilote un vrai navigateur Chrome en mode
            "headless" (sans interface graphique) pour que
            le JavaScript s'exécute et que les offres
            apparaissent dans le DOM avant qu'on les lise.
Pagination: Le site utilise des liens <a data-page="N">
            qui déclenchent un rechargement AJAX sans changer
            l'URL. On clique dessus via Selenium au lieu de
            construire une URL de page.
Sortie    : CSV → data/emploidakar_raw.csv
            Colonnes : titre, entreprise, ville, contrat,
                       date, lien
============================================================
"""

# ── Bibliothèques de pilotage du navigateur ──────────────
from selenium import webdriver                        # Contrôle Chrome
from selenium.webdriver.chrome.options import Options # Paramètres Chrome
from selenium.webdriver.chrome.service import Service # Gestion du driver
from selenium.webdriver.common.by import By           # Stratégies de localisation d'éléments
from selenium.webdriver.support.ui import WebDriverWait          # Attente explicite
from selenium.webdriver.support import expected_conditions as EC  # Conditions d'attente

# ── Installation automatique de ChromeDriver ─────────────
from webdriver_manager.chrome import ChromeDriverManager

# ── Parsing HTML ─────────────────────────────────────────
from bs4 import BeautifulSoup  # Lecture et extraction des données HTML

# ── Données et utilitaires ───────────────────────────────
import pandas as pd  # Manipulation et export CSV
import time          # Pauses entre requêtes (politesse envers le serveur)
import os            # Création des dossiers de sortie


# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────

# URL de la page listant toutes les offres au Sénégal
BASE_URL = "https://www.emploidakar.com/offres-demploi-au-senegal/"


# ─────────────────────────────────────────────────────────
# INITIALISATION DU NAVIGATEUR
# ─────────────────────────────────────────────────────────

def get_driver():
    """
    Configure et retourne une instance Chrome en mode headless.

    Options utilisées :
    - --headless         : Pas d'interface graphique (nécessaire en prod/CI)
    - --no-sandbox       : Requis dans les environnements Linux restreints
    - --disable-dev-shm-usage : Évite les crashs mémoire sur Docker/Linux
    - --disable-gpu      : Désactive le GPU (inutile en headless)
    - --window-size      : Simule une résolution desktop pour que le site
                           affiche la version complète (pas mobile)
    - user-agent         : Simule un vrai navigateur pour éviter d'être
                           bloqué comme bot
    """
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

    # ChromeDriverManager télécharge et installe automatiquement
    # la version de ChromeDriver compatible avec Chrome installé
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


# ─────────────────────────────────────────────────────────
# NAVIGATION ENTRE LES PAGES
# ─────────────────────────────────────────────────────────

def go_to_page(driver, page_number):
    """
    Navigue vers une page de résultats donnée.

    Pourquoi cette fonction existe :
        emploidakar.com n'a pas de pagination par URL (ex: ?page=2).
        Les offres sont chargées via AJAX : cliquer sur un lien
        <a data-page="N"> déclenche une requête en arrière-plan
        sans recharger la page entière.

    Stratégie :
    - Page 1 → navigation directe via driver.get()
    - Pages suivantes → on attend que le lien <a data-page="N">
      soit présent dans le DOM, on clique dessus, puis on attend
      que les nouvelles offres se chargent.

    Args:
        driver      : Instance Selenium active
        page_number : Numéro de page à atteindre (commence à 1)
    """
    if page_number == 1:
        # Chargement initial : on visite directement l'URL
        driver.get(BASE_URL)
        # Attente explicite : on attend que les offres soient visibles
        # avant de continuer (max 10 secondes)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.job_listings li.job_listing"))
        )
        return

    # Pour les pages > 1 : attendre le bouton de pagination correspondant
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, f'a[data-page="{page_number}"]'))
    )
    # Cliquer sur le lien de pagination → déclenche le rechargement AJAX
    driver.find_element(By.CSS_SELECTOR, f'a[data-page="{page_number}"]').click()

    # Attendre que les nouvelles offres soient bien affichées
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.job_listings li.job_listing"))
    )


# ─────────────────────────────────────────────────────────
# EXTRACTION D'UNE PAGE
# ─────────────────────────────────────────────────────────

def scrape_page(driver, page_number: int) -> list:
    """
    Extrait toutes les offres d'une page de résultats.

    Processus :
    1. Naviguer vers la page via go_to_page()
    2. Lire le HTML complet rendu par le navigateur
    3. Parser avec BeautifulSoup
    4. Sélectionner chaque carte d'offre : li.job_listing
    5. Extraire les champs : titre, entreprise, ville, contrat, date, lien

    Structure HTML d'une offre sur emploidakar.com :
        <li class="job_listing">
          <a href="...">
            <div class="position"><h3>Titre</h3></div>
            <div class="company"><strong>Entreprise</strong></div>
            <div class="location">Ville</div>
            <ul class="meta">
              <li class="job-type">CDI</li>
              <li class="date"><time datetime="2026-04-08">...</time></li>
            </ul>
          </a>
        </li>

    Args:
        driver      : Instance Selenium active (navigateur déjà ouvert)
        page_number : Numéro de la page à scraper

    Returns:
        Liste de dictionnaires, un par offre trouvée
    """
    print(f"\n Scraping page {page_number}")

    # Navigation vers la bonne page
    go_to_page(driver, page_number)

    # Récupération du HTML complet après exécution du JavaScript
    # BeautifulSoup parse ce HTML pour faciliter l'extraction
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Sélection de toutes les cartes d'offres sur la page
    cards = soup.select("ul.job_listings li.job_listing")
    print(f"    {len(cards)} offre(s) trouvée(s)")

    offres = []
    for card in cards:
        # Extraction de chaque champ via les sélecteurs CSS validés
        titre      = card.select_one("div.position h3")
        entreprise = card.select_one("div.company strong")
        ville      = card.select_one("div.location")
        contrat    = card.select_one("ul.meta li.job-type")

        # L'attribut datetime donne la date au format ISO (ex: "2026-04-08")
        date       = card.select_one("ul.meta li.date time")
        lien       = card.select_one("a")

        # Construction du dictionnaire : si un champ est absent → "N/A"
        offres.append({
            "titre":      titre.get_text(strip=True)       if titre      else "N/A",
            "entreprise": entreprise.get_text(strip=True)  if entreprise else "N/A",
            "ville":      ville.get_text(strip=True)       if ville      else "N/A",
            "contrat":    contrat.get_text(strip=True)     if contrat    else "N/A",
            "date":       date.get("datetime", "N/A")      if date       else "N/A",
            "lien":       lien.get("href", "N/A")          if lien       else "N/A",
        })

    return offres


# ─────────────────────────────────────────────────────────
# ORCHESTRATION : SCRAPER TOUTES LES PAGES
# ─────────────────────────────────────────────────────────

def scrape_all(nb_pages: int = 15) -> pd.DataFrame:
    """
    Lance le scraping sur plusieurs pages et retourne un DataFrame.

    Processus :
    1. Ouvrir un seul navigateur (optimisation : évite de relancer Chrome
       à chaque page)
    2. Boucler sur les pages 1 à nb_pages
    3. Collecter toutes les offres
    4. Fermer le navigateur proprement (bloc finally : garanti même en
       cas d'erreur)
    5. Construire un DataFrame pandas et supprimer les doublons

    Args:
        nb_pages : Nombre de pages à scraper (défaut : 5 = ~85 offres)

    Returns:
        DataFrame pandas avec toutes les offres uniques
    """
    driver = get_driver()
    toutes_offres = []

    try:
        for page in range(1, nb_pages + 1):
            toutes_offres.extend(scrape_page(driver, page))
            # Pause de 2 secondes entre chaque page :
            # - Évite de surcharger le serveur (comportement responsable)
            # - Réduit le risque d'être détecté et bloqué comme bot
            time.sleep(2)
    finally:
        # Le bloc finally garantit que le navigateur est toujours fermé,
        # même si une exception se produit pendant le scraping
        driver.quit()

    # Création du DataFrame
    df = pd.DataFrame(toutes_offres)

    # Suppression des doublons : une même offre peut apparaître sur
    # plusieurs pages si de nouvelles sont publiées pendant le scraping
    # df = df.drop_duplicates(subset=["titre", "entreprise"]).reset_index(drop=True)

    return df


# ─────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Exécution directe du script :
        python scraper_emploidakar.py

    Ce bloc ne s'exécute PAS quand le fichier est importé
    par un autre script (ex: main.py). Cela permet de réutiliser
    scrape_all() sans déclencher le scraping automatiquement.
    """
    df = scrape_all(nb_pages=15)

    if df.empty:
        print("Aucune offre trouvée")
    else:
        CSV_PATH = "data/emploidakar_raw.csv"

        # Création du dossier data/ s'il n'existe pas encore
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

        # Export CSV avec encodage UTF-8 + BOM :
        # utf-8-sig garantit que Excel (Windows) affiche
        # correctement les caractères accentués (é, à, ê...)
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"Sauvegardé → {CSV_PATH}")
        print(df.head(10))