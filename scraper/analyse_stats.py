"""
analyse_stats.py — Analyse statistique de dataset_final.csv
=============================================================
À lancer APRÈS correctifs_nettoyage.py :

    python analyse_stats.py

Entrée  : data/dataset_final.csv
Sortie  : data/stats_resume.csv, top_villes.csv, top_competences.csv,
          top_secteurs.csv, top_contrats.csv, top_entreprises.csv,
          top_metiers.csv, evolution_mensuelle.csv
"""

import pandas as pd
import os

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"

def titre(texte):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  {texte}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")

def barre(valeur, max_val, largeur=25):
    n = int(valeur / max_val * largeur) if max_val > 0 else 0
    return "█" * n + "░" * (largeur - n)

# ─── Chargement ───────────────────────────────────────────────────────────────
for p in ["data/dataset_final.csv", "../data/dataset_final.csv"]:
    if os.path.exists(p):
        INPUT = p
        OUTPUT_DIR = os.path.dirname(p)
        break
else:
    raise FileNotFoundError("data/dataset_final.csv introuvable.")

df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
df = df.fillna("")

COMP_COLS = [c for c in df.columns if c.startswith("comp_")]
kpis = {}


# ══════════════════════════════════════════════════════════════════════════════
# 1. CHIFFRES GLOBAUX
# ══════════════════════════════════════════════════════════════════════════════
titre("1. CHIFFRES GLOBAUX")

total_offres   = len(df)
nb_entreprises = df["entreprise"].replace("", pd.NA).dropna().nunique()

# ✅ Lire ville_normalisee directement (déjà nettoyée par correctifs_nettoyage.py)
nb_villes = (
    df["ville_normalisee"]
    .replace({"": pd.NA, "Non précisé": pd.NA, "Sénégal (non précisé)": pd.NA})
    .dropna()
    .nunique()
) if "ville_normalisee" in df.columns else 0

nb_sources = df["source"].replace("", pd.NA).dropna().nunique() if "source" in df.columns else "N/A"

kpis.update({
    "total_offres"  : total_offres,
    "nb_entreprises": nb_entreprises,
    "nb_villes"     : nb_villes,
})

print(f"\n  {GREEN}Total offres scrappées   :{RESET} {BOLD}{total_offres:,}{RESET}")
print(f"  {GREEN}Entreprises uniques      :{RESET} {BOLD}{nb_entreprises:,}{RESET}")
print(f"  {GREEN}Villes représentées      :{RESET} {BOLD}{nb_villes:,}{RESET}")
print(f"  {GREEN}Sources de données       :{RESET} {BOLD}{nb_sources}{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. TOP 10 VILLES
# ══════════════════════════════════════════════════════════════════════════════
titre("2. TOP 10 VILLES")

top_villes = (
    df["ville_normalisee"]
    .replace({"": pd.NA, "Non précisé": pd.NA, "Sénégal (non précisé)": pd.NA})
    .dropna()
    .value_counts()
    .head(10)
    .reset_index()
)
top_villes.columns = ["ville", "nb_offres"]
top_villes["pct"] = (top_villes["nb_offres"] / total_offres * 100).round(1)

max_v = top_villes["nb_offres"].max() if len(top_villes) > 0 else 1
for _, row in top_villes.iterrows():
    print(f"  {row['ville']:<30} {row['nb_offres']:>5}  {barre(row['nb_offres'], max_v)}  {row['pct']}%")

if len(top_villes) > 0:
    kpis["ville_dominante"]     = top_villes.iloc[0]["ville"]
    kpis["pct_ville_dominante"] = top_villes.iloc[0]["pct"]

top_villes.to_csv(os.path.join(OUTPUT_DIR, "top_villes.csv"), index=False, encoding="utf-8-sig")
print(f"\n  {GREEN}✅ Exporté → data/top_villes.csv{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. RÉPARTITION DES CONTRATS
# ══════════════════════════════════════════════════════════════════════════════
titre("3. RÉPARTITION DES CONTRATS")

# ✅ Priorité à contrat_std (nettoyé), puis contrat_clean, puis contrat brut
col_contrat = next(
    (c for c in ["contrat_std", "contrat_clean", "contrat"] if c in df.columns), None
)

if col_contrat:
    contrats = (
        df[col_contrat]
        .replace("", "Non précisé")
        .value_counts()
        .reset_index()
    )
    contrats.columns = ["contrat", "nb_offres"]
    contrats["pct"] = (contrats["nb_offres"] / total_offres * 100).round(1)

    max_c = contrats["nb_offres"].max()
    for _, row in contrats.iterrows():
        print(f"  {row['contrat']:<25} {row['nb_offres']:>5}  {barre(row['nb_offres'], max_c)}  {row['pct']}%")

    kpis["contrat_dominant"] = contrats.iloc[0]["contrat"]
    contrats.to_csv(os.path.join(OUTPUT_DIR, "top_contrats.csv"), index=False, encoding="utf-8-sig")
    print(f"\n  {GREEN}✅ Exporté → data/top_contrats.csv{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. TOP 15 COMPÉTENCES (colonnes comp_* binaires)
# ══════════════════════════════════════════════════════════════════════════════
titre("4. TOP 15 COMPÉTENCES DEMANDÉES")

if COMP_COLS:
    comp_counts = {}
    for col in COMP_COLS:
        count = df[col].astype(str).str.strip().str.lower().isin(["true", "1", "yes"]).sum()
        if count > 0:
            label = col.replace("comp_", "").replace("_", " ")
            comp_counts[label] = int(count)

    top15 = sorted(comp_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    top_comp_df = pd.DataFrame(top15, columns=["competence", "nb_offres"])
    top_comp_df["pct"] = (top_comp_df["nb_offres"] / total_offres * 100).round(1)

    max_s = top15[0][1] if top15 else 1
    for skill, count in top15:
        pct = round(count / total_offres * 100, 1)
        print(f"  {skill:<30} {count:>5}  {barre(count, max_s)}  {pct}%")

    kpis["competence_top1"]           = top15[0][0] if top15 else "N/A"
    kpis["nb_competences_distinctes"] = len(comp_counts)

    top_comp_df.to_csv(os.path.join(OUTPUT_DIR, "top_competences.csv"), index=False, encoding="utf-8-sig")
    print(f"\n  {GREEN}✅ Exporté → data/top_competences.csv{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. TOP 10 SECTEURS
# ══════════════════════════════════════════════════════════════════════════════
titre("5. TOP 10 SECTEURS")

col_secteur = next(
    (c for c in ["secteur", "secteur_activite", "categorie"] if c in df.columns), None
)

if col_secteur:
    top_secteurs = (
        df[col_secteur]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_secteurs.columns = ["secteur", "nb_offres"]
    top_secteurs["pct"] = (top_secteurs["nb_offres"] / total_offres * 100).round(1)

    max_sec = top_secteurs["nb_offres"].max()
    for _, row in top_secteurs.iterrows():
        print(f"  {row['secteur']:<35} {row['nb_offres']:>5}  {barre(row['nb_offres'], max_sec)}  {row['pct']}%")

    kpis["secteur_dominant"] = top_secteurs.iloc[0]["secteur"]
    top_secteurs.to_csv(os.path.join(OUTPUT_DIR, "top_secteurs.csv"), index=False, encoding="utf-8-sig")
    print(f"\n  {GREEN}✅ Exporté → data/top_secteurs.csv{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. TOP 10 ENTREPRISES
# ══════════════════════════════════════════════════════════════════════════════
titre("6. TOP 10 ENTREPRISES QUI RECRUTENT")

top_entreprises = (
    df["entreprise"]
    .replace("", pd.NA)
    .dropna()
    .value_counts()
    .head(10)
    .reset_index()
)
top_entreprises.columns = ["entreprise", "nb_offres"]
top_entreprises["pct"] = (top_entreprises["nb_offres"] / total_offres * 100).round(1)

max_e = top_entreprises["nb_offres"].max()
for _, row in top_entreprises.iterrows():
    print(f"  {row['entreprise']:<40} {row['nb_offres']:>5}  {barre(row['nb_offres'], max_e)}")

kpis["entreprise_top1"] = top_entreprises.iloc[0]["entreprise"] if len(top_entreprises) > 0 else "N/A"
top_entreprises.to_csv(os.path.join(OUTPUT_DIR, "top_entreprises.csv"), index=False, encoding="utf-8-sig")
print(f"\n  {GREEN}✅ Exporté → data/top_entreprises.csv{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. ÉVOLUTION MENSUELLE
# ✅ Lire date_publication_clean directement (recalculée par correctifs_nettoyage.py)
# ══════════════════════════════════════════════════════════════════════════════
titre("7. ÉVOLUTION MENSUELLE DES OFFRES")

col_date_pub = "date_publication_clean"

if col_date_pub in df.columns:
    dates_series = df[col_date_pub].replace("", pd.NA).dropna()
    dates_parsed = pd.to_datetime(dates_series, format="%Y-%m-%d", errors="coerce")
    n_valid = dates_parsed.notna().sum()
    print(f"  Colonne utilisée : {col_date_pub} ({n_valid:,} dates valides)")

    if n_valid > 0:
        df["_mois"] = dates_parsed.dt.to_period("M")
        evolution = (
            df.dropna(subset=["_mois"])
            .groupby("_mois")
            .size()
            .reset_index(name="nb_offres")
        )
        evolution["mois_str"] = evolution["_mois"].astype(str)
        evolution = evolution.sort_values("mois_str")
        evolution["croissance_pct"] = evolution["nb_offres"].pct_change().mul(100).round(1)

        evolution_df = evolution[["mois_str", "nb_offres", "croissance_pct"]].copy()
        evolution_df.columns = ["mois", "nb_offres", "croissance_pct"]

        max_m = evolution["nb_offres"].max()
        for _, row in evolution.iterrows():
            tendance = ""
            if pd.notna(row["croissance_pct"]):
                signe = "+" if row["croissance_pct"] >= 0 else ""
                tendance = f"  {signe}{row['croissance_pct']}%"
            print(f"  {str(row['mois_str']):<12} {row['nb_offres']:>5}  {barre(row['nb_offres'], max_m)}{YELLOW}{tendance}{RESET}")

        if len(evolution) >= 2:
            debut = evolution.iloc[0]["nb_offres"]
            fin   = evolution.iloc[-1]["nb_offres"]
            croissance = round((fin - debut) / debut * 100, 1) if debut > 0 else 0
            kpis["croissance_globale_pct"] = croissance
            signe = "+" if croissance >= 0 else ""
            print(f"\n  {GREEN}Croissance globale : {signe}{croissance}%{RESET}")

        evolution_df.to_csv(os.path.join(OUTPUT_DIR, "evolution_mensuelle.csv"), index=False, encoding="utf-8-sig")
        print(f"  {GREEN}✅ Exporté → data/evolution_mensuelle.csv{RESET}")
    else:
        print("  ⚠️  Aucune date valide dans date_publication_clean")
else:
    print("  ⚠️  Colonne date_publication_clean introuvable — relance correctifs_nettoyage.py")


# ══════════════════════════════════════════════════════════════════════════════
# 8. SALAIRES
# ══════════════════════════════════════════════════════════════════════════════
titre("8. ANALYSE DES SALAIRES")

salaires = None
for col in ["salaire_num", "salaire"]:
    if col in df.columns:
        s = pd.to_numeric(df[col].replace("", pd.NA), errors="coerce").dropna()
        s = s[(s >= 50_000) & (s <= 20_000_000)]
        if len(s) >= 5:
            salaires = s
            break

if salaires is not None:
    print(f"  Offres avec salaire   : {len(salaires):,} ({len(salaires)/total_offres*100:.1f}%)")
    print(f"  Salaire moyen         : {salaires.mean():>12,.0f} FCFA")
    print(f"  Salaire médian        : {salaires.median():>12,.0f} FCFA")
    print(f"  Salaire minimum       : {salaires.min():>12,.0f} FCFA")
    print(f"  Salaire maximum       : {salaires.max():>12,.0f} FCFA")
    kpis["salaire_moyen"]  = round(salaires.mean())
    kpis["salaire_median"] = round(salaires.median())
else:
    print("  ⚠️  Trop peu de salaires renseignés — non analysé")
    print("  (Normal : la plupart des offres au Sénégal ne publient pas les salaires)")


# ══════════════════════════════════════════════════════════════════════════════
# 9. TOP 10 MÉTIERS (Stagiaire déjà retiré par correctifs_nettoyage.py)
# ══════════════════════════════════════════════════════════════════════════════
titre("9. TOP 10 MÉTIERS NORMALISÉS")

col_metier = next(
    (c for c in ["metier_normalise", "titre"] if c in df.columns), None
)

if col_metier:
    top_metiers = (
        df[col_metier]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_metiers.columns = ["metier", "nb_offres"]
    top_metiers["pct"] = (top_metiers["nb_offres"] / total_offres * 100).round(1)

    max_met = top_metiers["nb_offres"].max()
    for _, row in top_metiers.iterrows():
        print(f"  {row['metier']:<40} {row['nb_offres']:>5}  {barre(row['nb_offres'], max_met)}  {row['pct']}%")

    top_metiers.to_csv(os.path.join(OUTPUT_DIR, "top_metiers.csv"), index=False, encoding="utf-8-sig")
    print(f"\n  {GREEN}✅ Exporté → data/top_metiers.csv{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 10. EXPORT KPIs RÉSUMÉ
# ══════════════════════════════════════════════════════════════════════════════
titre("10. EXPORT RÉSUMÉ KPIs")

kpis_df = pd.DataFrame([{"indicateur": k, "valeur": str(v)} for k, v in kpis.items()])
kpis_df.to_csv(os.path.join(OUTPUT_DIR, "stats_resume.csv"), index=False, encoding="utf-8-sig")

for f in ["stats_resume.csv","top_villes.csv","top_competences.csv","top_secteurs.csv",
          "top_contrats.csv","top_entreprises.csv","top_metiers.csv","evolution_mensuelle.csv"]:
    if os.path.exists(os.path.join(OUTPUT_DIR, f)):
        print(f"  {GREEN}✅ data/{f}{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# RÉCAPITULATIF FINAL
# ══════════════════════════════════════════════════════════════════════════════
titre("RÉCAPITULATIF — KPIs CLÉS")

recap = [
    ("Total offres",        kpis.get("total_offres", "N/A")),
    ("Entreprises uniques", kpis.get("nb_entreprises", "N/A")),
    ("Villes représentées", kpis.get("nb_villes", "N/A")),
    ("Ville dominante",     kpis.get("ville_dominante", "N/A")),
    ("Secteur dominant",    kpis.get("secteur_dominant", "N/A")),
    ("Compétence #1",       kpis.get("competence_top1", "N/A")),
    ("Entreprise #1",       kpis.get("entreprise_top1", "N/A")),
    ("Contrat dominant",    kpis.get("contrat_dominant", "N/A")),
    ("Croissance globale",  str(kpis.get("croissance_globale_pct", "N/A")) + "%"),
    ("Salaire moyen",       f"{kpis['salaire_moyen']:,} FCFA" if "salaire_moyen" in kpis else "Non disponible"),
]

for label, valeur in recap:
    print(f"  {label:<25} {BOLD}{valeur}{RESET}")

print(f"\n{BOLD}{GREEN}  ✅ Analyse terminée — prêt pour Power BI et Streamlit !{RESET}\n")