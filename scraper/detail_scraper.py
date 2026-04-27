"""
detail_scraper.py — Scrape les descriptions des offres d'emploi
================================================================
Lit merged_offres.csv, visite chaque lien et extrait la description
complète selon le sélecteur propre à chaque source.

Sources gérées :
  afriqueemplois  → div contenant la description de l'offre
  concoursn       → div.entry-content
  emploidakar     → div.job_description
  expatdakar      → div.description / div.listing-description
  optioncarriere  → div.col-sm-8 / section.job-description
  senego          → div.card-body
  senejobs        → div.job-description / div.description
  senjob          → div#offre_desc / div.job-detail

Sources ignorées (pas de lien) :
  linkedin        → lien N/A
  sociumjob       → lien N/A

Robustesse :
  - Checkpoint CSV   → reprend là où on s'est arrêté
  - Retry exponentiel sur erreurs réseau
  - Délai entre requêtes par source (respecter les serveurs)
  - Sauvegarde toutes les 50 offres
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re

# ─── Chemins ─────────────────────────────────────────────────────────────────

INPUT_FILE      = "data/merged_offres.csv"
OUTPUT_FILE     = "data/merged_with_desc.csv"
CHECKPOINT_FILE = "data/detail_checkpoint.csv"

# ─── Headers HTTP ────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# ─── Délai entre requêtes par source (secondes) ───────────────────────────────
# Plus lent sur les sites fragiles, plus rapide sur les robustes

DELAY_PAR_SOURCE = {
    "afriqueemplois": 1.5,
    "concoursn":      1.0,
    "emploidakar":    1.5,
    "expatdakar":     1.5,
    "optioncarriere": 1.5,
    "senego":         1.5,
    "senejobs":       1.5,
    "senjob":         1.5,
}

# ─── Sources sans lien → on saute directement ────────────────────────────────

SOURCES_SANS_LIEN = {"linkedin", "sociumjob"}

# ─── Sélecteurs CSS par source ────────────────────────────────────────────────
# Liste ordonnée : on essaie dans l'ordre et on prend le premier qui matche

SELECTEURS = {
    "afriqueemplois": [
        "div.prose",
        "div.description",
        "div.job-description",
        "div.content",
        "main",
    ],
    "concoursn": [
        "div.entry-content",
        "div.post-content",
        "article div.content",
    ],
    "emploidakar": [
        "div.job_description",
        "div.description",
        "div#job-description",
        "div.content-job",
    ],
    "expatdakar": [
        "div.description",
        "div.listing-description",
        "div.annonce-description",
        "div.content",
    ],
    "optioncarriere": [
        "div.col-sm-8 div.content",
        "section.job-description",
        "div.jobad-desc",
        "div#job-description",
        "div.content",
    ],
    "senego": [
        "div.card-body",
        "div.post-content",
        "div.entry-content",
        "article",
    ],
    "senejobs": [
        "div.job-description",
        "div.description",
        "div.content",
        "div#job-detail",
    ],
    "senjob": [
        "div#offre_desc",
        "div.job-detail",
        "div.description",
        "div.content",
    ],
}


# ─── Récupération d'une page (retry exponentiel) ─────────────────────────────

def get_page(url: str, retries: int = 4) -> BeautifulSoup | None:
    """Récupère une page avec backoff exponentiel."""
    wait = 5
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            short_err = str(e)[:80]
            print(f"    ⚠️  Tentative {attempt+1}/{retries} : {short_err}")
            if attempt < retries - 1:
                print(f"    ⏳ Attente {wait}s...")
                time.sleep(wait)
                wait *= 2
    return None


# ─── Extraction de la description ────────────────────────────────────────────

def extraire_description(soup: BeautifulSoup, source: str) -> str:
    """
    Applique les sélecteurs dans l'ordre jusqu'à trouver du contenu.
    Retourne le texte nettoyé ou 'N/A'.
    """
    selecteurs = SELECTEURS.get(source, [])

    for sel in selecteurs:
        bloc = soup.select_one(sel)
        if bloc:
            # Supprimer les scripts/styles inclus dans le bloc
            for tag in bloc.find_all(["script", "style", "noscript"]):
                tag.decompose()
            texte = bloc.get_text(separator=" ", strip=True)
            texte = re.sub(r"\s+", " ", texte).strip()
            if len(texte) > 50:   # ignorer les blocs trop courts
                return texte[:3000]   # limiter à 3000 caractères

    return "N/A"


# ─── Checkpoint ──────────────────────────────────────────────────────────────

def charger_checkpoint() -> set:
    """Retourne l'ensemble des liens déjà traités."""
    if os.path.exists(CHECKPOINT_FILE):
        df = pd.read_csv(CHECKPOINT_FILE, encoding="utf-8-sig")
        liens = set(df["lien"].dropna().tolist())
        print(f"  ♻️  Checkpoint : {len(liens)} offres déjà traitées")
        return liens
    return set()


def sauvegarder(rows: list):
    """Sauvegarde les lignes dans le checkpoint (append si existe)."""
    if not rows:
        return
    df_new = pd.DataFrame(rows)
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CHECKPOINT_FILE):
        df_new.to_csv(CHECKPOINT_FILE, mode="a", header=False,
                      index=False, encoding="utf-8-sig")
    else:
        df_new.to_csv(CHECKPOINT_FILE, index=False, encoding="utf-8-sig")


# ─── Scraper principal ────────────────────────────────────────────────────────

def scrape_descriptions(batch_size: int = 50):
    """
    Parcourt merged_offres.csv, visite chaque lien et enrichit
    la colonne 'description_complete'.

    Args:
        batch_size: sauvegarde tous les N offres traitées
    """
    print("\n" + "=" * 60)
    print("  🔍 DETAIL SCRAPER — descriptions complètes")
    print("=" * 60)

    # ── Charger les offres ────────────────────────────────────────────────────
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Fichier introuvable : {INPUT_FILE}")
        print("   → Lance d'abord : python fusion.py")
        return

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    print(f"  📂 {len(df)} offres chargées depuis {INPUT_FILE}")

    # ── Charger le checkpoint ─────────────────────────────────────────────────
    deja_traites = charger_checkpoint()

    # ── Filtrer les offres à traiter ──────────────────────────────────────────
    # Ignorer : liens N/A, sources sans lien, déjà traités
    mask_valide = (
        df["lien"].notna() &
        (df["lien"] != "N/A") &
        (~df["source"].isin(SOURCES_SANS_LIEN)) &
        (~df["lien"].isin(deja_traites))
    )
    a_traiter = df[mask_valide].copy()
    ignores   = len(df) - len(a_traiter) - len(deja_traites.intersection(set(df["lien"])))

    print(f"  ✅ À traiter    : {len(a_traiter)}")
    print(f"  ♻️  Déjà faits  : {len(deja_traites)}")
    print(f"  ⏭️  Ignorés     : {len(df[~mask_valide & ~df['lien'].isin(deja_traites)])} "
          f"(liens N/A ou sources sans lien)")

    # ── Boucle principale ─────────────────────────────────────────────────────
    batch     = []
    traites   = 0
    erreurs   = 0

    for i, (idx, row) in enumerate(a_traiter.iterrows(), 1):
        source = str(row.get("source", "")).strip()
        lien   = str(row.get("lien", "")).strip()
        titre  = str(row.get("titre", ""))[:60]

        print(f"\n  [{i}/{len(a_traiter)}] {titre}")
        print(f"  → {lien}")

        # Récupérer la page
        soup = get_page(lien)

        if soup:
            desc = extraire_description(soup, source)
            print(f"  ✓ {len(desc)} caractères extraits")
        else:
            desc = "ERREUR_RESEAU"
            erreurs += 1
            print(f"  ✗ Échec réseau")

        # Construire la ligne enrichie
        enriched = row.to_dict()
        enriched["description_complete"] = desc
        batch.append(enriched)
        traites += 1

        # Sauvegarde par batch
        if traites % batch_size == 0:
            sauvegarder(batch)
            batch = []
            print(f"\n  💾 Checkpoint sauvegardé ({traites} traitées, {erreurs} erreurs)")

        # Délai par source
        delay = DELAY_PAR_SOURCE.get(source, 1.5)
        time.sleep(delay)

    # Sauvegarder le reste
    if batch:
        sauvegarder(batch)

    # ── Fusion checkpoint + offres ignorées ───────────────────────────────────
    print(f"\n{'='*60}")
    print("  📦 Fusion finale...")

    # Offres avec description (checkpoint)
    if os.path.exists(CHECKPOINT_FILE):
        df_desc = pd.read_csv(CHECKPOINT_FILE, encoding="utf-8-sig")
    else:
        df_desc = pd.DataFrame()

    # Offres sans lien / sources ignorées → description_complete = N/A
    df_sans_lien = df[
        df["lien"].isna() |
        (df["lien"] == "N/A") |
        df["source"].isin(SOURCES_SANS_LIEN)
    ].copy()
    df_sans_lien["description_complete"] = "N/A"

    # Fusionner tout
    df_final = pd.concat([df_desc, df_sans_lien], ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["lien"]).reset_index(drop=True)

    os.makedirs("data", exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"  ✅ {len(df_final)} offres sauvegardées → {OUTPUT_FILE}")
    print(f"  📊 Avec description : {(df_final['description_complete'] != 'N/A').sum()}")
    print(f"  📊 Sans description : {(df_final['description_complete'] == 'N/A').sum()}")
    print(f"  📊 Erreurs réseau   : {(df_final['description_complete'] == 'ERREUR_RESEAU').sum()}")
    print(f"{'='*60}\n")


# ─── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape les descriptions complètes des offres d'emploi"
    )
    parser.add_argument(
        "--batch", type=int, default=50,
        help="Sauvegarder tous les N offres (défaut: 50)"
    )
    parser.add_argument(
        "--no-resume", action="store_true",
        help="Ignorer le checkpoint et tout retraiter"
    )
    args = parser.parse_args()

    if args.no_resume and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("  🗑️  Checkpoint supprimé — démarrage depuis zéro")

    scrape_descriptions(batch_size=args.batch)