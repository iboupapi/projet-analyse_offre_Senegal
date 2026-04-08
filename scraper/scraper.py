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
    driver = webdriver.Chrome(service=service, options=options)
    return driver

BASE_URL = "https://www.emploidakar.com/offres-demploi-au-senegal/"

def go_to_page(driver, page_number):
    # Page 1 est déjà affichée, inutile de cliquer
    if page_number == 1:
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.job_listings li.job_listing"))
        )
        return

    # Attendre que le lien de pagination soit présent et cliquer
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, f'a[data-page="{page_number}"]'))
    )
    driver.find_element(By.CSS_SELECTOR, f'a[data-page="{page_number}"]').click()

    # Attendre que les offres soient chargées
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.job_listings li.job_listing"))
    )

def scrape_page(driver, page_number: int) -> list:
    print(f"\n📄 Scraping page {page_number}")

    go_to_page(driver, page_number)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select("ul.job_listings li.job_listing")
    print(f"   🔍 {len(cards)} offre(s) trouvée(s)")

    offres = []
    for card in cards:
        titre      = card.select_one("div.position h3")
        entreprise = card.select_one("div.company strong")
        ville      = card.select_one("div.location")
        contrat    = card.select_one("ul.meta li.job-type")
        date       = card.select_one("ul.meta li.date time")
        lien       = card.select_one("a")

        offres.append({
            "titre": titre.get_text(strip=True) if titre else "N/A",
            "entreprise": entreprise.get_text(strip=True) if entreprise else "N/A",
            "ville": ville.get_text(strip=True) if ville else "N/A",
            "contrat": contrat.get_text(strip=True) if contrat else "N/A",
            "date": date.get("datetime", "N/A") if date else "N/A",
            "lien": lien.get("href", "N/A") if lien else "N/A",
        })

    return offres

def scrape_all(nb_pages: int = 5) -> pd.DataFrame:
    driver = get_driver()
    toutes_offres = []

    try:
        for page in range(1, nb_pages + 1):
            toutes_offres.extend(scrape_page(driver, page))
            time.sleep(2)
    finally:
        driver.quit()

    df = pd.DataFrame(toutes_offres)
    df = df.drop_duplicates(subset=["titre", "entreprise"]).reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = scrape_all(nb_pages=5)
    if df.empty:
        print("⚠️ Aucune offre trouvée")
    else:
        CSV_PATH = "data/data_raw.csv"
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ Sauvegardé → {CSV_PATH}")
        print(df.head(10))
