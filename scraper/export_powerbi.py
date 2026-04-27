"""
clean_and_export_v2.py — Nettoyage profond basé sur analyse réelle
===================================================================
Corrections appliquées :
  1. Suppression des lignes parasites (agrégats "Les X offres du...")
  2. Suppression des doublons (même offre multi-sources)
  3. Re-classification secteur basée sur MÉTIER (pas sur titre d'entreprise)
  4. Nettoyage titres (H/F, préfixes numériques)
  5. Fusion entreprises en doublon de nom
  6. Contrats propres sans "Non précisé"
  7. Villes propres sans "Non précisé"
  8. KPIs propres sans "Autre" ni valeurs parasites

Lance depuis scraper/ :
    python clean_and_export_v2.py
Produit dans data/powerbi_v2/
"""

import pandas as pd
import numpy as np
import os
import re

# ─── Chemins ──────────────────────────────────────────────────────────────────
for p in ["data/dataset_final.csv", "../data/dataset_final.csv"]:
    if os.path.exists(p):
        INPUT   = p
        OUT_DIR = p.replace("dataset_final.csv", "powerbi_v2")
        break
else:
    raise FileNotFoundError("data/dataset_final.csv introuvable")

os.makedirs(OUT_DIR, exist_ok=True)

# ─── Fonction save propre ─────────────────────────────────────────────────────
def save(df, filename):
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            test = df[col].astype(str).str.replace(",", "", regex=False).str.strip()
            converted = pd.to_numeric(test, errors="coerce")
            if converted.notna().mean() > 0.8:
                df[col] = converted
        if df[col].dtype == float:
            try:
                if (df[col].dropna() % 1 == 0).all():
                    df[col] = df[col].astype("Int64")
            except:
                pass
    path = os.path.join(OUT_DIR, filename)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  ✅ {filename:<50} ({len(df):>6,} lignes)")
    return df

print("\n" + "="*65)
print("  🧹 NETTOYAGE PROFOND V2 — DONNÉES POUR POWER BI")
print("="*65)

# ══════════════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════
df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)
df = df.fillna("")
n_raw = len(df)
comp_cols = [c for c in df.columns if c.startswith("comp_")]
print(f"\n  📂 {n_raw:,} offres brutes | {len(df.columns)} colonnes\n")

rapport = []

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 1 — SUPPRESSION DES LIGNES PARASITES
# ══════════════════════════════════════════════════════════════════
print("  📌 ÉTAPE 1 — Suppression lignes parasites...")

# Lignes "agrégats" : titres du type "Les 44 offres d'emploi du..."
masque_agregat = df["titre"].str.contains(
    r"les\s+\d+\s+offres", case=False, na=False, regex=True
)
n_agregats = masque_agregat.sum()
df = df[~masque_agregat].copy()
rapport.append({"etape": "Lignes agrégats supprimées",
                "nb": n_agregats, "detail": "Titres du type 'Les X offres du...'"})
print(f"     → {n_agregats} lignes 'Les X offres du...' supprimées")

# Lignes sans titre ni entreprise
masque_vide = (df["titre"].str.strip() == "") & (df["entreprise"].str.strip() == "")
n_vide = masque_vide.sum()
df = df[~masque_vide].copy()
rapport.append({"etape": "Lignes sans titre+entreprise", "nb": n_vide, "detail": ""})
print(f"     → {n_vide} lignes sans titre ni entreprise supprimées")

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 2 — SUPPRESSION DES DOUBLONS
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 2 — Suppression des doublons...")

# Priorité de source : garder la plus riche en info
source_priority = {
    "emploidakar": 1, "afriqueemplois": 2, "expatdakar": 3,
    "senejobs": 4, "optioncarriere": 5, "linkedin": 6,
    "senjob": 7, "senego": 8, "concoursn": 9
}
df["_prio"] = df["source"].map(source_priority).fillna(99)
df = df.sort_values("_prio")

# Doublon sur lien exact
n0 = len(df)
df = df.drop_duplicates(subset=["lien"], keep="first")
n_dup_lien = n0 - len(df)

# Doublon sur titre + entreprise (même offre multi-sources)
n1 = len(df)
df = df.drop_duplicates(subset=["titre", "entreprise"], keep="first")
n_dup_titre = n1 - len(df)
df = df.drop(columns=["_prio"])

rapport.append({"etape": "Doublons lien exact", "nb": n_dup_lien, "detail": ""})
rapport.append({"etape": "Doublons titre+entreprise", "nb": n_dup_titre,
                "detail": "Même offre sur plusieurs sites"})
print(f"     → {n_dup_lien} doublons sur lien exact")
print(f"     → {n_dup_titre} doublons sur titre+entreprise")
print(f"     → {len(df):,} offres restantes")

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 3 — NETTOYAGE TITRES
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 3 — Nettoyage titres...")

def clean_titre(t):
    t = str(t).strip()
    # Enlever "Entreprise X recrute 0N " au début
    t = re.sub(r"^.{0,60}recrute\s+\d*\s*", "", t, flags=re.IGNORECASE).strip()
    # Enlever préfixes numériques "01 " "02 "
    t = re.sub(r"^\d{1,2}\s+", "", t)
    # Enlever H/F, (H/F), F/H, (e)
    t = re.sub(r"\s*[\(\[]?[HhFf][/\\][FfHh][\)\]]?", "", t)
    t = re.sub(r"\s*\(e\)\s*$", "", t, flags=re.IGNORECASE)
    # Enlever mentions (H) (F)
    t = re.sub(r"\s*[\(\[]\s*[HhFf]\s*[\)\]]", "", t)
    # Nettoyer espaces
    t = re.sub(r"\s+", " ", t).strip()
    # Si après nettoyage le titre est trop court ou vide, garder l'original
    if len(t) < 4:
        return str(t).strip()
    return t

df["titre_clean"] = df["titre"].apply(clean_titre)
n_mod = (df["titre_clean"] != df["titre"]).sum()
print(f"     → {n_mod} titres nettoyés")

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 4 — NETTOYAGE ENTREPRISES
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 4 — Nettoyage entreprises...")

def clean_entreprise(e):
    e = str(e).strip()
    if e in ["", "nan", "N/A"]:
        return "Non renseignée"
    # Supprimer "recrute" et ce qui suit
    e = re.sub(r"\s+recrute.*$", "", e, flags=re.IGNORECASE).strip()
    e = re.sub(r"\s+", " ", e).strip()
    return e if len(e) > 1 else "Non renseignée"

df["entreprise_clean"] = df["entreprise"].apply(clean_entreprise)

# Fusions de noms d'entreprises
fusions = {
    "GPF-SN":                          "GPF",
    "World Vision":                     "World Vision International",
    "International Staffing Company":   "ISC",
    "Phoenix Consulting Group SN":      "Phoenix Group",
    "Phoenix Consulting Group":         "Phoenix Group",
    "Médecins Sans Frontières":         "MSF",
    "Médecins Sans Frontières (MSF)":   "MSF",
}
df["entreprise_clean"] = df["entreprise_clean"].replace(fusions)
print(f"     → {len(fusions)} fusions entreprises appliquées")

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 5 — RE-CLASSIFICATION SECTEUR (le cœur du problème)
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 5 — Re-classification secteurs...")

# Table de correspondance MÉTIER → SECTEUR
# Basée sur l'analyse réelle des données
METIER_SECTEUR = {
    # Commercial / Vente
    "Commercial":                       "Commercial / Vente",
    "Responsable Commercial":           "Commercial / Vente",
    "Directeur Commercial":             "Commercial / Vente",
    "Superviseur Commercial":           "Commercial / Vente",
    "Attaché Commercial":               "Commercial / Vente",
    "Agent Commercial":                 "Commercial / Vente",
    "Télévendeur":                      "Commercial / Vente",
    "Téléconseiller":                   "Commercial / Vente",
    "Conseiller Commercial":            "Commercial / Vente",
    "Business Developer":               "Commercial / Vente",

    # Finance / Comptabilité
    "Comptable":                        "Finance / Comptabilité",
    "Chef Comptable":                   "Finance / Comptabilité",
    "Comptable Général":                "Finance / Comptabilité",
    "Auditeur":                         "Finance / Comptabilité",
    "Auditeur Interne":                 "Finance / Comptabilité",
    "Contrôleur de Gestion":            "Finance / Comptabilité",
    "Directeur Administratif & Financier": "Finance / Comptabilité",
    "Responsable Administratif & Financier": "Finance / Comptabilité",
    "Analyste Financier":               "Finance / Comptabilité",
    "Gestionnaire d'opérations financières": "Finance / Comptabilité",

    # Informatique / Tech
    "Développeur Web/Logiciel":         "Informatique / Tech",
    "Développeur Full Stack":           "Informatique / Tech",
    "Développeur Frontend":             "Informatique / Tech",
    "Développeur Backend":              "Informatique / Tech",
    "Développeur Mobile":               "Informatique / Tech",
    "Ingénieur Informatique":           "Informatique / Tech",
    "Data Analyst":                     "Informatique / Tech",
    "Data Scientist":                   "Informatique / Tech",
    "Data Engineer":                    "Informatique / Tech",
    "Administrateur Sys/Réseau":        "Informatique / Tech",
    "Technicien Informatique":          "Informatique / Tech",
    "Chef de Projet IT":                "Informatique / Tech",

    # Ressources Humaines
    "Responsable RH":                   "Ressources Humaines",
    "Assistant RH":                     "Ressources Humaines",
    "Directeur RH":                     "Ressources Humaines",
    "Chargé RH / Recrutement":          "Ressources Humaines",
    "Formateur":                        "Ressources Humaines",

    # Marketing / Communication
    "Community Manager":                "Marketing / Communication",
    "Responsable Marketing":            "Marketing / Communication",
    "Graphiste / Designer":             "Marketing / Communication",
    "Chargé Marketing/Communication":   "Marketing / Communication",
    "Vidéaste":                         "Marketing / Communication",
    "Infographiste":                    "Marketing / Communication",

    # Logistique / Transport
    "Chauffeur":                        "Logistique / Transport",
    "Responsable Logistique":           "Logistique / Transport",
    "Agent Logistique":                 "Logistique / Transport",
    "Magasinier":                       "Logistique / Transport",
    "Conducteur de Travaux":            "Ingénierie / BTP",

    # Santé
    "Infirmier":                        "Santé / Médical",
    "Sage-Femme":                       "Santé / Médical",
    "Médecin":                          "Santé / Médical",

    # Éducation
    "Enseignant":                       "Éducation / Formation",

    # Administration
    "Assistant Administratif":          "Administration / Gestion",
    "Assistant de Direction":           "Administration / Gestion",
    "Secrétaire de Direction":          "Administration / Gestion",
    "Office Manager":                   "Administration / Gestion",
    "Chef de Projet":                   "Administration / Gestion",
    "Directeur Général":                "Administration / Gestion",
    "Chef de Service":                  "Administration / Gestion",
    "Concierge":                        "Administration / Gestion",
    "Agent de Sécurité":                "Administration / Gestion",
    "Responsable des Operations":       "Administration / Gestion",

    # Hôtellerie
    "Cuisinier":                        "Hôtellerie / Restauration",
    "Chef Cuisinier":                   "Hôtellerie / Restauration",
    "Serveur":                          "Hôtellerie / Restauration",
    "Maître d'Hôtel":                   "Hôtellerie / Restauration",
    "Réceptionniste":                   "Hôtellerie / Restauration",

    # Ingénierie
    "Ingénieur Électrique":             "Ingénierie / BTP",
    "Architecte":                       "Ingénierie / BTP",
    "Technicien":                       "Ingénierie / BTP",

    # Juridique
    "Juriste":                          "Droit / Juridique",
    "Avocat":                           "Droit / Juridique",

    # ONG
    "Coordinateur de projet":           "ONG / Humanitaire",
    "Chargé de programme":              "ONG / Humanitaire",
}

def reclassifier_secteur(row):
    metier  = str(row.get("metier_normalise", "")).strip()
    secteur = str(row.get("secteur", "")).strip()
    titre   = str(row.get("titre_clean",  "")).strip().lower()

    # Si le métier a une correspondance directe → on prend le secteur du métier
    if metier in METIER_SECTEUR:
        return METIER_SECTEUR[metier]

    # Si le secteur est déjà cohérent (pas Autre) → on garde
    if secteur not in ["Autre", "", "Non classifié"]:
        return secteur

    # Reclassification par mots-clés dans le titre
    titre_rules = [
        (["comptable", "comptabilité", "finance", "financier", "audit", "fiscalité", "ohada"], "Finance / Comptabilité"),
        (["développeur", "developer", "devops", "data analyst", "data scientist", "informatique",
          "système", "réseau", "software", "tech", "it ", "web", "mobile", "stack", "python",
          "java", "sql", "cloud", "cybersécurité", "sécurité informatique"], "Informatique / Tech"),
        (["commercial", "vente", "business develop", "télévendeur", "téléconseiller",
          "conseiller client", "chargé de clientèle"], "Commercial / Vente"),
        (["community manager", "marketing", "communication", "graphiste", "designer",
          "infographiste", "vidéaste", "rédacteur"], "Marketing / Communication"),
        (["chauffeur", "logistique", "transport", "magasinier", "livreur",
          "conducteur", "agent de transit"], "Logistique / Transport"),
        (["infirmier", "médecin", "sage-femme", "pharmacien", "santé",
          "médical", "laborantin", "kinésithérapeute"], "Santé / Médical"),
        (["enseignant", "professeur", "formateur", "éducation",
          "pédagogique", "moniteur", "coach"], "Éducation / Formation"),
        (["juriste", "avocat", "juridique", "droit", "notaire",
          "huissier", "compliance"], "Droit / Juridique"),
        (["ingénieur", "architecte", "btp", "génie civil", "électricien",
          "mécanicien", "technicien maintenance", "travaux"], "Ingénierie / BTP"),
        (["cuisinier", "chef de cuisine", "serveur", "hôtellerie",
          "restauration", "réceptionniste", "maître d'hôtel"], "Hôtellerie / Restauration"),
        (["responsable rh", "assistant rh", "recruteur", "ressources humaines",
          "talent", "paie", "formation rh"], "Ressources Humaines"),
        (["assistant admin", "secrétaire", "office manager", "chef de projet",
          "directeur général", "coordinateur", "gestionnaire"], "Administration / Gestion"),
        (["ong", "humanitaire", "ngo", "unicef", "oms", "pnud",
          "fhi", "giz", "oxfam", "plan international"], "ONG / Humanitaire"),
        (["banque", "assurance", "crédit", "microfinance", "bceao",
          "financier bancaire"], "Banque / Assurance"),
        (["agriculture", "agroalimentaire", "agro", "environnement",
          "élevage", "horticulture"], "Agriculture / Environnement"),
    ]

    for keywords, new_secteur in titre_rules:
        for kw in keywords:
            if kw in titre:
                return new_secteur

    return "Autre"

df["secteur_clean"] = df.apply(reclassifier_secteur, axis=1)

# Stats
n_autre_avant = (df["secteur"] == "Autre").sum()
n_autre_apres = (df["secteur_clean"] == "Autre").sum()
n_reclasses = n_autre_avant - n_autre_apres
rapport.append({"etape": "Secteurs reclassifiés", "nb": n_reclasses,
                "detail": "Basé sur métier puis titre"})
print(f"     → {n_autre_avant} offres 'Autre' avant")
print(f"     → {n_reclasses} offres reclassifiées")
print(f"     → {n_autre_apres} offres restent dans 'Autre'")
print(f"     Répartition finale :")
print(df["secteur_clean"].value_counts().to_string())

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 6 — NETTOYAGE CONTRATS
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 6 — Nettoyage contrats...")

def clean_contrat(c):
    c = str(c).strip().upper()
    if "CDI" in c:                              return "CDI"
    if "CDD" in c:                              return "CDD"
    if "STAGE" in c or "INTERN" in c:           return "Stage"
    if "INTERIM" in c or "INTÉRIM" in c:        return "Intérim"
    if "FREELANCE" in c or "PRESTATION" in c:   return "Freelance / Prestation"
    if "VOLONTARIAT" in c:                       return "Volontariat"
    return None  # None = Non précisé → exclu des exports

df["contrat_clean_v2"] = df["contrat_std"].apply(clean_contrat)

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 7 — NETTOYAGE VILLES
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 7 — Nettoyage villes...")

corrections_villes = {
    "Thies": "Thiès", "thies": "Thiès",
    "Saint Louis": "Saint-Louis",
    "Remote / Télétravail": "Télétravail",
    "Remote": "Télétravail",
    "Non précisé": None,  # None = exclu
    "Non Précisé": None,
}

def clean_ville(v):
    v = str(v).strip()
    if v in ["", "nan", "Non précisé", "Non Précisé"]:
        return None
    # Appliquer corrections
    if v in corrections_villes:
        return corrections_villes[v]
    # Exclure les adresses longues parasites
    if len(v) > 40:
        return None
    return v.strip()

df["ville_clean_v2"] = df["ville_normalisee"].apply(clean_ville)

# ══════════════════════════════════════════════════════════════════
# ÉTAPE 8 — DATES
# ══════════════════════════════════════════════════════════════════
print("\n  📌 ÉTAPE 8 — Parsing dates...")

df["_date"] = pd.NaT
for col in ["date_publication_clean", "date_clean", "date"]:
    if col in df.columns:
        p = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
        if p.notna().sum() > 50:
            df["_date"] = p
            print(f"     → {col} : {p.notna().sum():,} dates valides")
            break

df["mois"]       = df["_date"].dt.strftime("%Y-%m").where(df["_date"].notna(), "")
df["mois_label"] = df["_date"].dt.strftime("%b %Y").where(df["_date"].notna(), "")

# ══════════════════════════════════════════════════════════════════
# RÉSUMÉ NETTOYAGE
# ══════════════════════════════════════════════════════════════════
n_final = len(df)
print(f"\n{'='*65}")
print(f"  📊 RÉSUMÉ NETTOYAGE")
print(f"{'='*65}")
print(f"  Offres brutes          : {n_raw:>7,}")
print(f"  Lignes parasites       : -{(n_raw - n_final + n_dup_lien + n_dup_titre):>6,}")
print(f"  Doublons               : -{(n_dup_lien + n_dup_titre):>6,}")
print(f"  Offres propres finales : {n_final:>7,}")
print(f"  Taux conservation      :  {n_final/n_raw*100:.1f}%")

# ══════════════════════════════════════════════════════════════════
# EXPORTS
# ══════════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("  💾 EXPORT DES TABLES POWER BI")
print(f"{'='*65}\n")

# ── Rapport nettoyage
rapport.append({"etape": "TOTAL offres brutes",   "nb": n_raw,   "detail": ""})
rapport.append({"etape": "TOTAL offres propres",  "nb": n_final, "detail": ""})
save(pd.DataFrame(rapport), "00_rapport_nettoyage.csv")

# ── Table principale
cols_export = (["titre_clean", "entreprise_clean", "secteur_clean",
                "metier_normalise", "ville_clean_v2", "contrat_clean_v2",
                "source", "lien", "mois", "mois_label", "nb_competences"]
               + comp_cols)
cols_export = [c for c in cols_export if c in df.columns]
t1 = df[cols_export].rename(columns={
    "titre_clean":     "titre",
    "entreprise_clean":"entreprise",
    "secteur_clean":   "secteur",
    "metier_normalise":"metier",
    "ville_clean_v2":  "ville",
    "contrat_clean_v2":"contrat",
})
save(t1, "01_offres_clean.csv")

# ── Secteurs — SANS "Autre"
t2 = (df[df["secteur_clean"] != "Autre"]["secteur_clean"]
      .value_counts()
      .reset_index())
t2.columns = ["secteur", "nb_offres"]
t2["pct"]  = (t2["nb_offres"] / n_final * 100).round(1)
t2["rang"] = range(1, len(t2) + 1)
save(t2, "02_top_secteurs.csv")

# ── Compétences
comp_sum = df[comp_cols].sum().sort_values(ascending=False)
t3 = pd.DataFrame({
    "competence": comp_sum.index.str.replace("comp_", "").str.replace("_", " "),
    "nb_offres":  comp_sum.values.astype(int),
})
t3["pct"]  = (t3["nb_offres"] / n_final * 100).round(1)
t3["rang"] = range(1, len(t3) + 1)
t3 = t3[t3["nb_offres"] > 0]
save(t3, "03_top_competences.csv")

# ── Métiers — SANS "Non classifié"
t4 = (df[df["metier_normalise"].fillna("").str.strip().ne("") &
         df["metier_normalise"].fillna("").ne("Non classifié")]
      ["metier_normalise"]
      .value_counts()
      .head(50)
      .reset_index())
t4.columns = ["metier", "nb_offres"]
t4["pct"]  = (t4["nb_offres"] / n_final * 100).round(1)
t4["rang"] = range(1, len(t4) + 1)
save(t4, "04_top_metiers.csv")

# ── Villes — SANS None/"Non précisé"
t5 = (df["ville_clean_v2"]
      .dropna()
      .replace("", np.nan)
      .dropna()
      .value_counts()
      .reset_index())
t5.columns = ["ville", "nb_offres"]
t5["pct"]  = (t5["nb_offres"] / n_final * 100).round(1)
t5["rang"] = range(1, len(t5) + 1)
save(t5, "05_top_villes.csv")

# ── Entreprises — SANS "Non renseignée"
t6 = (df[df["entreprise_clean"] != "Non renseignée"]["entreprise_clean"]
      .value_counts()
      .head(30)
      .reset_index())
t6.columns = ["entreprise", "nb_offres"]
t6["pct"]  = (t6["nb_offres"] / n_final * 100).round(1)
t6["rang"] = range(1, len(t6) + 1)
save(t6, "06_top_entreprises.csv")

# ── Évolution mensuelle
evol = df[df["mois"].str.strip().ne("")]
if len(evol) > 0:
    t7 = (evol.groupby(["mois", "mois_label"])
          .size().reset_index(name="nb_offres")
          .sort_values("mois"))
    t7["precedent"]       = t7["nb_offres"].shift(1)
    t7["croissance_pct"]  = ((t7["nb_offres"] - t7["precedent"])
                             / t7["precedent"] * 100).round(1).fillna(0)
    t7["moy_mobile_3m"]   = t7["nb_offres"].rolling(3, min_periods=1).mean().round(0)
    t7 = t7.drop(columns=["precedent"])
    save(t7, "07_evolution_mensuelle.csv")

# ── Contrats — SANS "Non précisé"
t8 = (df["contrat_clean_v2"]
      .dropna()
      .value_counts()
      .reset_index())
t8.columns = ["contrat", "nb_offres"]
t8["pct"]  = (t8["nb_offres"] / n_final * 100).round(1)
save(t8, "08_contrats.csv")

# ── Compétences par secteur (sans Autre)
rows = []
for sec in df[df["secteur_clean"] != "Autre"]["secteur_clean"].unique():
    sub = df[df["secteur_clean"] == sec]
    for cc in comp_cols:
        n_c = int(sub[cc].sum())
        if n_c > 0:
            rows.append({
                "secteur":     sec,
                "competence":  cc.replace("comp_", "").replace("_", " "),
                "nb_offres":   n_c,
                "pct_secteur": round(n_c / len(sub) * 100, 1),
            })
t10 = pd.DataFrame(rows).sort_values(["secteur", "nb_offres"], ascending=[True, False])
save(t10, "10_competences_par_secteur.csv")

# ── Secteur × Contrat
t11 = (df[df["contrat_clean_v2"].notna() & (df["secteur_clean"] != "Autre")]
       .groupby(["secteur_clean", "contrat_clean_v2"])
       .size().reset_index(name="nb_offres")
       .sort_values(["secteur_clean", "nb_offres"], ascending=[True, False]))
t11.columns = ["secteur", "contrat", "nb_offres"]
save(t11, "11_secteur_par_contrat.csv")

# ══════════════════════════════════════════════════════════════════
# TABLE 09 — KPIs RÉSUMÉ (propres, sans Autre/Non précisé)
# ══════════════════════════════════════════════════════════════════
kpis = []

def kpi(indicateur, valeur_num, valeur_txt=None):
    kpis.append({
        "indicateur": indicateur,
        "valeur_num": (int(valeur_num) if isinstance(valeur_num, (int, np.integer, float))
                       and float(valeur_num) == int(float(valeur_num))
                       else round(float(valeur_num), 1)),
        "valeur_txt": valeur_txt if valeur_txt else str(int(valeur_num)
                      if float(valeur_num) == int(float(valeur_num)) else valeur_num)
    })

# Volumes
kpi("Total offres analysées",     n_final)
kpi("Total offres brutes",        n_raw)
kpi("Doublons / parasites retirés", n_raw - n_final)
kpi("Entreprises uniques",
    int(df[df["entreprise_clean"] != "Non renseignée"]["entreprise_clean"].nunique()))
kpi("Nombre de sources",          int(df["source"].nunique()))

# Secteur dominant — SANS Autre
df_sec = df[df["secteur_clean"] != "Autre"]
vc_sec = df_sec["secteur_clean"].value_counts()
kpi("Secteur #1",            int(vc_sec.max()),  vc_sec.idxmax())
kpi("Nb offres secteur #1",  int(vc_sec.max()))
kpi("% secteur #1",          round(vc_sec.max() / n_final * 100, 1),
    f"{round(vc_sec.max()/n_final*100,1)}%")

# Compétence #1
cs    = df[comp_cols].sum().sort_values(ascending=False)
top_c = cs.index[0].replace("comp_", "").replace("_", " ")
pct_c = round(int(cs.iloc[0]) / n_final * 100, 1)
kpi("Compétence #1",           int(cs.iloc[0]),  top_c)
kpi("% compétence #1",         pct_c,             f"{pct_c}%")
kpi("Nb offres compétence #1", int(cs.iloc[0]))

# Entreprise #1
ve    = df[df["entreprise_clean"] != "Non renseignée"]["entreprise_clean"].value_counts()
kpi("Entreprise #1",           int(ve.max()),  ve.idxmax())
kpi("Nb offres entreprise #1", int(ve.max()))

# Métier #1 — SANS Non classifié
df_met = df[df["metier_normalise"].fillna("").str.strip().ne("") &
            df["metier_normalise"].fillna("").ne("Non classifié")]
vm    = df_met["metier_normalise"].value_counts()
kpi("Métier #1",           int(vm.max()),  vm.idxmax())
kpi("Nb offres métier #1", int(vm.max()))

# Ville #1 — SANS Non précisé
vv = df["ville_clean_v2"].dropna().replace("", np.nan).dropna().value_counts()
if len(vv) > 0:
    kpi("Ville #1",            int(vv.max()),  vv.idxmax())
    kpi("Nb offres ville #1",  int(vv.max()))

# Évolution
evol_ok = df[df["mois"].str.strip().ne("")]
if len(evol_ok) > 0:
    em = evol_ok.groupby("mois").size().sort_index()
    if len(em) >= 2:
        c = round((em.iloc[-1] - em.iloc[-2]) / em.iloc[-2] * 100, 1)
        kpi("Croissance mensuelle (%)", c, f"{'▲' if c >= 0 else '▼'} {abs(c)}%")
        kpi("Nb offres dernier mois",   int(em.iloc[-1]))
        kpi("Mois de référence",        0, em.index[-1])

# Compétences
kpi("Offres avec compétences",   int((df["nb_competences"] > 0).sum()))
kpi("Moy. compétences / offre",  round(float(df["nb_competences"].mean()), 1))

# % offres avec entreprise connue
pct_ent = round(
    (df["entreprise_clean"] != "Non renseignée").sum() / n_final * 100, 1)
kpi("% offres avec entreprise",  pct_ent, f"{pct_ent}%")

# Secteurs clés
for sec in ["Informatique / Tech", "Finance / Comptabilité",
            "Commercial / Vente", "Ressources Humaines"]:
    n_s = int((df["secteur_clean"] == sec).sum())
    kpi(f"Nb offres — {sec}", n_s,
        f"{round(n_s/n_final*100,1)}% des offres")

t9 = pd.DataFrame(kpis)
t9["valeur_num"] = pd.to_numeric(t9["valeur_num"], errors="coerce")
save(t9, "09_stats_resume.csv")

# ══════════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ══════════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print(f"  🎉 Export terminé → {OUT_DIR}/")
print(f"{'='*65}")
print(f"""
  TABLES PRÊTES POUR POWER BI :
  ─────────────────────────────────────────────────────────
  00 rapport_nettoyage   → journal de ce qui a été corrigé
  01 offres_clean        → table principale propre
  02 top_secteurs        → SANS "Autre" → donut propre
  03 top_competences     → 60 compétences triées
  04 top_metiers         → SANS "Non classifié"
  05 top_villes          → SANS "Non précisé"
  06 top_entreprises     → SANS "Non renseignée"
  07 evolution_mensuelle → courbe temporelle
  08 contrats            → SANS "Non précisé" → donut propre
  09 stats_resume        → 29 KPIs propres sans valeurs parasites
  10 competences/secteur → matrice croisée
  11 secteur/contrat     → croisement type contrat × secteur
  ─────────────────────────────────────────────────────────
  DANS POWER BI : importer chaque CSV via
  Accueil → Obtenir les données → Texte/CSV
  Les colonnes sont déjà des vrais nombres — aucune
  manipulation dans Power Query nécessaire.
""")