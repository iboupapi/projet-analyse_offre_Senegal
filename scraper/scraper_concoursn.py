"""
scraper_concoursn.py — Scraper concoursn.com/category/senegal/recrutement-senegal/
Structure :
  - Chaque offre  : article.vce-post (dans div.vce-loop-wrap)
  - Titre         : h2.entry-title > a (texte)
  - Lien          : h2.entry-title > a (href)
  - Entreprise    : extrait du titre via regex
  - Tags          : classes CSS de l'article (tag-xxx)
Pagination : Lien statique <a href=".../page/N/"> dans nav#vce-pagination
             → Pas de JS, pas de Selenium — requests suffit
             → Détection de fin : plus de lien "Voir Plus" dans la page

Robustesse :
  - Sauvegarde CSV après chaque page  → aucune perte de données si crash
  - Reprise automatique               → repart de la dernière page sauvegardée
  - Retry exponentiel (5s→10s→20s→40s→80s) sur les erreurs réseau
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os

BASE_URL        = "https://concoursn.com/category/senegal/recrutement-senegal/"
CHECKPOINT_FILE = "data/concoursn_checkpoint.csv"   # sauvegarde page par page
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}
DELAY = 1.5   # secondes entre chaque page (respecter le serveur)


# ─── Récupération d'une page (retry exponentiel) ─────────────────────────────

def get_page(url: str, retries: int = 5) -> BeautifulSoup | None:
    """
    Récupère une page avec retry exponentiel.
    En cas de coupure réseau (NameResolutionError, timeout) on attend
    plus longtemps avant de réessayer plutôt que d'abandonner.

    Délais : 5s → 10s → 20s → 40s → 80s
    """
    wait = 5
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"  ⚠️  Tentative {attempt+1}/{retries} échouée : {e}")
            if attempt < retries - 1:
                print(f"  ⏳ Attente {wait}s avant réessai...")
                time.sleep(wait)
                wait *= 2   # backoff exponentiel
    print(f"  ❌ Abandon après {retries} tentatives : {url}")
    return None


# ─── Checkpoint : sauvegarde & reprise ───────────────────────────────────────

def sauvegarder_checkpoint(offres: list, path: str):
    """Sauvegarde toutes les offres collectées jusqu'ici dans un CSV."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df = pd.DataFrame(offres)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def charger_checkpoint(path: str) -> tuple[list, int, str]:
    """
    Charge le checkpoint existant et retourne :
      - la liste des offres déjà collectées
      - le numéro de la prochaine page à scraper
      - l'URL de la prochaine page

    Si pas de checkpoint → repart de la page 1.
    """
    if not os.path.exists(path):
        return [], 1, BASE_URL

    df = pd.read_csv(path, encoding="utf-8-sig")
    offres = df.to_dict(orient="records")

    # Retrouver la dernière page sauvegardée depuis la colonne "page_scraped"
    if "page_scraped" in df.columns and not df.empty:
        last_page = int(df["page_scraped"].max())
        next_page = last_page + 1
        next_url  = (
            BASE_URL if next_page == 1
            else f"https://concoursn.com/category/senegal/recrutement-senegal/page/{next_page}/"
        )
        print(f"  ♻️  Checkpoint trouvé : {len(offres)} offres, reprise à la page {next_page}")
        return offres, next_page, next_url

    return offres, 1, BASE_URL


# ─── Extraction de l'entreprise depuis le titre ───────────────────────────────

def extraire_entreprise(titre: str) -> str:
    """Tente d'extraire le nom de l'entreprise depuis le titre."""
    m = re.match(r"^(.+?)\s+(?:recrute?s?|recherche?|offre)\b", titre, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return "N/A"


# ─── Parsing d'une page de liste ─────────────────────────────────────────────

def parser_page(soup: BeautifulSoup, page_num: int) -> list:
    """
    Extrait toutes les offres d'une page de liste.

    Structure HTML :
        <div class="vce-loop-wrap">
          <article class="vce-post ... tag-xxx tag-yyy">
            <header class="entry-header">
              <h2 class="entry-title">
                <a href="https://concoursn.com/..." title="...">Titre</a>
              </h2>
            </header>
          </article>
        </div>
    """
    offres = []

    loop_wrap = soup.find("div", class_="vce-loop-wrap")
    if not loop_wrap:
        print("  ⚠️  Pas de vce-loop-wrap trouvé sur cette page")
        return offres

    articles = loop_wrap.find_all("article", class_=re.compile(r"vce-post"))

    for article in articles:
        a_tag = article.select_one("h2.entry-title a")
        if not a_tag:
            continue

        titre      = a_tag.get_text(strip=True)
        lien       = a_tag.get("href", "N/A")
        entreprise = extraire_entreprise(titre)

        classes = article.get("class", [])

        tags = [
            cls.replace("tag-", "").replace("-", " ")
            for cls in classes if cls.startswith("tag-")
        ]

        categories = [
            cls.replace("category-", "").replace("-", " ")
            for cls in classes if cls.startswith("category-")
        ]

        post_id = "N/A"
        for cls in classes:
            m = re.match(r"^post-(\d+)$", cls)
            if m:
                post_id = m.group(1)
                break

        offres.append({
            "titre":        titre,
            "entreprise":   entreprise,
            "tags":         ", ".join(tags) if tags else "N/A",
            "categorie":    ", ".join(categories) if categories else "N/A",
            "post_id":      post_id,
            "lien":         lien,
            "page_scraped": page_num,   # ← pour la reprise automatique
            "source":       "concoursn.com",
        })
        print(f"  ✓ {titre[:60]:<60} | {entreprise[:25]}")

    return offres


# ─── Récupération du lien "Voir Plus" ────────────────────────────────────────

def get_next_url(soup: BeautifulSoup) -> str | None:
    """Récupère l'URL de la page suivante depuis nav#vce-pagination."""
    nav = soup.find("nav", id="vce-pagination")
    if nav:
        a = nav.find("a", href=True)
        if a:
            return a["href"]
    return None


# ─── Scraper principal ────────────────────────────────────────────────────────

def scrape_concoursn(max_pages: int = 3000, resume: bool = True) -> pd.DataFrame:
    """
    Scrape toutes les offres de recrutement sur concoursn.com.

    Args:
        max_pages : nombre maximum de pages (défaut: 3000)
        resume    : reprendre depuis le checkpoint si True (défaut: True)

    Returns:
        DataFrame pandas avec toutes les offres dédupliquées.
    """
    print("\n" + "=" * 55)
    print("  🌐 SCRAPER CONCOURSN.COM")
    print("=" * 55)

    # ── Chargement du checkpoint ──────────────────────────────────────────────
    if resume:
        all_offres, page_num, url = charger_checkpoint(CHECKPOINT_FILE)
    else:
        all_offres, page_num, url = [], 1, BASE_URL
        print("  🆕 Démarrage depuis zéro (--no-resume)")

    # ── Boucle de scraping ────────────────────────────────────────────────────
    while url:
        print(f"\n  📄 Page {page_num} — {url}")

        soup = get_page(url)
        if not soup:
            # Échec définitif après tous les retries → sauvegarder et arrêter
            print(f"\n  💾 Sauvegarde d'urgence avant arrêt...")
            sauvegarder_checkpoint(all_offres, CHECKPOINT_FILE)
            print(f"  ✅ {len(all_offres)} offres sauvegardées dans {CHECKPOINT_FILE}")
            print(f"  ▶️  Relancez le script pour reprendre à la page {page_num}")
            break

        offres = parser_page(soup, page_num)
        print(f"  ✅ {len(offres)} offres extraites — total cumulé : {len(all_offres) + len(offres)}")
        all_offres.extend(offres)

        # Sauvegarde après chaque page
        sauvegarder_checkpoint(all_offres, CHECKPOINT_FILE)

        # Limite max_pages
        if max_pages and page_num >= max_pages:
            print(f"\n  ⏹️  Limite de {max_pages} page(s) atteinte")
            break

        # Page suivante
        next_url = get_next_url(soup)
        if not next_url:
            print("\n  🔚 Dernière page atteinte — plus de lien 'Voir Plus'")
            break

        url = next_url
        page_num += 1
        time.sleep(DELAY)

    # ── Déduplication finale ──────────────────────────────────────────────────
    cols = ["titre", "entreprise", "tags", "categorie", "post_id",
            "lien", "page_scraped", "source"]
    df = pd.DataFrame(all_offres) if all_offres else pd.DataFrame(columns=cols)
    df = df.drop_duplicates(subset=["lien"]).reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  ✅ {len(df)} offres uniques — concoursn.com")
    print(f"{'='*55}\n")
    return df


# ─── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scraper concoursn.com — Offres de recrutement Sénégal"
    )
    parser.add_argument(
        "--pages", type=int, default=3000,
        help="Nombre max de pages à scraper (défaut: 3000)"
    )
    parser.add_argument(
        "--output", type=str, default="data/concoursn_raw",
        help="Chemin de sortie sans extension (défaut: data/concoursn_raw)"
    )
    parser.add_argument(
        "--format", choices=["csv", "json", "both"], default="csv",
        help="Format de sortie (défaut: csv)"
    )
    parser.add_argument(
        "--no-resume", action="store_true",
        help="Ignorer le checkpoint et repartir de zéro"
    )
    args = parser.parse_args()

    df = scrape_concoursn(max_pages=args.pages, resume=not args.no_resume)

    if df.empty:
        print("⚠️  Aucune offre trouvée.")
    else:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

        if args.format in ("csv", "both"):
            csv_path = args.output + ".csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"📁 CSV sauvegardé → {csv_path}")

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
        print(f"  Offres totales     : {len(df)}")
        print(f"  Entreprises uniques: {df['entreprise'].nunique()}")
        print(f"  Pages scrapées     : {df['page_scraped'].max():.0f}")
        print(f"\n  Aperçu :")
        print(df[["titre", "entreprise", "tags"]].head(10).to_string())