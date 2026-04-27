"""
scraper_afriqueemplois.py — Scraper afriqueemplois.com/sn
Structure :
  - Chaque offre  : div.bg-white.rounded-2xl.shadow-sm (carte emploi)
  - Titre         : h3 (dans la carte)
  - Entreprise    : texte après "Entreprise :"
  - Lieu          : texte après "Lieu :"
  - Contrat       : texte après "Type de contrat :"
  - Salaire       : texte après "Salaire :"
  - Date limite   : texte après "Date limite :"
  - Exclusif      : badge bg-gradient présent ou non
  - Lien          : parent <a> de la carte
Pagination : Bouton "Charger plus" (id="load-more", data-page=N)
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
import re
import time
import os

BASE_URL = "https://afriqueemplois.com/sn"


# ─── Driver ───────────────────────────────────────────────────────────────────

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


# ─── Chargement de toutes les offres ─────────────────────────────────────────

def charger_toutes_les_offres(driver, max_clics: int = None) -> BeautifulSoup:
    """
    Charge toutes les offres en cliquant sur 'Charger plus'
    jusqu'à ce que le bouton disparaisse ou que le nombre d'offres
    n'augmente plus (plateau).

    Stratégie anti-boucle infinie :
    - Si le nombre d'offres n'augmente pas pendant 2 clics consécutifs
      → on considère que tout est chargé et on s'arrête.

    Args:
        max_clics: limite optionnelle du nombre de clics (None = illimité)
    """
    print(f"\n  📄 Chargement de {BASE_URL}")
    driver.get(BASE_URL)

    # Attendre que les offres soient réellement rendues dans le DOM
    print("  ⏳ Attente du rendu des offres...")
    for _ in range(20):                          # max 20s
        time.sleep(1)
        soup_check = BeautifulSoup(driver.page_source, "html.parser")
        if soup_check.find("a", href=re.compile(r"/sn/post/\d+")):
            print("  ✅ Offres détectées dans le DOM")
            break
    else:
        print("  ⚠️  Timeout : aucune offre détectée après 20s — on continue quand même")

    nb_precedent = 0
    nb_stable    = 0       # Compteur de clics sans changement
    MAX_STABLE   = 2       # Arrêt après 2 clics sans nouvelles offres
    clic         = 0

    while True:
        soup      = BeautifulSoup(driver.page_source, "html.parser")
        # Compter uniquement les vraies offres (lien /sn/post/) — pas les catégories
        nb_actuel = len([
            c for c in soup.select("article.bg-white.rounded-2xl.shadow-sm")
            if c.find("a", href=re.compile(r"/sn/post/\d+"))
        ])

        if nb_actuel == nb_precedent:
            nb_stable += 1
            if nb_stable >= MAX_STABLE:
                print(f"  🔚 Plateau atteint : {nb_actuel} offres (arrêt après {clic} clics)")
                break
        else:
            nb_stable    = 0
            nb_precedent = nb_actuel

        # Limite optionnelle
        if max_clics is not None and clic >= max_clics:
            print(f"  ⏹️  Limite de {max_clics} clic(s) atteinte — {nb_actuel} offres chargées")
            break

        # Chercher et cliquer sur le bouton "Charger plus"
        try:
            btn = driver.find_element(By.ID, "load-more")
            # Vérifier que le bouton est visible et actif
            if not btn.is_displayed() or not btn.is_enabled():
                print(f"  🔚 Bouton désactivé — fin du chargement ({nb_actuel} offres)")
                break
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", btn)
            clic += 1
            print(f"  🔄 Clic {clic} → {nb_actuel} offres chargées")
            time.sleep(3)
        except Exception:
            print(f"  🔚 Bouton introuvable après {clic} clics — fin du chargement")
            break

    return BeautifulSoup(driver.page_source, "html.parser")


# ─── Parsing des offres ───────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Nettoie et normalise un texte."""
    return re.sub(r"\s+", " ", text.strip()) if text else ""


def extract_field(pattern: str, text: str) -> str:
    """Extrait un champ via regex dans du texte brut."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else "N/A"


def parser_offres(soup: BeautifulSoup) -> list:
    """
    Extrait les données de toutes les cartes d'offres.

    Structure HTML d'une carte afriqueemplois :
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden ...">
          <a href="/sn/post/XXXXX">
            <img src="...">
            <div>
              <h3>Titre du poste</h3>
              <span class="bg-gradient...">EXCLUSIF</span>   ← optionnel
              Entreprise: ... Lieu: ... Type de contrat: ...
              Salaire: ... Date limite: DD/MM/YYYY
            </div>
          </a>
        </div>
    """
    all_cards = soup.select("article.bg-white.rounded-2xl.shadow-sm")

    # ── Garder uniquement les vraies offres d'emploi ──────────────────────────
    # Les cartes de catégories ont un lien /sn/category/... — on les ignore.
    # Les offres ont un lien /sn/post/XXXXX.
    cards = [
        c for c in all_cards
        if c.find("a", href=re.compile(r"/sn/post/\d+"))
    ]
    print(f"  🔍 {len(cards)} offre(s) à parser ({len(all_cards) - len(cards)} carte(s) ignorée(s))")

    offres = []
    for card in cards:

        # --- Titre ---
        h3 = card.find("h3")
        titre = clean(h3.get_text()) if h3 else "N/A"

        # --- Lien : <a href="/sn/post/..."> ---
        lien = "N/A"
        a_tag = card.find("a", href=re.compile(r"/sn/post/\d+"))
        if a_tag:
            href = a_tag["href"]
            lien = href if href.startswith("http") else "https://afriqueemplois.com" + href

        # --- Image ---
        img = card.find("img")
        image = img["src"] if img and img.get("src") else "N/A"

        # --- Badge EXCLUSIF ---
        exclusif = False
        for badge in card.find_all(class_=re.compile(r"bg-gradient")):
            if "EXCLUSIF" in badge.get_text():
                exclusif = True
                break

        # --- Niveau (ex: "Niveau BAC+5") ---
        niveau = "N/A"
        for span in card.find_all("span"):
            txt = clean(span.get_text())
            if re.match(r"Niveau\s+BAC", txt, re.I):
                niveau = txt
                break

        # --- Texte brut du lien pour extraction des champs structurés ---
        raw = clean(a_tag.get_text()) if a_tag else ""

        entreprise  = extract_field(r"Entreprise\s*:\s*(.+?)(?:Lieu\s*:|$)",              raw)
        lieu        = extract_field(r"Lieu\s*:\s*(.+?)(?:Type de contrat\s*:|$)",         raw)
        contrat     = extract_field(r"Type de contrat\s*:\s*(.+?)(?:Salaire\s*:|$)",      raw)
        salaire     = extract_field(r"Salaire\s*:\s*(.+?)(?:Date limite\s*:|$)",          raw)
        date_limite = extract_field(r"Date limite\s*:\s*(\d{2}/\d{2}/\d{4})",            raw)

        # --- Description courte (texte après la date limite) ---
        description = "N/A"
        m = re.search(r"\d{2}/\d{2}/\d{4}\s*(.+)", raw)
        if m:
            desc = re.sub(r"\b\d{1,5}\b", "", m.group(1))  # supprimer compteurs
            desc = re.sub(r"Voir plus",   "", desc)
            description = clean(desc)[:300] or "N/A"

        if titre != "N/A":
            offres.append({
                "titre":       titre,
                "entreprise":  entreprise,
                "lieu":        lieu,
                "contrat":     contrat,
                "salaire":     salaire,
                "date_limite": date_limite,
                "exclusif":    exclusif,
                "niveau":      niveau,
                "description": description,
                "lien":        lien,
                "image":       image,
                "source":      "afriqueemplois.com/sn",
            })
            print(f"  ✓ {titre[:50]:<50} | {lieu:<15} | {contrat:<10} | {date_limite}")

    return offres


# ─── Scraper principal ────────────────────────────────────────────────────────

def scrape_afriqueemplois(max_clics: int = None) -> pd.DataFrame:
    """
    Lance le scraping complet de afriqueemplois.com/sn.

    Args:
        max_clics: nombre maximum de clics sur "Charger plus" (None = illimité)

    Returns:
        DataFrame pandas avec toutes les offres dédupliquées.
    """
    print("\n" + "=" * 55)
    print("  🌐 SCRAPER AFRIQUEEMPLOIS.COM/SN")
    print("=" * 55)

    driver = get_driver()
    try:
        soup = charger_toutes_les_offres(driver, max_clics=max_clics)
    finally:
        driver.quit()
        print("\n  🔒 Driver fermé")

    offres = parser_offres(soup)

    cols = ["titre", "entreprise", "lieu", "contrat", "salaire",
            "date_limite", "exclusif", "niveau", "description", "lien",
            "image", "source"]

    df = pd.DataFrame(offres) if offres else pd.DataFrame(columns=cols)
    # df = df.drop_duplicates(subset=["titre", "lieu"]).reset_index(drop=True)

    print(f"\n  ✅ {len(df)} offres uniques — afriqueemplois.com/sn")
    return df


# ─── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scraper afriqueemplois.com/sn — Offres d'emploi Sénégal"
    )
    parser.add_argument(
        "--clics", type=int, default=None,
        help="Nombre max de clics sur 'Charger plus' (défaut: illimité)"
    )
    parser.add_argument(
        "--output", type=str, default="data/afriqueemplois_raw",
        help="Chemin de sortie sans extension (défaut: data/afriqueemplois_raw)"
    )
    parser.add_argument(
        "--format", choices=["csv", "json", "both"], default="csv",
        help="Format de sortie (défaut: csv)"
    )
    args = parser.parse_args()

    df = scrape_afriqueemplois(max_clics=args.clics)

    if df.empty:
        print("⚠️  Aucune offre trouvée. Vérifiez votre connexion ou la structure du site.")
    else:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

        if args.format in ("csv", "both"):
            csv_path = args.output + ".csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"\n📁 CSV sauvegardé → {csv_path}")

        if args.format in ("json", "both"):
            import json
            from datetime import datetime
            json_path = args.output + ".json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "source":     BASE_URL,
                        "scraped_at": datetime.now().isoformat(),
                        "total":      len(df),
                        "offres":     df.to_dict(orient="records"),
                    },
                    f, ensure_ascii=False, indent=2,
                )
            print(f"📁 JSON sauvegardé → {json_path}")

        print(f"\n📊 Stats :")
        print(f"  Offres totales  : {len(df)}")
        print(f"  Villes uniques  : {df['lieu'].nunique()}")
        print(f"  Offres exclusif : {df['exclusif'].sum()}")
        print(f"  Contrats        : {df['contrat'].value_counts().head().to_dict()}")
        print(f"\n  Aperçu :")
        print(df[["titre", "lieu", "contrat", "date_limite"]].head(10).to_string())