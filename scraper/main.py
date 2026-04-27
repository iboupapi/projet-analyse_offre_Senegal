"""
============================================================
main.py — Orchestrateur du pipeline de scraping
------------------------------------------------------------
Objectif  : Lancer tous les scrapers en séquence, puis
            fusionner leurs résultats dans un seul fichier
            CSV consolidé.

Pourquoi un orchestrateur séparé ?
    Chaque scraper est indépendant et peut être lancé seul
    pour tester ou déboguer un seul site. Ce fichier sert
    de point d'entrée unique quand on veut tout scraper
    d'un coup.

Fonctionnement :
    1. Exécute chaque scraper comme un sous-processus Python
       indépendant (subprocess.run). Cela isole les erreurs :
       si un scraper plante, les autres continuent.
    2. Appelle fusion_csv() pour consolider tous les fichiers
       *_raw.csv générés.

Usage :
    python main.py

Sortie :
    data/merged_offres.csv — toutes les offres fusionnées
============================================================
"""

import subprocess  # Exécution de scripts Python en sous-processus
import sys         # Accès à l'interpréteur Python courant (sys.executable)
import os          # Manipulation des chemins de fichiers

# Import de la fonction de fusion depuis le module dédié
from fusion import fusion_csv


# ─────────────────────────────────────────────────────────
# LISTE DES SCRAPERS À EXÉCUTER
# ─────────────────────────────────────────────────────────

# Chaque entrée correspond au nom d'un fichier scraper dans
# le même dossier. Pour ajouter un nouveau site, il suffit
# d'ajouter son fichier ici.
SCRAPERS = [
    "scraper_emploidakar.py",      # emploidakar.com    (~68 offres)
    "scraper_expatdakar.py",       # expat-dakar.com    (~? offres)
    "scraper_optioncarriere.py",   # optioncarriere.sn  (~394 offres)
    "scraper_senego.py",           # annonces.senego.com(~384 offres)
    "scraper_senjob.py",           # senjob.com         (~231 offres)
    "scraper_linkedin.py",         # linkedin.com       (~? offres)
    "scraper_sociumjob.py",        # sociumjob.com      (~? offres)
    # "scraper_nouveausite.py",    ← décommenter pour ajouter un site
]


# ─────────────────────────────────────────────────────────
# EXÉCUTION D'UN SCRAPER
# ─────────────────────────────────────────────────────────

def run_scraper(script: str):
    """
    Lance un scraper en tant que sous-processus Python indépendant.

    Avantages de subprocess vs import direct :
    - Isolation : une erreur dans un scraper ne bloque pas les autres
    - Mémoire   : chaque scraper libère sa mémoire (navigateur Chrome)
                  à la fin de son exécution
    - Clarté    : les logs de chaque scraper s'affichent en temps réel

    Args:
        script : Nom du fichier scraper (ex: "scraper_senjob.py")
    """
    print(f"\n{'='*50}")
    print(f"  Lancement : {script}")
    print(f"{'='*50}")

    result = subprocess.run(
        # sys.executable : utilise le même Python que main.py
        # (important dans les environnements virtuels)
        [sys.executable, os.path.join(os.path.dirname(__file__), script)],
        capture_output=False  # Affiche les logs en temps réel dans le terminal
    )

    # Signalement si le scraper s'est terminé avec une erreur
    # (code de retour non nul = erreur)
    if result.returncode != 0:
        print(f"    {script} s'est terminé avec le code {result.returncode}")


# ─────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────

def main():
    """
    Pipeline complet : scraping de tous les sites + fusion.

    Étapes :
    1. Lancer chaque scraper de la liste SCRAPERS
       → chacun génère son fichier data/*_raw.csv
    2. Appeler fusion_csv() pour fusionner tous les CSV
       → génère data/merged_offres.csv
    """
    print(" Démarrage du pipeline de scraping multi-sources\n")

    # ── Étape 1 : Scraping de chaque site ───────────────
    for scraper in SCRAPERS:
        run_scraper(scraper)

    # ── Étape 2 : Fusion de tous les CSV ────────────────
    print("\n\n Fusion des fichiers CSV...")
    df = fusion_csv()

    print(f"\n Pipeline terminé ! {len(df)} offres consolidées dans merged_offres.csv")


# ─────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()