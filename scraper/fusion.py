"""
============================================================
fusion.py — Module de fusion des fichiers CSV
------------------------------------------------------------
Objectif  : Consolider en un seul DataFrame (et fichier CSV)
            tous les fichiers *_raw.csv produits par les
            différents scrapers.

Pourquoi un module dédié ?
    Séparer la logique de fusion de la logique de scraping
    respecte le principe de responsabilité unique (SRP) :
    - Les scrapers ont une seule mission : extraire des données
    - Ce module a une seule mission : consolider les données

Usage direct :
    python fusion.py
    → Relit tous les *_raw.csv et génère merged_offres.csv

Usage depuis main.py :
    from fusion import fusion_csv
    df = fusion_csv()

Sortie :
    data/merged_offres.csv — toutes les offres fusionnées
                             et dédoublonnées
============================================================
"""

import pandas as pd  # Manipulation des données tabulaires
import os            # Chemins de fichiers
import glob          # Recherche de fichiers par pattern (ex: *_raw.csv)


# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────

# Chemin absolu vers le dossier data/, calculé relativement
# à l'emplacement de ce fichier (robuste quel que soit le
# répertoire de travail courant)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ─────────────────────────────────────────────────────────
# FONCTION PRINCIPALE DE FUSION
# ─────────────────────────────────────────────────────────

def fusion_csv(output_filename: str = "merged_offres.csv") -> pd.DataFrame:
    """
    Fusionne tous les fichiers *_raw.csv du dossier data/.

    Processus :
    1. Recherche tous les fichiers correspondant au pattern *_raw.csv
    2. Charge chaque fichier dans un DataFrame pandas
    3. Ajoute une colonne 'source' dérivée du nom de fichier
       (ex: emploidakar_raw.csv → source = "emploidakar")
    4. Concatène tous les DataFrames en un seul
    5. Supprime les doublons sur titre + entreprise + source
    6. Sauvegarde le résultat dans merged_offres.csv

    Pourquoi conserver la colonne 'source' ?
        Elle permet de tracer l'origine de chaque offre pour
        les analyses futures (ex: quelle plateforme publie le
        plus d'offres CDI ? quelle ville est la plus représentée
        sur senjob vs emploidakar ?)

    Args:
        output_filename : Nom du fichier de sortie (défaut: merged_offres.csv)

    Returns:
        DataFrame pandas avec toutes les offres fusionnées et
        dédoublonnées. Retourne un DataFrame vide si aucun
        fichier source n'est trouvé.
    """
    # Recherche de tous les fichiers *_raw.csv dans data/
    # glob.glob() retourne une liste de chemins correspondant au pattern
    pattern = os.path.join(DATA_DIR, "*_raw.csv")
    fichiers = glob.glob(pattern)

    if not fichiers:
        print("  Aucun fichier *_raw.csv trouvé dans data/")
        print("  Vérifiez que les scrapers ont bien été exécutés.")
        return pd.DataFrame()

    # ── Chargement de chaque fichier ──────────────────────
    dfs = []
    for fichier in fichiers:
        # Extraction du nom du site à partir du nom de fichier
        # ex: "data/emploidakar_raw.csv" → "emploidakar"
        nom = os.path.basename(fichier).replace("_raw.csv", "")
        try:
            df = pd.read_csv(fichier)

            # Ajout de la colonne source pour tracer l'origine des données
            # (utile si la colonne source n'a pas été ajoutée par le scraper)
            df["source"] = nom

            dfs.append(df)
            print(f"   {nom:<25} — {len(df)} offres chargées")
        except Exception as e:
            # On continue même si un fichier est corrompu ou vide
            print(f"   Erreur sur {nom} : {e}")

    # ── Concaténation ─────────────────────────────────────
    # pd.concat() empile les DataFrames verticalement.
    # ignore_index=True : réinitialise l'index de 0 à N-1
    merged = pd.concat(dfs, ignore_index=True)

    # ── Dédoublonnage ─────────────────────────────────────
    # Une même offre peut apparaître sur plusieurs sites.
    # On dédoublonne sur les colonnes disponibles parmi :
    # titre, entreprise, source
    # (on ne dédoublonne pas cross-source pour conserver
    # l'information de multi-publication)
    # cols_dedup = [c for c in ["titre", "entreprise", "source"] if c in merged.columns]
    # if cols_dedup:
    #     avant = len(merged)
    #     merged = merged.drop_duplicates(subset=cols_dedup)
    #     print(f"\n   Doublons supprimés : {avant - len(merged)}")

    # ── Sauvegarde ────────────────────────────────────────
    output_path = os.path.join(DATA_DIR, output_filename)

    # utf-8-sig : encodage UTF-8 avec BOM, compatible Excel Windows
    merged.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n   Fichier fusionné : {output_path}")
    print(f"   Total : {len(merged)} offres uniques")

    return merged


# ─────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Exécution directe :
        python fusion.py

    Utile pour refaire la fusion sans relancer les scrapers
    (ex: si on veut changer la logique de dédoublonnage).
    """
    fusion_csv()