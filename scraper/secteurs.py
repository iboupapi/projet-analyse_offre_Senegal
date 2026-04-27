"""
secteurs.py — Détection des secteurs d'activité
=================================================
À lancer UNE FOIS avant app.py :
    python scraper/secteurs.py

Lit data/dataset_final.csv, ajoute une colonne "secteur"
et resauvegarde dataset_final.csv.
"""

import pandas as pd
import re
import os

# Chemin depuis la racine ou depuis scraper/
for path in ["data/dataset_final.csv", "../data/dataset_final.csv"]:
    if os.path.exists(path):
        DATA_PATH = path
        break
else:
    raise FileNotFoundError("data/dataset_final.csv introuvable")

# ─── Dictionnaire secteurs ────────────────────────────────────────────────────
# Ordre important : du plus spécifique au plus général

SECTEURS = {
    "Informatique / Tech":     [r"\bdev(elop)?", r"\bprogramm", r"\binformat", r"\bsoftware\b",
                                 r"\bdata\b", r"\bweb\b", r"\bmobile\b", r"\bsyst[eè]me",
                                 r"\bréseau", r"\bcybersécurité", r"\bcloud\b", r"\bsupport\s+it",
                                 r"\btechnicien\s+(info|sys|réseau)"],
    "Finance / Comptabilité":  [r"\bcomptab", r"\bfinanci", r"\baudit", r"\bcontr[oô]l",
                                 r"\bfiscal", r"\btrésor", r"\bbudget", r"\bohada",
                                 r"\bcomptable\b", r"\bconseiller\s+financ"],
    "Ressources Humaines":     [r"\b(rh|drh)\b", r"\bressources\s+humaines", r"\brecrutement",
                                 r"\bformation\b", r"\bpaye\b", r"\btalent", r"\bpeople"],
    "Commercial / Vente":      [r"\bcommercial", r"\bvente", r"\bvendeur", r"\bvendeuse",
                                 r"\bchargé\s+de\s+client", r"\brelation\s+client",
                                 r"\bconseil(ler)?\s+de\s+vente", r"\breprésentant"],
    "Marketing / Communication":[r"\bmarketing", r"\bcommunication", r"\bcommunity",
                                  r"\bdigital", r"\bseo\b", r"\bchargé\s+de\s+comm",
                                  r"\brelations?\s+publiques", r"\bjournali", r"\brédact"],
    "Santé / Médical":         [r"\bmédecin", r"\binfirmier", r"\bsanté\b", r"\bhôpital",
                                 r"\bpharmacien", r"\blab(oratoire)?", r"\bsagefemme",
                                 r"\baide.soignant", r"\bchirurg", r"\bépidémio"],
    "Éducation / Formation":   [r"\benseignant", r"\bprofesseur", r"\bformateur",
                                 r"\béducation", r"\bpédagog", r"\bchargé\s+de\s+cours",
                                 r"\bchercheur", r"\bdoctorat", r"\buniversité"],
    "Ingénierie / BTP":        [r"\bingénieur", r"\barchitect", r"\btravaux", r"\bbtp\b",
                                 r"\bconstruction", r"\bgénie\s+civil", r"\bchantier",
                                 r"\btopograph", r"\bhydraul", r"\bmécanici"],
    "Logistique / Transport":  [r"\blogistique", r"\btransport", r"\bchauffeur",
                                 r"\blivreur", r"\bmagasinier", r"\bstock", r"\bapprovisio",
                                 r"\bsupply\s+chain", r"\bdouane", r"\bfret\b"],
    "Agriculture / Environnement":[r"\bagricult", r"\bagronom", r"\bélevage",
                                    r"\bpêche\b", r"\bforêt", r"\benvironnem",
                                    r"\bhydroagricole", r"\bvétérinaire", r"\birrigat"],
    "Droit / Juridique":       [r"\bjuriste", r"\bavocat", r"\bdroit\b", r"\bjuridique",
                                 r"\bcompliance", r"\bnotaire", r"\bparajuridique"],
    "Administration / Gestion":[r"\badministrat", r"\bsecrétaire", r"\bassistant",
                                 r"\bgestionnaire", r"\bcoordinat", r"\bdirecteur",
                                 r"\bmanager\b", r"\bresponsable\b", r"\bchef\s+de"],
    "Banque / Assurance":      [r"\bbanque\b", r"\bbancaire", r"\bassurance", r"\bcrédit",
                                 r"\bmicrofinance", r"\bconseiller\s+bancaire"],
    "ONG / Humanitaire":       [r"\bong\b", r"\bhumanitaire", r"\bcoopération",
                                 r"\bdéveloppement\s+international", r"\bngo\b",
                                 r"\bprojets?\s+(de\s+)?développement"],
    "Hôtellerie / Restauration":[r"\bhôtel", r"\brestauration", r"\bcuisinier",
                                  r"\bbarmaid?\b", r"\bréceptionniste", r"\btourisme",
                                  r"\bhébergement"],
    "Autre":                   [],   # fallback
}


def detecter_secteur(texte: str) -> str:
    t = str(texte).lower()
    for secteur, patterns in SECTEURS.items():
        if secteur == "Autre":
            continue
        if any(re.search(p, t) for p in patterns):
            return secteur
    return "Autre"


def ajouter_secteurs():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", low_memory=False)
    print(f"📂 {len(df)} offres chargées")

    # Texte combiné : titre + tags + description courte
    texte = (
        df.get("titre",       "").fillna("").astype(str) + " " +
        df.get("tags",        "").fillna("").astype(str) + " " +
        df.get("description", "").fillna("").astype(str)
    )

    df["secteur"] = texte.apply(detecter_secteur)

    # Stats
    print("\n📊 Répartition par secteur :")
    for s, n in df["secteur"].value_counts().items():
        print(f"  {s:<35} {n:>5}  ({n/len(df)*100:.1f}%)")

    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    print(f"\n✅ Colonne 'secteur' ajoutée → {DATA_PATH}")


if __name__ == "__main__":
    ajouter_secteurs()