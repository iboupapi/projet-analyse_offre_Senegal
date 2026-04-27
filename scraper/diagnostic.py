# diagnostic.py
# Lance ce script APRES avoir exécuté fusion.py
# Il affiche un résumé de merged_offres.csv à copier-coller ici

import pandas as pd
import os

CSV = "data/merged_offres.csv"

if not os.path.exists(CSV):
    print("❌ Fichier introuvable : data/merged_offres.csv")
    print("   → Lance d'abord : python fusion.py")
else:
    df = pd.read_csv(CSV)

    print("=" * 60)
    print(f"  TOTAL OFFRES : {len(df)}")
    print("=" * 60)

    print("\n📋 Colonnes disponibles :")
    print(list(df.columns))

    print("\n🌐 Sources :")
    print(df["source"].value_counts().to_dict())

    print("\n🔗 Liens N/A :")
    print((df["lien"] == "N/A").sum())

    print("\n👀 Aperçu (20 premières lignes) :")
    print(df[["titre", "source", "lien"]].head(20).to_string())

    print("\n📊 Exemple de lien par source :")
    for source, group in df.groupby("source"):
        exemple = group["lien"].dropna().iloc[0] if not group["lien"].dropna().empty else "N/A"
        print(f"  {source:<30} → {exemple}")