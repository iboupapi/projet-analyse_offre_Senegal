"""
correctifs_nettoyage.py — Patch corrigé (v3)
============================================================
    python correctifs_nettoyage.py

Corrections :
  1. Villes     — lit la colonne 'ville' (1164 valeurs) en priorité
  2. Entreprises — fusions (Topwork/Top Work, etc.)
  3. Dates      — utilise date_publication, ignore date_limite
  4. Métiers    — retire Stagiaire, Bénévole, Volontaire

Entrée : data/dataset_final.csv
Sortie : data/dataset_final.csv (backup → dataset_final_backup3.csv)
"""

import pandas as pd
import re
import os
import shutil
import unicodedata
from datetime import datetime

RESET = "\033[0m"
BOLD  = "\033[1m"
GREEN = "\033[92m"
BLUE  = "\033[94m"

def titre(texte):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  {texte}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")

def strip_accents(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(s))
        if unicodedata.category(c) != 'Mn'
    )

def slug(s):
    return re.sub(r'\W+', '', strip_accents(s).lower())


# ─── Chargement ───────────────────────────────────────────────────────────────
for p in ["data/dataset_final.csv", "../data/dataset_final.csv"]:
    if os.path.exists(p):
        INPUT = p
        OUTPUT_DIR = os.path.dirname(p)
        BACKUP = p.replace("dataset_final.csv", "dataset_final_backup3.csv")
        break
else:
    raise FileNotFoundError("data/dataset_final.csv introuvable.")

shutil.copy(INPUT, BACKUP)
df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
df = df.fillna("")
print(f"\n  Lignes chargées : {len(df):,}")
print(f"  Backup → {BACKUP}")

# Diagnostic rapide des colonnes ville
print(f"\n  Diagnostic colonnes ville :")
for col in ["lieu", "ville", "ville_clean", "localisation", "ville_normalisee"]:
    if col in df.columns:
        n = (df[col].replace("", pd.NA)
                    .replace("Non précisé", pd.NA)
                    .dropna().shape[0])
        print(f"    {col:<20} → {n:>5} valeurs non-vides")


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTION 1 — VILLES
# ✅ Priorité : ville (1164 valeurs) > lieu (3) > localisation (1)
# ══════════════════════════════════════════════════════════════════════════════
titre("CORRECTION 1 — VILLES")

VILLES_MAP = [
    # Dakar et tous ses quartiers / communes d'arrondissement
    (r"dakar|pikine|gu[eé]diawaye|rufisque|parcelles|almadies|"
     r"ouakam|plateau|mermoz|sacr[eé].c[oœ]ur|yoff|ngor|grand.yoff|"
     r"hlm|libert[eé]|fann|gueule.tap[eé]e|medina|biscuiterie|thiaroye|"
     r"mbao|malika|keur.massar|yeumbeul|sangalkam|s[eé]bikhotane|"
     r"bargny|diamniadio|lac.rose|dkr",                             "Dakar"),
    # Thiès et sa région
    (r"thi[eè]s|thies|sindia",                                      "Thiès"),
    # Mbour (région Thiès mais ville distincte)
    (r"mbour|saly|joal|popenguine|somone|ngaparou",                 "Mbour"),
    # Saint-Louis
    (r"saint.louis|st.louis",                                       "Saint-Louis"),
    # Ziguinchor
    (r"ziguinchor",                                                  "Ziguinchor"),
    # Kaolack
    (r"kaolack",                                                     "Kaolack"),
    # Touba
    (r"\btouba\b",                                                   "Touba"),
    # Kolda
    (r"\bkolda\b",                                                   "Kolda"),
    # Louga
    (r"\blouga\b",                                                   "Louga"),
    # Diourbel
    (r"\bdiourbel\b",                                                "Diourbel"),
    # Tambacounda
    (r"tambacounda|tamba\b",                                         "Tambacounda"),
    # Matam
    (r"\bmatam\b",                                                   "Matam"),
    # Fatick
    (r"\bfatick\b",                                                  "Fatick"),
    # Kédougou
    (r"k[eé]dougou",                                                 "Kédougou"),
    # Sédhiou
    (r"s[eé]dhiou",                                                  "Sédhiou"),
    # Remote
    (r"remote|t[eé]l[eé]travail|[aà] distance",                     "Remote / Télétravail"),
    # Sénégal générique (sans ville)
    (r"^s[eé]n[eé]gal$|^sn$",                                       "Non précisé"),
]

def normaliser_ville_v3(val):
    if not val or str(val).strip().lower() in ("", "nan", "n/a", "none", "non précisé"):
        return "Non précisé"
    # Nettoyer les \n et espaces multiples (ex: "Dakar,\n                Dakar")
    v = re.sub(r'\s+', ' ', str(val).strip())
    # Si doublon séparé par virgule+newline comme "Dakar,\n Dakar" → prendre premier
    if re.search(r',\s*\n', str(val)):
        v = str(val).split(',')[0].strip()
    v_low = strip_accents(v.lower())
    for pattern, label in VILLES_MAP:
        if re.search(pattern, v_low):
            return label
    # Format "Ville, Sénégal" → extraire la ville avant la virgule
    m = re.match(r'^(.+?),\s*s[eé]n[eé]gal\s*$', v_low)
    if m:
        ville_brute = m.group(1).strip()
        for pattern, label in VILLES_MAP:
            if re.search(pattern, ville_brute):
                return label
        return ville_brute.title()
    # Format "Quartier, Ville" (ex: "Ouakam, Dakar") → retester sur la valeur complète
    return v.strip()[:40]

def get_source_ville(row):
    # ✅ ORDRE CORRIGÉ : ville en priorité (1164 valeurs), puis lieu, puis localisation
    for col in ["ville", "lieu", "localisation"]:
        v = str(row.get(col, "")).strip()
        # Nettoyer \n avant de vérifier si vide
        v = re.sub(r'\s+', ' ', v)
        if v and v.lower() not in ("", "nan", "n/a", "none"):
            return v
    return ""

avant_nb = df["ville_normalisee"].replace({"": pd.NA, "Non précisé": pd.NA}).dropna().nunique()
df["ville_normalisee"] = df.apply(lambda row: normaliser_ville_v3(get_source_ville(row)), axis=1)
apres_nb = df["ville_normalisee"].replace({"Non précisé": pd.NA}).dropna().nunique()

print(f"\n  Villes distinctes avant : {avant_nb}")
print(f"  Villes distinctes après : {apres_nb}")
print(f"\n  Top 10 villes après correction :")
for v, n in df["ville_normalisee"].replace("Non précisé", pd.NA).dropna().value_counts().head(10).items():
    print(f"    {v:<30} {n:>5}")


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTION 2 — ENTREPRISES
# ══════════════════════════════════════════════════════════════════════════════
titre("CORRECTION 2 — ENTREPRISES")

ENTREPRISES_MAP = {
    "topwork":                     "Topwork",
    "topworks":                    "Topwork",
    "top work":                    "Topwork",
    "rmosenegal":                  "RMO Sénégal",
    "rmosénégal":                  "RMO Sénégal",
    "servtecsenegal":              "SERVTEC Sénégal",
    "servtecsénégal":              "SERVTEC Sénégal",
    "eliterh":                     "Elite RH",
    "internationalstaffingcompany":"International Staffing Company",
    "phoenixconsultinggroupsn":    "Phoenix Consulting Group SN",
    "phoenixconsultinggroup":      "Phoenix Consulting Group SN",
    "msf":                         "MSF (Médecins Sans Frontières)",
    "medecinssansfrontieres":      "MSF (Médecins Sans Frontières)",
}

def normaliser_entreprise(val):
    if not val or str(val).strip().lower() in ("", "nan", "n/a"):
        return ""
    v = str(val).strip()
    v_slug = slug(v)
    if v_slug in ENTREPRISES_MAP:
        return ENTREPRISES_MAP[v_slug]
    if v.isupper() and len(v) <= 6:
        return v
    return v

avant_e = df["entreprise"].replace("", pd.NA).dropna().nunique()
df["entreprise"] = df["entreprise"].apply(normaliser_entreprise)
apres_e = df["entreprise"].replace("", pd.NA).dropna().nunique()

print(f"\n  Entreprises avant : {avant_e:,}  →  après : {apres_e:,}  (fusionnées : {avant_e - apres_e:,})")
print(f"\n  Top 10 entreprises :")
for e, n in df["entreprise"].replace("", pd.NA).dropna().value_counts().head(10).items():
    print(f"    {e:<40} {n:>5}")


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTION 3 — DATES
# ══════════════════════════════════════════════════════════════════════════════
titre("CORRECTION 3 — DATES")

AUJOURD_HUI = pd.Timestamp(datetime.today().date())

def parse_date_pub(row):
    for col in ["date_publication", "date"]:
        v = str(row.get(col, "")).strip()
        if not v or v.lower() in ("", "nan", "n/a", "none"):
            continue
        try:
            d = pd.to_datetime(v, format="%Y-%m-%d", errors="raise")
            if d <= AUJOURD_HUI:
                return d.strftime("%Y-%m-%d")
        except:
            pass
        try:
            d = pd.to_datetime(v, dayfirst=True, errors="raise")
            if d <= AUJOURD_HUI:
                return d.strftime("%Y-%m-%d")
        except:
            pass
    return ""

print("\n  Recalcul des dates (on ignore date_limite = expiration)...")
df["date_publication_clean"] = df.apply(parse_date_pub, axis=1)

dates_valides = (df["date_publication_clean"].str.strip() != "").sum()
print(f"  Dates valides : {dates_valides:,}")

if dates_valides > 0:
    dates_parsed = pd.to_datetime(df["date_publication_clean"], errors="coerce")
    evolution = dates_parsed.dt.to_period("M").value_counts().sort_index()
    print(f"\n  Distribution mensuelle :")
    for mois, nb in evolution.items():
        print(f"    {mois}  →  {nb:>5} offres")


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTION 4 — MÉTIERS
# ══════════════════════════════════════════════════════════════════════════════
titre("CORRECTION 4 — MÉTIERS")

PAS_DES_METIERS = {
    "stagiaire", "benevole", "benevolat",
    "volontaire", "apprenti", "alternant", "alternante"
}

def nettoyer_metier(val):
    if not val or str(val).strip().lower() in ("", "nan", "n/a"):
        return ""
    v = str(val).strip()
    if slug(v) in PAS_DES_METIERS:
        return ""
    return v

if "metier_normalise" in df.columns:
    avant_m = (df["metier_normalise"].str.strip() != "").sum()
    df["metier_normalise"] = df["metier_normalise"].apply(nettoyer_metier)
    apres_m = (df["metier_normalise"].str.strip() != "").sum()
    print(f"\n  Métiers retirés : {avant_m - apres_m:,} (Stagiaire, Bénévole, etc.)")
    print(f"\n  Top 10 métiers :")
    for m, n in df["metier_normalise"].replace("", pd.NA).dropna().value_counts().head(10).items():
        print(f"    {m:<40} {n:>5}")


# ══════════════════════════════════════════════════════════════════════════════
# SAUVEGARDE
# ══════════════════════════════════════════════════════════════════════════════
titre("SAUVEGARDE")

df.to_csv(INPUT, index=False, encoding="utf-8-sig")
print(f"\n  {GREEN}✅ dataset_final.csv mis à jour ({len(df):,} lignes){RESET}")
print(f"  {GREEN}✅ Backup → {BACKUP}{RESET}")
print(f"\n  Prochaine étape : python analyse_stats.py\n")

CSV