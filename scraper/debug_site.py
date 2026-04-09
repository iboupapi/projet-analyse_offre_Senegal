"""
debug_site.py — Inspecter rapidement un site pour trouver les bons sélecteurs CSS
Usage : modifier SITE_URL et lancer : python debug_site.py
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

SITE_URL = "https://www.optioncarriere.sn/emploi"

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

driver = get_driver()
driver.get(SITE_URL)
time.sleep(5)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(2)

soup = BeautifulSoup(driver.page_source, "html.parser")

print(f"=== ANALYSE : {SITE_URL} ===\n")
print(f"Titre de la page : {soup.title.get_text() if soup.title else 'N/A'}")

# Classes CSS sur les éléments principaux
print("\n=== CLASSES CSS (articles/div/li) ===")
classes = {}
for tag in soup.find_all(["article", "li", "div"], limit=200):
    cls = " ".join(tag.get("class", []))
    if cls and any(k in cls.lower() for k in ["job", "offre", "emploi", "post", "item", "card", "listing", "offer"]):
        classes[cls] = classes.get(cls, 0) + 1
for cls, count in sorted(classes.items(), key=lambda x: -x[1])[:20]:
    print(f"  [{count}x] .{cls}")

# Pagination
print("\n=== PAGINATION ===")
for tag in soup.find_all(["nav", "div", "ul"], limit=50):
    cls = " ".join(tag.get("class", []))
    if any(k in cls.lower() for k in ["pag", "page", "nav"]):
        print(f"  <{tag.name}> class='{cls}'")
        for a in tag.find_all("a", limit=5):
            print(f"    → '{a.get_text(strip=True)}' | href={a.get('href')} | data-page={a.get('data-page')}")

# Screenshot
driver.save_screenshot("debug_screenshot.png")
print("\n✅ Screenshot sauvegardé → debug_screenshot.png")

# Aperçu HTML brut
print("\n=== HTML BRUT (1000 premiers chars) ===")
print(driver.page_source[:1000])

driver.quit()
