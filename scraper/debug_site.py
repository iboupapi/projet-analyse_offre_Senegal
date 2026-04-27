# # """
# # debug_site.py — Inspecter rapidement un site pour trouver les bons sélecteurs CSS
# # Usage : modifier SITE_URL et lancer : python debug_site.py
# # """
# # from selenium import webdriver
# # from selenium.webdriver.chrome.options import Options
# # from selenium.webdriver.chrome.service import Service
# # from selenium.webdriver.common.by import By
# # from webdriver_manager.chrome import ChromeDriverManager
# # from bs4 import BeautifulSoup
# # import time

# # SITE_URL = "https://afriqueemplois.com/sn"

# # def get_driver():
# #     options = Options()
# #     options.add_argument("--headless")
# #     options.add_argument("--no-sandbox")
# #     options.add_argument("--disable-dev-shm-usage")
# #     options.add_argument("--window-size=1920,1080")
# #     service = Service(ChromeDriverManager().install())
# #     return webdriver.Chrome(service=service, options=options)

# # driver = get_driver()
# # driver.get(SITE_URL)
# # time.sleep(5)
# # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
# # time.sleep(2)

# # soup = BeautifulSoup(driver.page_source, "html.parser")

# # print(f"=== ANALYSE : {SITE_URL} ===\n")
# # print(f"Titre de la page : {soup.title.get_text() if soup.title else 'N/A'}")

# # # Classes CSS sur les éléments principaux
# # print("\n=== CLASSES CSS (articles/div/li) ===")
# # classes = {}
# # for tag in soup.find_all(["article", "li", "div"], limit=200):
# #     cls = " ".join(tag.get("class", []))
# #     if cls and any(k in cls.lower() for k in ["job", "offre", "emploi", "post", "item", "card", "listing", "offer"]):
# #         classes[cls] = classes.get(cls, 0) + 1
# # for cls, count in sorted(classes.items(), key=lambda x: -x[1])[:20]:
# #     print(f"  [{count}x] .{cls}")

# # # Pagination
# # print("\n=== PAGINATION ===")
# # for tag in soup.find_all(["nav", "div", "ul"], limit=50):
# #     cls = " ".join(tag.get("class", []))
# #     if any(k in cls.lower() for k in ["pag", "page", "nav"]):
# #         print(f"  <{tag.name}> class='{cls}'")
# #         for a in tag.find_all("a", limit=5):
# #             print(f"    → '{a.get_text(strip=True)}' | href={a.get('href')} | data-page={a.get('data-page')}")

# # # Screenshot
# # driver.save_screenshot("debug_screenshot.png")
# # print("\n✅ Screenshot sauvegardé → debug_screenshot.png")

# # # Aperçu HTML brut
# # print("\n=== HTML BRUT (1000 premiers chars) ===")
# # print(driver.page_source[:1000])

# # driver.quit()




# # from selenium import webdriver
# # from selenium.webdriver.chrome.options import Options
# # from selenium.webdriver.chrome.service import Service
# # from selenium.webdriver.common.by import By
# # from selenium.webdriver.support.ui import WebDriverWait
# # from selenium.webdriver.support import expected_conditions as EC
# # from webdriver_manager.chrome import ChromeDriverManager
# # from bs4 import BeautifulSoup
# # import time

# # def get_driver():
# #     options = Options()
# #     options.add_argument("--headless")
# #     options.add_argument("--no-sandbox")
# #     options.add_argument("--disable-dev-shm-usage")
# #     options.add_argument("--window-size=1920,1080")
# #     service = Service(ChromeDriverManager().install())
# #     return webdriver.Chrome(service=service, options=options)

# # driver = get_driver()
# # driver.get("https://sociumjob.com/jobs")
# # time.sleep(5)

# # soup = BeautifulSoup(driver.page_source, "html.parser")

# # # Structure d'une carte offre
# # print("=== 1ère CARTE (w-full space-y-6) ===")
# # card = soup.select_one("div.w-full.space-y-6")
# # if card:
# #     print(card.prettify()[:2000])

# # # Bouton "Voir plus"
# # print("\n=== BOUTON VOIR PLUS ===")
# # for btn in driver.find_elements(By.XPATH, "//*[contains(text(), 'Voir plus')]"):
# #     print(f"  <{btn.tag_name}> | '{btn.text}' | visible={btn.is_displayed()}")

# # # Compter les offres visibles
# # cards = soup.select("div.w-full.space-y-6")
# # print(f"\n=== OFFRES VISIBLES : {len(cards)} ===")

# # driver.quit()





# # from selenium import webdriver
# # from selenium.webdriver.chrome.options import Options
# # from selenium.webdriver.chrome.service import Service
# # from selenium.webdriver.common.by import By
# # from webdriver_manager.chrome import ChromeDriverManager
# # from bs4 import BeautifulSoup
# # import time

# # def get_driver():
# #     options = Options()
# #     options.add_argument("--headless")
# #     options.add_argument("--no-sandbox")
# #     options.add_argument("--disable-dev-shm-usage")
# #     options.add_argument("--window-size=1920,1080")
# #     service = Service(ChromeDriverManager().install())
# #     return webdriver.Chrome(service=service, options=options)

# # driver = get_driver()
# # driver.get("https://afriqueemplois.com/sn")
# # time.sleep(5)

# # # Trouver le bouton et son parent cliquable
# # btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Voir plus')]")
# # parent = btn.find_element(By.XPATH, "..")
# # print(f"=== BOUTON ===")
# # print(f"  Span : tag={btn.tag_name}")
# # print(f"  Parent : tag={parent.tag_name} | class='{parent.get_attribute('class')}'")
# # print(f"  Grand-parent : tag={parent.find_element(By.XPATH, '..').tag_name} | class='{parent.find_element(By.XPATH, '..').get_attribute('class')}'")

# # # Cliquer 3 fois et compter les offres à chaque fois
# # for i in range(3):
# #     try:
# #         btn = driver.find_element(By.XPATH, "//*[contains(text(), \"Voir plus d'offres\")]")
# #         driver.execute_script("arguments[0].click();", btn)
# #         time.sleep(3)
# #         from bs4 import BeautifulSoup
# #         soup = BeautifulSoup(driver.page_source, "html.parser")
# #         cards = soup.select("div.w-full.space-y-6")
# #         print(f"  Après clic {i+1} : {len(cards)} offres")
# #     except Exception as e:
# #         print(f"  Plus de bouton après {i+1} clics : {e}")
# #         break

# # driver.quit()





# # from selenium import webdriver
# # from selenium.webdriver.chrome.options import Options
# # from selenium.webdriver.chrome.service import Service
# # from selenium.webdriver.common.by import By
# # from webdriver_manager.chrome import ChromeDriverManager
# # from bs4 import BeautifulSoup
# # import time

# # def get_driver():
# #     options = Options()
# #     options.add_argument("--headless")
# #     options.add_argument("--no-sandbox")
# #     options.add_argument("--disable-dev-shm-usage")
# #     options.add_argument("--window-size=1920,1080")
# #     service = Service(ChromeDriverManager().install())
# #     return webdriver.Chrome(service=service, options=options)

# # driver = get_driver()
# # driver.get("https://afriqueemplois.com/sn")
# # time.sleep(5)

# # soup = BeautifulSoup(driver.page_source, "html.parser")

# # # Chercher le compteur total d'offres affiché sur la page
# # print("=== COMPTEUR TOTAL ===")
# # for tag in soup.find_all(["p", "span", "h1", "h2", "h3", "div"]):
# #     txt = tag.get_text(strip=True)
# #     if any(k in txt.lower() for k in ["offre", "job", "résultat", "annonce"]) and any(c.isdigit() for c in txt) and len(txt) < 80:
# #         print(f"  '{txt}'")

# # # Cliquer jusqu'à ce que le bouton disparaisse
# # print("\n=== CHARGEMENT COMPLET ===")
# # nb_clics = 0
# # while True:
# #     try:
# #         btn = driver.find_element(By.XPATH, "//*[contains(text(), \"Voir plus d'offres\")]")
# #         driver.execute_script("arguments[0].click();", btn)
# #         nb_clics += 1
# #         time.sleep(3)
# #         soup = BeautifulSoup(driver.page_source, "html.parser")
# #         cards = soup.select("div.w-full.space-y-6")
# #         print(f"  Clic {nb_clics} → {len(cards)} offres chargées")
# #     except Exception:
# #         print(f"  Bouton disparu après {nb_clics} clics")
# #         break

# # soup = BeautifulSoup(driver.page_source, "html.parser")
# # print(f"\n  TOTAL FINAL : {len(soup.select('div.w-full.space-y-6'))} offres")
# # driver.quit()


# # test_structure.py
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from webdriver_manager.chrome import ChromeDriverManager
# from bs4 import BeautifulSoup

# options = Options()
# options.add_argument("--headless")
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# service = Service(ChromeDriverManager().install())
# driver = webdriver.Chrome(service=service, options=options)

# driver.get("https://afriqueemplois.com/sn")

# WebDriverWait(driver, 20).until(
#     lambda d: d.find_elements(By.XPATH, "//a[contains(@href, '/sn/post/')]")
# )

# soup = BeautifulSoup(driver.page_source, "html.parser")

# # Trouver le parent direct de chaque lien /sn/post/
# liens = soup.find_all("a", href=lambda h: h and "/sn/post/" in h)
# print(f"✅ {len(liens)} liens /sn/post/ trouvés\n")

# for i, a in enumerate(liens[:3], 1):
#     parent = a.parent
#     print(f"--- Offre {i} ---")
#     print(f"  <a> classes     : {a.get('class')}")
#     print(f"  parent tag      : {parent.name}")
#     print(f"  parent classes  : {parent.get('class')}")
#     gp = parent.parent
#     print(f"  grand-parent tag     : {gp.name}")
#     print(f"  grand-parent classes : {gp.get('class')}")
#     print()

# driver.quit()

# Lance ça dans un python rapide
import pandas as pd
df = pd.read_csv("../data/dataset_final.csv", encoding="utf-8-sig", low_memory=False)
for col in ["date_publication_clean","date_clean","date_publication","date","date_limite_clean"]:
    if col in df.columns:
        n = pd.to_datetime(df[col], errors="coerce", dayfirst=True).notna().sum()
        print(f"{col:<30} → {n:,} dates valides")