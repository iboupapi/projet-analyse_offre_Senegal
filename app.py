"""
app.py — Dashboard Streamlit : Analyse des Offres d'Emploi au Sénégal
======================================================================
Prérequis :
  1. python scraper/secteurs.py     (ajoute la colonne secteur)
  2. streamlit run app.py

Structure :
  Page 1 — Vue d'ensemble  (KPIs + résumé)
  Page 2 — Secteurs        (nombre d'offres par secteur, secteur dominant)
  Page 3 — Compétences     (top 10, nuage de points)
  Page 4 — Géographie      (répartition par ville)
  Page 5 — Temporalité     (évolution mensuelle, croissance)
  Page 6 — Offres          (table filtrée + téléchargement)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os, re
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Emploi Sénégal",
    page_icon="🇸🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette & thème ───────────────────────────────────────────────────────────
C_GREEN  = "#00e5a0"
C_BLUE   = "#00b4d8"
C_YELLOW = "#ffd166"
C_RED    = "#ff6b6b"
C_BG     = "#0a1628"
C_CARD   = "#0f2027"
C_TEXT   = "#c8dce6"
C_MUTED  = "#7a9aaa"

PALETTE  = [C_GREEN, C_BLUE, C_YELLOW, C_RED, "#a8dadc", "#e9c46a",
            "#06d6a0", "#118ab2", "#ef476f", "#ffd166", "#26c485", "#7209b7"]

PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color=C_TEXT),
    margin=dict(l=10, r=10, t=40, b=10),
    colorway=PALETTE,
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {{ font-family:'DM Sans',sans-serif; }}
h1,h2,h3 {{ font-family:'Syne',sans-serif !important; }}
.stApp {{ background:{C_BG}; }}
section[data-testid="stSidebar"] {{ background:#0d1b2a; border-right:1px solid #1e3a4a; }}

/* KPI Card */
.kpi {{ background:linear-gradient(135deg,#0f2027,#203a43);
        border-radius:14px; padding:1.2rem 1.4rem;
        border-left:4px solid {C_GREEN};
        box-shadow:0 4px 24px rgba(0,0,0,.35); height:100%; }}
.kpi-label {{ font-size:.7rem; text-transform:uppercase; letter-spacing:.12em;
              color:{C_MUTED}; margin-bottom:.25rem; }}
.kpi-value {{ font-family:'Syne',sans-serif; font-weight:800; color:{C_GREEN}; line-height:1.1; }}
.kpi-sub   {{ font-size:.75rem; color:{C_MUTED}; margin-top:.2rem; }}

/* Section header */
.sec {{ font-family:'Syne',sans-serif; font-size:1rem; font-weight:700;
        color:#e8f4f8; border-bottom:2px solid {C_GREEN};
        padding-bottom:.3rem; margin-bottom:.8rem; }}

/* Metric delta positive */
.delta-pos {{ color:{C_GREEN}; font-weight:600; }}
.delta-neg {{ color:{C_RED};   font-weight:600; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════

BASE = os.path.dirname(os.path.abspath(__file__))

@st.cache_data(show_spinner="Chargement des données…")
def load():
    path = os.path.join(BASE, "data", "dataset_final.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False).fillna("N/A")

    # ── Date ─────────────────────────────────────────────────────────────────
    df["_date"] = pd.NaT
    for col in ["date_publication","date_limite","date"]:
        if col in df.columns:
            p = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if p.notna().sum() > 200:
                df["_date"] = p
                break
    df["_annee"] = df["_date"].dt.year.astype("Int64").astype(str).replace("<NA>","Inconnu")
    df["_mois_dt"]= df["_date"].dt.to_period("M")
    df["_mois"]   = df["_mois_dt"].astype(str).where(df["_date"].notna(), "Inconnu")

    # ── Ville ─────────────────────────────────────────────────────────────────
    if "ville_clean" not in df.columns:
        col_l = next((c for c in ["lieu","ville","localisation"] if c in df.columns), None)
        MAP = [("dakar","Dakar"),("thiès","Thiès"),("thies","Thiès"),
               ("saint-louis","Saint-Louis"),("saint","Saint-Louis"),
               ("ziguinchor","Ziguinchor"),("kaolack","Kaolack"),
               ("kolda","Kolda"),("touba","Touba"),("mbour","Mbour"),
               ("louga","Louga"),("diourbel","Diourbel")]
        def gv(x):
            x = str(x).lower()
            for kw,lb in MAP:
                if kw in x: return lb
            if x in ("n/a","","nan"): return "Non précisé"
            return "Autre"
        df["ville_clean"] = df[col_l].apply(gv) if col_l else "Non précisé"

    # ── Contrat ───────────────────────────────────────────────────────────────
    if "contrat_clean" not in df.columns:
        def gc(x):
            x = str(x).lower()
            if "cdi"   in x: return "CDI"
            if "cdd"   in x: return "CDD"
            if "stage" in x or "stagiaire" in x: return "Stage"
            if "free"  in x or "consult"   in x: return "Freelance"
            return "Non précisé"
        df["contrat_clean"] = df.get("contrat", pd.Series(["N/A"]*len(df))).apply(gc)

    # ── Secteur (si absent → lancer secteurs.py) ──────────────────────────────
    if "secteur" not in df.columns:
        df["secteur"] = "Non classifié"

    # ── Salaire numérique ────────────────────────────────────────────────────
    def ps(s):
        m = re.search(r"(\d[\d\s]{3,})", str(s).replace("\xa0",""))
        if m:
            v = float(re.sub(r"\s","", m.group(1)))
            return v if 30_000 <= v <= 15_000_000 else None
        return None
    df["_salaire"] = df.get("salaire", pd.Series(["N/A"]*len(df))).apply(ps)

    return df

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def kpi(label, value, sub="", accent=C_GREEN):
    size = "1.8rem" if len(str(value)) <= 8 else "1.1rem"
    return f"""<div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="font-size:{size};color:{accent}">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""

def sec(title):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)

def bar_h(series, title="", height=380, color=C_GREEN):
    s = series.sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h",
        marker=dict(color=s.values.tolist(),
                    colorscale=[[0,"#003d2b"],[1,color]], showscale=False),
        text=[f"{v:,}" for v in s.values],
        textposition="outside", textfont=dict(color=C_TEXT, size=11),
    ))
    fig.update_layout(**PLOTLY, height=height, title=title,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(tickfont=dict(size=12)))
    return fig

def bar_v(series, title="", height=340, color=C_GREEN):
    fig = go.Figure(go.Bar(
        x=series.index, y=series.values,
        marker=dict(color=series.values.tolist(),
                    colorscale=[[0,"#003d2b"],[1,color]], showscale=False),
        text=series.values, textposition="outside",
        textfont=dict(color=C_TEXT, size=11),
    ))
    fig.update_layout(**PLOTLY, height=height, title=title,
        xaxis=dict(tickangle=-30, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.05)"))
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    df = load()
    if df is None:
        st.error("❌ `data/dataset_final.csv` introuvable. Lance `python scraper/competences.py`")
        return

    comp_cols = [c for c in df.columns if c.startswith("comp_")]

    # ══════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown(f"## 🇸🇳 Emploi Sénégal")
        st.markdown("---")
        st.markdown("### 🎛️ Filtres globaux")

        src_all = sorted(df["source"].unique())
        src_sel = st.multiselect("Source", src_all, default=src_all,
                                 help="Sites de recrutement")

        vil_all = sorted(df["ville_clean"].unique())
        vil_sel = st.multiselect("Ville", vil_all, default=vil_all)

        cnt_all = sorted(df["contrat_clean"].unique())
        cnt_sel = st.multiselect("Type de contrat", cnt_all, default=cnt_all)

        sec_all = sorted(df["secteur"].unique())
        sec_sel = st.multiselect("Secteur", sec_all, default=sec_all)

        st.markdown("---")
        mois_ok = sorted([m for m in df["_mois"].unique()
                          if m not in ("Inconnu","NaT","nan","")])
        if mois_ok:
            m0 = st.selectbox("Période — De", mois_ok, index=0)
            m1 = st.selectbox("Période — À",  mois_ok, index=len(mois_ok)-1)
        else:
            m0 = m1 = None

        st.markdown("---")
        st.caption(f"Dataset : **{len(df):,}** offres")

    # ── Filtrage ──────────────────────────────────────────────────────────────
    mask = (df["source"].isin(src_sel) & df["ville_clean"].isin(vil_sel) &
            df["contrat_clean"].isin(cnt_sel) & df["secteur"].isin(sec_sel))
    if m0 and m1:
        mask &= (df["_mois"] >= m0) & (df["_mois"] <= m1)
    dff = df[mask].copy()

    if len(dff) == 0:
        st.warning("⚠️ Aucune offre ne correspond aux filtres sélectionnés.")
        return

    # ── Navigation ────────────────────────────────────────────────────────────
    pages = ["🏠 Vue d'ensemble","📂 Secteurs","🧠 Compétences",
             "🗺️ Géographie","📈 Temporalité","📋 Offres"]
    page  = st.sidebar.radio("Navigation", pages, index=0)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — VUE D'ENSEMBLE
    # ══════════════════════════════════════════════════════════════════════════
    if page == pages[0]:
        st.markdown("""
        <h1 style='font-family:Syne;color:#e8f4f8;margin-bottom:0'>
          🇸🇳 Offres d'Emploi au Sénégal</h1>
        <p style='color:#7a9aaa;margin-top:.2rem'>
          Analyse exploratoire · Marché du travail sénégalais</p>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # Calculs KPIs
        n = len(dff)
        top_ville  = dff["ville_clean"].value_counts()
        top_sec    = dff["secteur"].value_counts()
        top_cnt    = dff["contrat_clean"].value_counts()

        if comp_cols:
            cs   = dff[comp_cols].sum().sort_values(ascending=False)
            tc   = cs.index[0].replace("comp_","").replace("_"," ")
            tcn  = int(cs.iloc[0])
        else:
            tc, tcn = "N/A", 0

        # Croissance mensuelle (dernier mois vs avant-dernier)
        evol = dff[dff["_mois"] != "Inconnu"].groupby("_mois").size()
        if len(evol) >= 2:
            croiss = (evol.iloc[-1] - evol.iloc[-2]) / evol.iloc[-2] * 100
            croiss_str = f"{'▲' if croiss >= 0 else '▼'} {abs(croiss):.1f}% vs mois préc."
            croiss_col = C_GREEN if croiss >= 0 else C_RED
        else:
            croiss_str, croiss_col = "—", C_MUTED

        sal = dff["_salaire"].dropna()
        sal_str = f"{sal.mean():,.0f} FCFA" if len(sal) >= 5 else "N/D"

        # Row 1 KPIs
        c1,c2,c3,c4 = st.columns(4)
        c1.markdown(kpi("📊 Total des offres",      f"{n:,}",
                        f"sur {len(df):,} dans le dataset"), unsafe_allow_html=True)
        c2.markdown(kpi("🏙️ Ville #1",             top_ville.idxmax(),
                        f"{top_ville.max():,} offres ({top_ville.max()/n*100:.1f}%)"), unsafe_allow_html=True)
        c3.markdown(kpi("📂 Secteur dominant",      top_sec.idxmax(),
                        f"{top_sec.max():,} offres ({top_sec.max()/n*100:.1f}%)"), unsafe_allow_html=True)
        c4.markdown(kpi("🏆 Compétence #1",         tc,
                        f"{tcn:,} offres ({tcn/n*100:.1f}%)"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Row 2 KPIs
        c5,c6,c7,c8 = st.columns(4)
        c5.markdown(kpi("📈 Croissance mensuelle",  croiss_str, "dernier mois disponible",
                        croiss_col), unsafe_allow_html=True)
        c6.markdown(kpi("💰 Salaire moyen",         sal_str,
                        f"sur {len(sal)} offres renseignées"), unsafe_allow_html=True)
        c7.markdown(kpi("📄 Contrat le plus fréquent", top_cnt.idxmax(),
                        f"{top_cnt.max():,} offres ({top_cnt.max()/n*100:.1f}%)"), unsafe_allow_html=True)
        c8.markdown(kpi("🧠 Offres avec compétences",
                        f"{(dff['nb_competences']>0).sum():,}" if 'nb_competences' in dff.columns else "—",
                        f"sur {n:,} offres"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Aperçu rapide — 3 mini graphiques
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            sec("📂 Top 5 secteurs")
            s5 = dff["secteur"].value_counts().head(5)
            st.plotly_chart(bar_h(s5, height=280), use_container_width=True)

        with col_b:
            sec("🧠 Top 5 compétences")
            if comp_cols:
                cc5 = dff[comp_cols].sum().sort_values(ascending=True).tail(5)
                cc5.index = cc5.index.str.replace("comp_","").str.replace("_"," ")
                st.plotly_chart(bar_h(cc5, height=280, color=C_BLUE), use_container_width=True)

        with col_c:
            sec("🗺️ Top 5 villes")
            v5 = dff["ville_clean"].value_counts().head(5)
            st.plotly_chart(bar_h(v5, height=280, color=C_YELLOW), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — SECTEURS
    # ══════════════════════════════════════════════════════════════════════════
    elif page == pages[1]:
        st.markdown("<h2 style='font-family:Syne;color:#e8f4f8'>📂 Analyse par secteur</h2>",
                    unsafe_allow_html=True)
        st.markdown("---")

        sc_counts = dff["secteur"].value_counts()

        # KPI secteur dominant
        c1,c2,c3 = st.columns(3)
        c1.markdown(kpi("🏆 Secteur dominant",      sc_counts.idxmax(),
                        f"{sc_counts.max():,} offres ({sc_counts.max()/len(dff)*100:.1f}%)"),
                    unsafe_allow_html=True)
        c2.markdown(kpi("📊 Secteurs identifiés",   str(sc_counts[sc_counts.index!="Autre"].shape[0]),
                        "catégories distinctes"), unsafe_allow_html=True)
        non_classe = sc_counts.get("Autre",0) + sc_counts.get("Non classifié",0)
        c3.markdown(kpi("❓ Non classifiés",         f"{non_classe:,}",
                        f"{non_classe/len(dff)*100:.1f}% des offres"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([3,2])
        with col1:
            sec("Nombre d'offres par secteur")
            st.plotly_chart(bar_h(sc_counts, height=500), use_container_width=True)

        with col2:
            sec("Répartition (donut)")
            fig_pie = go.Figure(go.Pie(
                labels=sc_counts.index, values=sc_counts.values,
                hole=0.45,
                marker=dict(colors=PALETTE[:len(sc_counts)]),
                textfont=dict(size=10),
                textinfo="label+percent",
            ))
            fig_pie.update_layout(**PLOTLY, height=500,
                                  legend=dict(font=dict(size=10, color=C_TEXT)))
            st.plotly_chart(fig_pie, use_container_width=True)

        # Secteur × type de contrat
        st.markdown("<br>", unsafe_allow_html=True)
        sec("Secteurs × Type de contrat")
        pivot = dff.groupby(["secteur","contrat_clean"]).size().unstack(fill_value=0)
        fig_stack = go.Figure()
        for i, col in enumerate(pivot.columns):
            fig_stack.add_trace(go.Bar(
                name=col, x=pivot.index, y=pivot[col],
                marker_color=PALETTE[i % len(PALETTE)],
            ))
        fig_stack.update_layout(**PLOTLY, barmode="stack", height=380,
            xaxis=dict(tickangle=-30), yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.05)"),
            legend=dict(font=dict(color=C_TEXT)))
        st.plotly_chart(fig_stack, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — COMPÉTENCES
    # ══════════════════════════════════════════════════════════════════════════
    elif page == pages[2]:
        st.markdown("<h2 style='font-family:Syne;color:#e8f4f8'>🧠 Analyse des compétences</h2>",
                    unsafe_allow_html=True)
        st.markdown("---")

        if not comp_cols:
            st.warning("Aucune colonne `comp_*` trouvée. Lance `python scraper/competences.py`")
            return

        cc_all = dff[comp_cols].sum().sort_values(ascending=False)
        cc_all.index = cc_all.index.str.replace("comp_","").str.replace("_"," ")
        top10 = cc_all.head(10)

        # KPIs
        c1,c2,c3 = st.columns(3)
        c1.markdown(kpi("🏆 Compétence #1", top10.index[0],
                        f"{int(top10.iloc[0]):,} offres ({top10.iloc[0]/len(dff)*100:.1f}%)"),
                    unsafe_allow_html=True)
        c2.markdown(kpi("🏅 Compétence #2", top10.index[1],
                        f"{int(top10.iloc[1]):,} offres"), unsafe_allow_html=True)
        c3.markdown(kpi("🏅 Compétence #3", top10.index[2],
                        f"{int(top10.iloc[2]):,} offres"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([2,1])
        with col1:
            sec("Top 10 compétences demandées")
            fig = go.Figure(go.Bar(
                x=top10.values, y=top10.index, orientation="h",
                marker=dict(color=top10.values.tolist(),
                            colorscale=[[0,"#003d2b"],[1,C_GREEN]], showscale=False),
                text=[f"{v:,}  ({v/len(dff)*100:.1f}%)" for v in top10.values],
                textposition="outside", textfont=dict(color=C_TEXT, size=12),
            ))
            fig.update_layout(**PLOTLY, height=420,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(tickfont=dict(size=13)))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            sec("Top 10 — tableau")
            df_top = pd.DataFrame({
                "Compétence": top10.index,
                "Offres":     top10.values.astype(int),
                "% du total": (top10.values / len(dff) * 100).round(1),
            })
            st.dataframe(df_top, use_container_width=True, hide_index=True)

        # Toutes les compétences
        st.markdown("<br>", unsafe_allow_html=True)
        sec("Toutes les compétences détectées")
        fig2 = go.Figure(go.Bar(
            x=cc_all.index, y=cc_all.values,
            marker=dict(color=cc_all.values.tolist(),
                        colorscale=[[0,"#003d2b"],[1,C_BLUE]], showscale=False),
        ))
        fig2.update_layout(**PLOTLY, height=320,
            xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.05)"))
        st.plotly_chart(fig2, use_container_width=True)

        # Compétences par secteur
        if "secteur" in dff.columns:
            st.markdown("<br>", unsafe_allow_html=True)
            sec("Top 5 compétences par secteur")
            secteur_choisi = st.selectbox("Choisir un secteur",
                                          sorted(dff["secteur"].unique()))
            sub = dff[dff["secteur"] == secteur_choisi]
            if comp_cols:
                cc_sec = sub[comp_cols].sum().sort_values(ascending=False).head(5)
                cc_sec.index = cc_sec.index.str.replace("comp_","").str.replace("_"," ")
                if cc_sec.sum() > 0:
                    st.plotly_chart(bar_h(cc_sec.sort_values(), height=260, color=C_YELLOW),
                                    use_container_width=True)
                else:
                    st.info("Aucune compétence détectée pour ce secteur.")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — GÉOGRAPHIE
    # ══════════════════════════════════════════════════════════════════════════
    elif page == pages[3]:
        st.markdown("<h2 style='font-family:Syne;color:#e8f4f8'>🗺️ Répartition géographique</h2>",
                    unsafe_allow_html=True)
        st.markdown("---")

        vc = dff["ville_clean"].value_counts()
        vc_no_other = vc[~vc.index.isin(["Autre","Non précisé"])]

        c1,c2,c3 = st.columns(3)
        c1.markdown(kpi("🏙️ Ville #1", vc.idxmax(),
                        f"{vc.max():,} offres ({vc.max()/len(dff)*100:.1f}%)"),
                    unsafe_allow_html=True)
        c2.markdown(kpi("🏙️ Ville #2", vc.index[1] if len(vc)>1 else "—",
                        f"{vc.iloc[1]:,} offres" if len(vc)>1 else ""), unsafe_allow_html=True)
        c3.markdown(kpi("📍 Villes identifiées", str(len(vc_no_other)),
                        "villes distinctes"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns([3,2])
        with col1:
            sec("Nombre d'offres par ville")
            st.plotly_chart(bar_v(vc, height=360), use_container_width=True)

        with col2:
            sec("Répartition (donut)")
            fig_pie = go.Figure(go.Pie(
                labels=vc.index, values=vc.values, hole=0.45,
                marker=dict(colors=PALETTE[:len(vc)]),
                textfont=dict(size=10),
            ))
            fig_pie.update_layout(**PLOTLY, height=360,
                                  legend=dict(font=dict(size=10,color=C_TEXT)))
            st.plotly_chart(fig_pie, use_container_width=True)

        # Villes × secteurs
        st.markdown("<br>", unsafe_allow_html=True)
        sec("Top villes × secteur dominant")
        top_villes_list = vc_no_other.head(8).index.tolist()
        pivot_v = (dff[dff["ville_clean"].isin(top_villes_list)]
                   .groupby(["ville_clean","secteur"]).size()
                   .unstack(fill_value=0))
        fig_v = go.Figure()
        for i, col in enumerate(pivot_v.columns):
            fig_v.add_trace(go.Bar(
                name=col, x=pivot_v.index, y=pivot_v[col],
                marker_color=PALETTE[i % len(PALETTE)],
            ))
        fig_v.update_layout(**PLOTLY, barmode="stack", height=360,
            xaxis=dict(tickangle=-20),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.05)"),
            legend=dict(font=dict(size=9,color=C_TEXT)))
        st.plotly_chart(fig_v, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5 — TEMPORALITÉ
    # ══════════════════════════════════════════════════════════════════════════
    elif page == pages[4]:
        st.markdown("<h2 style='font-family:Syne;color:#e8f4f8'>📈 Évolution temporelle</h2>",
                    unsafe_allow_html=True)
        st.markdown("---")

        evol = (dff[dff["_mois"] != "Inconnu"]
                .groupby("_mois").size()
                .reset_index(name="nb")
                .sort_values("_mois"))

        if len(evol) < 2:
            st.info("Pas assez de données de dates pour afficher l'évolution.")
        else:
            # KPIs temporels
            dernier  = int(evol["nb"].iloc[-1])
            avantder = int(evol["nb"].iloc[-2])
            croiss   = (dernier - avantder) / avantder * 100 if avantder else 0
            pic_mois = evol.loc[evol["nb"].idxmax(), "_mois"]
            pic_n    = int(evol["nb"].max())

            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(kpi("📅 Mois avec le + d'offres", pic_mois,
                            f"{pic_n:,} offres"), unsafe_allow_html=True)
            c2.markdown(kpi("📈 Croissance mensuelle",
                            f"{'▲' if croiss>=0 else '▼'} {abs(croiss):.1f}%",
                            f"{dernier:,} vs {avantder:,} offres",
                            C_GREEN if croiss>=0 else C_RED), unsafe_allow_html=True)
            c3.markdown(kpi("📊 Moyenne mensuelle",
                            f"{evol['nb'].mean():,.0f}",
                            "offres / mois"), unsafe_allow_html=True)
            c4.markdown(kpi("🗓️ Période couverte",
                            f"{evol['_mois'].iloc[0]}",
                            f"→ {evol['_mois'].iloc[-1]}"), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Évolution mensuelle
            sec("Évolution mensuelle des offres")
            fig_evol = go.Figure()
            fig_evol.add_trace(go.Scatter(
                x=evol["_mois"], y=evol["nb"],
                mode="lines+markers",
                name="Offres",
                line=dict(color=C_GREEN, width=2.5),
                marker=dict(color=C_GREEN, size=6),
                fill="tozeroy", fillcolor="rgba(0,229,160,.08)",
            ))
            # Moyenne mobile 3 mois
            if len(evol) >= 3:
                evol["ma3"] = evol["nb"].rolling(3, center=True).mean()
                fig_evol.add_trace(go.Scatter(
                    x=evol["_mois"], y=evol["ma3"],
                    mode="lines", name="Moyenne mobile (3 mois)",
                    line=dict(color=C_YELLOW, width=2, dash="dot"),
                ))
            fig_evol.update_layout(**PLOTLY, height=360,
                xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.05)"),
                legend=dict(font=dict(color=C_TEXT)))
            st.plotly_chart(fig_evol, use_container_width=True)

            # Évolution par secteur
            sec("Évolution mensuelle par secteur (top 5)")
            top5_sec = dff["secteur"].value_counts().head(5).index.tolist()
            evol_sec = (dff[dff["_mois"].ne("Inconnu") & dff["secteur"].isin(top5_sec)]
                        .groupby(["_mois","secteur"]).size().reset_index(name="nb"))
            fig_sec = go.Figure()
            for i, s in enumerate(top5_sec):
                sub = evol_sec[evol_sec["secteur"]==s]
                fig_sec.add_trace(go.Scatter(
                    x=sub["_mois"], y=sub["nb"], mode="lines+markers",
                    name=s, line=dict(color=PALETTE[i], width=2),
                    marker=dict(size=5),
                ))
            fig_sec.update_layout(**PLOTLY, height=360,
                xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.05)"),
                legend=dict(font=dict(color=C_TEXT, size=10)))
            st.plotly_chart(fig_sec, use_container_width=True)

        # Salaires (si disponibles)
        sal = dff["_salaire"].dropna()
        if len(sal) >= 5:
            st.markdown("<br>", unsafe_allow_html=True)
            sec(f"💰 Distribution des salaires ({len(sal)} offres renseignées)")
            c1, c2 = st.columns(2)
            with c1:
                fig_sal = go.Figure(go.Histogram(
                    x=sal, nbinsx=25,
                    marker=dict(color=C_YELLOW, line=dict(color=C_BG, width=1)),
                ))
                fig_sal.update_layout(**PLOTLY, height=300,
                    xaxis_title="Salaire (FCFA)",
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.05)"))
                st.plotly_chart(fig_sal, use_container_width=True)
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(kpi("Salaire moyen",   f"{sal.mean():,.0f} FCFA",  ""), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(kpi("Salaire médian",  f"{sal.median():,.0f} FCFA","",C_BLUE), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(kpi("Salaire max",     f"{sal.max():,.0f} FCFA",   "",C_YELLOW), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 6 — TABLE DES OFFRES
    # ══════════════════════════════════════════════════════════════════════════
    elif page == pages[5]:
        st.markdown("<h2 style='font-family:Syne;color:#e8f4f8'>📋 Explorer les offres</h2>",
                    unsafe_allow_html=True)
        st.markdown("---")

        search = st.text_input("🔍 Rechercher dans les titres / entreprises",
                               placeholder="ex: développeur, comptable, ONG, Dakar…")

        cols_a = [c for c in ["titre","entreprise","secteur","ville_clean",
                               "contrat_clean","salaire","date_limite","source","lien"]
                  if c in dff.columns]
        dft = dff[cols_a].copy()
        dft.columns = [c.replace("_clean","").replace("_"," ").title() for c in cols_a]

        if search:
            mask_s = dft["Titre"].str.contains(search, case=False, na=False)
            if "Entreprise" in dft.columns:
                mask_s |= dft["Entreprise"].str.contains(search, case=False, na=False)
            dft = dft[mask_s]

        st.dataframe(
            dft.head(300), use_container_width=True, height=480,
            column_config={"Lien": st.column_config.LinkColumn("Lien", display_text="↗ Voir l'offre")},
        )
        st.caption(f"300 premières sur **{len(dft):,}** offres filtrées")

        st.download_button(
            "⬇️ Télécharger la sélection (CSV)",
            dff[cols_a].to_csv(index=False, encoding="utf-8-sig"),
            "offres_emploi_senegal.csv", "text/csv",
        )


if __name__ == "__main__":
    main()