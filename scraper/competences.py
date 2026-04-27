"""
competences.py — Extraction des compétences pour analyse PowerBI / Excel
=========================================================================
Lit merged_with_desc.csv et produit deux fichiers :

  dataset_final.csv        → une ligne par offre avec colonnes booléennes
                             (competence_python, competence_excel, etc.)
                             + colonnes nettoyées pour PowerBI

  competences_long.csv     → format "long" : une ligne par (offre, compétence)
                             idéal pour les graphiques PowerBI (barres, treemap)

Usage :
    python competences.py
"""

import pandas as pd
import re
import os

INPUT_FILE       = "../data/merged_with_desc.csv"
OUTPUT_WIDE      = "../data/dataset_final.csv"          # format large  (PowerBI)
OUTPUT_LONG      = "../data/competences_long.csv"       # format long   (graphiques)

# ─── Dictionnaire de compétences ─────────────────────────────────────────────
# Clé   = nom de la colonne dans le CSV final
# Valeur = liste de mots-clés à chercher (regex, insensible à la casse)

COMPETENCES = {

    # ── Programmation ────────────────────────────────────────────────────────
    "Python":       [r"\bpython\b"],
    "Java":         [r"\bjava\b(?!script)"],
    "JavaScript":   [r"\bjavascript\b", r"\bjs\b", r"\bnode\.?js\b"],
    "PHP":          [r"\bphp\b"],
    "R_stats":      [r"\b(langage\s)?R\b", r"\bR\s+studio\b", r"\brstudio\b"],
    "VBA":          [r"\bvba\b"],
    "C_Cpp":        [r"\b(c\+\+|langage c)\b"],
    "Dart_Flutter": [r"\bdart\b", r"\bflutter\b"],

    # ── Web & Mobile ─────────────────────────────────────────────────────────
    "React":        [r"\breact\b"],
    "Angular":      [r"\bangular\b"],
    "Django":       [r"\bdjango\b"],
    "Laravel":      [r"\blaravel\b"],
    "WordPress":    [r"\bwordpress\b"],
    "HTML_CSS":     [r"\bhtml\b", r"\bcss\b"],

    # ── Bases de données ─────────────────────────────────────────────────────
    "SQL":          [r"\bsql\b"],
    "MySQL":        [r"\bmysql\b"],
    "PostgreSQL":   [r"\bpostgresql\b", r"\bpostgres\b"],
    "MongoDB":      [r"\bmongodb\b"],
    "Oracle_DB":    [r"\boracle\b"],

    # ── Data & BI ────────────────────────────────────────────────────────────
    "Power_BI":     [r"\bpower\s?bi\b"],
    "Tableau":      [r"\btableau\b"],
    "Excel_avance": [r"\bexcel\b"],
    "SPSS":         [r"\bspss\b"],
    "Machine_Learning": [r"\bmachine\s?learning\b", r"\bml\b", r"\bdeep\s?learning\b"],
    "Data_Science": [r"\bdata\s?science\b", r"\bdatascience\b"],
    "Pandas_NumPy": [r"\bpandas\b", r"\bnumpy\b"],

    # ── Bureautique ───────────────────────────────────────────────────────────
    "Suite_Office": [r"\b(suite\s)?office\b", r"\bmicrosoft\s?office\b"],
    "Word":         [r"\bword\b"],
    "PowerPoint":   [r"\bpowerpoint\b"],
    "Google_Sheets":[r"\bgoogle\s?sheets\b"],

    # ── ERP / CRM ────────────────────────────────────────────────────────────
    "SAP":          [r"\bsap\b"],
    "Odoo":         [r"\bodoo\b"],
    "Salesforce":   [r"\bsalesforce\b"],
    "Sage":         [r"\bsage\b"],

    # ── DevOps / Cloud ────────────────────────────────────────────────────────
    "Git":          [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "Docker":       [r"\bdocker\b"],
    "AWS":          [r"\baws\b", r"\bamazon\s?web\s?services\b"],
    "Linux":        [r"\blinux\b", r"\bunix\b"],

    # ── Finance & Comptabilité ────────────────────────────────────────────────
    "OHADA":        [r"\bohada\b"],
    "IFRS":         [r"\bifrs\b", r"\bnormes\s?ifrs\b"],
    "Audit":        [r"\baudit\b"],
    "Comptabilite": [r"\bcomptabilit[eé]\b"],
    "Finance":      [r"\bfinance\b", r"\bfinanci[eè]r\b"],
    "SYSCOHADA":    [r"\bsyscohada\b"],

    # ── Langues ───────────────────────────────────────────────────────────────
    "Anglais":      [r"\banglais\b", r"\benglish\b", r"\bbilingue\b"],
    "Français":     [r"\bfrançais\b", r"\bfrancais\b"],
    "Wolof":        [r"\bwolof\b"],
    "Arabe":        [r"\barabe\b"],
    "Espagnol":     [r"\bespagnol\b"],

    # ── Gestion de projet ─────────────────────────────────────────────────────
    "Gestion_projet": [r"\bgestion\s+de\s+projet\b", r"\bproject\s+management\b",
                       r"\bpmp\b", r"\bscrum\b", r"\bagile\b"],
    "MS_Project":   [r"\bms\s?project\b", r"\bmicrosoft\s?project\b"],
    "Jira":         [r"\bjira\b"],

    # ── Marketing & Communication ─────────────────────────────────────────────
    "Marketing_digital": [r"\bmarketing\s?digital\b", r"\bseo\b", r"\bsem\b",
                          r"\bgoogle\s?ads\b", r"\bfacebook\s?ads\b"],
    "Community_management": [r"\bcommunity\s?manag\b", r"\bréseaux\s+sociaux\b"],
    "Photoshop":    [r"\bphotoshop\b", r"\billustrator\b", r"\bindesign\b"],

    # ── Compétences transversales ─────────────────────────────────────────────
    "Permis_conduire": [r"\bpermis\s+(de\s+)?condui\b", r"\bpermis\s+[bBcC]\b"],
    "Travail_equipe":  [r"\btravail\s+en\s+[eé]quipe\b", r"\besprit\s+d.[eé]quipe\b"],
    "Leadership":      [r"\bleadership\b", r"\bmanagement\s+d.[eé]quipe\b"],
    "Communication":   [r"\bcommunication\b"],
    "Negociation":     [r"\bn[eé]gociation\b"],
}


# ─── Fonctions utilitaires ────────────────────────────────────────────────────

def nettoyer_texte(texte) -> str:
    """Retourne une chaîne propre, même si la valeur est NaN."""
    if pd.isna(texte) or texte in ("N/A", "ERREUR_RESEAU"):
        return ""
    return str(texte).lower()


def detecter_competences(texte: str) -> dict:
    """
    Retourne un dict {nom_competence: True/False} pour un texte donné.
    On cherche dans le titre + description courte + description complète.
    """
    resultats = {}
    for comp, patterns in COMPETENCES.items():
        trouve = any(re.search(p, texte, re.IGNORECASE) for p in patterns)
        resultats[f"comp_{comp}"] = trouve
    return resultats


def nb_competences(row) -> int:
    """Compte le nombre de compétences détectées dans une ligne."""
    return sum(1 for col in row.index if col.startswith("comp_") and row[col])


# ─── Pipeline principal ───────────────────────────────────────────────────────

def extraire_competences():
    print("\n" + "=" * 60)
    print("  🧠 EXTRACTION DES COMPÉTENCES")
    print("=" * 60)

    # ── Chargement ────────────────────────────────────────────────────────────
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Fichier introuvable : {INPUT_FILE}")
        print("   → Lance d'abord : python detail_scraper.py")
        return

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig", low_memory=False)
    print(f"  📂 {len(df)} offres chargées")

    # ── Nettoyage des colonnes pour PowerBI ───────────────────────────────────
    # Harmoniser les valeurs manquantes
    for col in df.columns:
        df[col] = df[col].fillna("N/A")

    # Colonne texte combiné : titre + description courte + description complète
    df["_texte_combine"] = (
        df.get("titre",                "").apply(nettoyer_texte) + " " +
        df.get("description",          "").apply(nettoyer_texte) + " " +
        df.get("description_complete", "").apply(nettoyer_texte)
    )

    # ── Détection des compétences ─────────────────────────────────────────────
    print(f"  🔍 Détection de {len(COMPETENCES)} compétences...")
    comp_df = df["_texte_combine"].apply(
        lambda t: pd.Series(detecter_competences(t))
    )
    df = pd.concat([df, comp_df], axis=1)

    # Colonne synthèse : nombre de compétences détectées
    df["nb_competences"] = df.apply(nb_competences, axis=1)

    # ── Nettoyage colonnes inutiles pour PowerBI ──────────────────────────────
    df = df.drop(columns=["_texte_combine"], errors="ignore")

    # ── Colonnes utiles PowerBI — nettoyage des valeurs ──────────────────────
    # Source : harmoniser les noms
    if "source" in df.columns:
        df["source"] = df["source"].str.strip().str.lower()

    # Contrat : harmoniser cdd/cdi/stage
    if "contrat" in df.columns:
        df["contrat_clean"] = df["contrat"].str.lower().str.strip()
        df["contrat_clean"] = df["contrat_clean"].apply(lambda x:
            "CDI"   if "cdi" in str(x) else
            "CDD"   if "cdd" in str(x) else
            "Stage" if "stage" in str(x) or "stagiaire" in str(x) else
            "Freelance" if "free" in str(x) or "consul" in str(x) else
            "Autre"
        )

    # Lieu : extraire la ville principale
    if "lieu" in df.columns:
        def extraire_ville(lieu):
            lieu = str(lieu).lower()
            if "dakar"    in lieu: return "Dakar"
            if "thiès"    in lieu or "thies" in lieu: return "Thiès"
            if "saint"    in lieu: return "Saint-Louis"
            if "ziguinchor" in lieu: return "Ziguinchor"
            if "kaolack"  in lieu: return "Kaolack"
            if "kolda"    in lieu: return "Kolda"
            if "touba"    in lieu: return "Touba"
            if "international" in lieu or "remote" in lieu: return "Remote/International"
            if lieu in ("n/a", "", "nan"): return "Non précisé"
            return "Autre"
        df["ville_clean"] = df["lieu"].apply(extraire_ville)

    # ── Sauvegarde format LARGE (une ligne par offre) ─────────────────────────
    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_WIDE, index=False, encoding="utf-8-sig")
    print(f"\n  ✅ Format large  → {OUTPUT_WIDE}  ({len(df)} lignes)")

    # ── Sauvegarde format LONG (une ligne par offre × compétence) ─────────────
    # Idéal pour graphiques PowerBI : barres, treemaps, nuages de mots
    comp_cols = [c for c in df.columns if c.startswith("comp_")]
    id_cols   = ["titre", "source", "lieu", "contrat", "date_limite",
                 "lien", "ville_clean" if "ville_clean" in df.columns else "lieu",
                 "contrat_clean" if "contrat_clean" in df.columns else "contrat",
                 "nb_competences"]
    id_cols   = [c for c in id_cols if c in df.columns]

    df_long = df[id_cols + comp_cols].melt(
        id_vars    = id_cols,
        value_vars = comp_cols,
        var_name   = "competence",
        value_name = "present"
    )
    # Garder seulement les compétences présentes + nettoyer le nom
    df_long = df_long[df_long["present"] == True].copy()
    df_long["competence"] = df_long["competence"].str.replace("comp_", "").str.replace("_", " ")
    df_long = df_long.drop(columns=["present"])

    df_long.to_csv(OUTPUT_LONG, index=False, encoding="utf-8-sig")
    print(f"  ✅ Format long   → {OUTPUT_LONG}  ({len(df_long)} lignes)")

    # ── Statistiques rapides ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  📊 TOP 15 COMPÉTENCES DÉTECTÉES")
    print(f"{'='*60}")
    top = comp_df.sum().sort_values(ascending=False).head(15)
    top.index = top.index.str.replace("comp_", "").str.replace("_", " ")
    for comp, count in top.items():
        pct = count / len(df) * 100
        bar = "█" * int(pct / 2)
        print(f"  {comp:<20} {count:>5} offres  {pct:>5.1f}%  {bar}")

    print(f"\n  Offres avec ≥1 compétence : {(df['nb_competences'] > 0).sum()}")
    print(f"  Offres sans compétence    : {(df['nb_competences'] == 0).sum()}")
    print(f"{'='*60}\n")


# ─── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    extraire_competences()