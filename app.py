import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ─── CONFIG PAGE ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Offres d'Emploi — Sénégal",
    page_icon="🇸🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS PERSONNALISÉ ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Fond général */
    .stApp { background-color: #0f1117; color: #ffffff; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1c2030;
        border-right: 1px solid #2d3347;
    }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    
    /* Cartes KPI */
    .kpi-card {
        background: #1c2030;
        border: 1px solid #2d3347;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .kpi-label {
        font-size: 12px;
        color: #8892a4;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 600;
        color: #4a9eff;
        line-height: 1.1;
    }
    .kpi-value-text {
        font-size: 18px;
        font-weight: 600;
        color: #ffffff;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 11px;
        color: #8892a4;
        margin-top: 4px;
    }
    
    /* Titres de section */
    .section-title {
        font-size: 12px;
        font-weight: 500;
        color: #8892a4;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1c2030 0%, #0f1117 100%);
        border-bottom: 1px solid #2d3347;
        padding: 16px 0;
        margin-bottom: 20px;
    }
    
    /* Masquer éléments Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Graphiques */
    .plot-container { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── CHARGEMENT DES DONNÉES ───────────────────────────────────────
@st.cache_data
def load_data():
    base = os.path.dirname(__file__)
    data_dir = os.path.join(base, "data")

    def read(filename):
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            return pd.read_csv(path, encoding="utf-8")
        return pd.DataFrame()

    return {
        "kpis":        read("09_stats_resume.csv"),
        "secteurs":    read("02_top_secteurs.csv"),
        "competences": read("03_top_competences.csv"),
        "metiers":     read("04_top_metiers.csv"),
        "villes":      read("05_top_villes.csv"),
        "entreprises": read("06_top_entreprises.csv"),
        "evolution":   read("07_evolution_mensuelle.csv"),
        "contrats":    read("08_contrats.csv"),
        "offres":      read("01_offres_clean.csv"),
        "comp_secteur":read("10_competences_par_secteur.csv"),
    }

data = load_data()

# ─── HELPERS KPI ─────────────────────────────────────────────────
def get_kpi_int(df, indicateur):
    row = df[df["indicateur"] == indicateur]
    if not row.empty:
        val = row["valeur_entier"].values[0]
        return int(val) if pd.notna(val) else 0
    return 0

def get_kpi_txt(df, indicateur):
    row = df[df["indicateur"] == indicateur]
    if not row.empty:
        return str(row["valeur_txt"].values[0])
    return "—"

def get_kpi_dec(df, indicateur):
    row = df[df["indicateur"] == indicateur]
    if not row.empty:
        val = row["valeur_decimal"].values[0]
        return float(val) if pd.notna(val) else 0.0
    return 0.0

kpis = data["kpis"]

# ─── COULEURS ────────────────────────────────────────────────────
COLORS = {
    "blue":    "#4a9eff",
    "green":   "#3ecf8e",
    "orange":  "#e87c44",
    "purple":  "#a78bfa",
    "pink":    "#ec4899",
    "yellow":  "#f59e0b",
    "bg":      "#0f1117",
    "panel":   "#1c2030",
    "border":  "#2d3347",
    "text":    "#ffffff",
    "subtext": "#8892a4",
}

SECTEUR_COLORS = [
    "#4a9eff", "#3ecf8e", "#a78bfa", "#f59e0b",
    "#e87c44", "#ec4899", "#06b6d4", "#84cc16",
    "#f43f5e", "#8b5cf6", "#14b8a6", "#fb923c",
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor=COLORS["panel"],
    plot_bgcolor=COLORS["panel"],
    font=dict(color=COLORS["text"], family="system-ui"),
    xaxis=dict(
        gridcolor=COLORS["border"],
        linecolor=COLORS["border"],
        tickfont=dict(color=COLORS["subtext"]),
    ),
    yaxis=dict(
        gridcolor=COLORS["border"],
        linecolor=COLORS["border"],
        tickfont=dict(color=COLORS["subtext"]),
    ),
)

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR — FILTRES
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🇸🇳 Filtres")
    st.markdown("---")

    # Filtre Secteur
    secteurs_list = ["Tous les secteurs"]
    if not data["secteurs"].empty:
        secteurs_list += sorted(data["secteurs"]["secteur"].dropna().unique().tolist())
    secteur_sel = st.selectbox("📂 Secteur", secteurs_list)

    # Filtre Contrat
    contrats_list = ["Tous contrats"]
    if not data["contrats"].empty:
        contrats_list += sorted(data["contrats"]["contrat"].dropna().unique().tolist())
    contrat_sel = st.selectbox("📋 Type de contrat", contrats_list)

    # Filtre Entreprise
    entreprises_list = ["Toutes les entreprises"]
    if not data["entreprises"].empty:
        entreprises_list += sorted(data["entreprises"]["entreprise"].dropna().unique().tolist())
    entreprise_sel = st.selectbox("🏢 Entreprise", entreprises_list)

    # Filtre Métier
    metiers_list = ["Tous les métiers"]
    if not data["metiers"].empty:
        metiers_list += sorted(data["metiers"]["metier"].dropna().unique().tolist())
    metier_sel = st.selectbox("💼 Métier", metiers_list)

    st.markdown("---")
    st.markdown(
        "<div style='font-size:11px;color:#8892a4;'>Données : avril 2026<br>9 sources scrapées</div>",
        unsafe_allow_html=True
    )

# ─── Appliquer les filtres sur offres ────────────────────────────
offres = data["offres"].copy() if not data["offres"].empty else pd.DataFrame()

if not offres.empty:
    if secteur_sel != "Tous les secteurs":
        offres = offres[offres["secteur"] == secteur_sel]
    if contrat_sel != "Tous contrats":
        offres = offres[offres["contrat"] == contrat_sel]
    if entreprise_sel != "Toutes les entreprises":
        offres = offres[offres["entreprise"] == entreprise_sel]
    if metier_sel != "Tous les métiers":
        offres = offres[offres["metier"] == metier_sel]

n_filtrees = len(offres)
filtre_actif = any([
    secteur_sel != "Tous les secteurs",
    contrat_sel != "Tous contrats",
    entreprise_sel != "Toutes les entreprises",
    metier_sel != "Tous les métiers",
])

# ═══════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<div style='margin-bottom:20px;'>
    <h1 style='font-size:24px;font-weight:600;margin:0;color:#ffffff;'>
        Analyse des Offres d'Emploi — Sénégal
    </h1>
    <p style='font-size:13px;color:#8892a4;margin:4px 0 0 0;'>
        14 848 offres propres · 9 sources · avril 2026
    </p>
</div>
""", unsafe_allow_html=True)

# Bannière filtre actif
if filtre_actif:
    st.info(f"🔍 **{n_filtrees:,} offres** correspondent à vos filtres", icon="🔍")

# ═══════════════════════════════════════════════════════════════════
# KPI CARDS
# ═══════════════════════════════════════════════════════════════════
col1, col2, col3, col4 = st.columns(4)

total = n_filtrees if filtre_actif else get_kpi_int(kpis, "Total offres analysées")
entreprises_n = get_kpi_int(kpis, "Entreprises uniques")
comp1 = get_kpi_txt(kpis, "Compétence #1")
pct_c1 = get_kpi_dec(kpis, "% compétence #1")
ent1 = get_kpi_txt(kpis, "Entreprise #1")
ent1_n = get_kpi_int(kpis, "Nb offres entreprise #1")

with col1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Total offres</div>
        <div class='kpi-value'>{total:,}</div>
        <div class='kpi-sub'>9 sources scrapées</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Entreprises</div>
        <div class='kpi-value'>{entreprises_n:,}</div>
        <div class='kpi-sub'>recruteurs uniques</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Compétence #1</div>
        <div class='kpi-value-text'>{comp1}</div>
        <div class='kpi-sub'>{pct_c1}% des offres</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Entreprise #1</div>
        <div class='kpi-value-text'>{ent1}</div>
        <div class='kpi-sub'>{ent1_n:,} offres publiées</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# LIGNE 1 — COMPÉTENCES + SECTEURS
# ═══════════════════════════════════════════════════════════════════
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown("<div class='section-title'>Top 10 compétences demandées</div>",
                unsafe_allow_html=True)

    # Si filtre secteur actif → compétences par secteur
    if secteur_sel != "Tous les secteurs" and not data["comp_secteur"].empty:
        comp_df = (data["comp_secteur"][data["comp_secteur"]["secteur"] == secteur_sel]
                   .nlargest(10, "nb_offres"))
    else:
        comp_df = data["competences"].head(10) if not data["competences"].empty else pd.DataFrame()

    if not comp_df.empty:
        fig_comp = px.bar(
            comp_df.sort_values("nb_offres"),
            x="nb_offres", y="competence",
            orientation="h",
            text="nb_offres",
            color_discrete_sequence=[COLORS["blue"]],
        )
        fig_comp.update_traces(textposition="outside",
                               textfont=dict(color=COLORS["subtext"], size=11))
        fig_comp.update_layout(
            **PLOTLY_LAYOUT,
            height=320,
            title=None,
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
        )
        st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Aucune donnée compétences disponible")

with col_right:
    st.markdown("<div class='section-title'>Répartition par secteur</div>",
                unsafe_allow_html=True)

    if not data["secteurs"].empty:
        sec_df = data["secteurs"].copy()

        # Surbrillance si filtre secteur actif
        if secteur_sel != "Tous les secteurs":
            sec_df["opacity"] = sec_df["secteur"].apply(
                lambda x: 1.0 if x == secteur_sel else 0.3)
            pull = sec_df["secteur"].apply(
                lambda x: 0.1 if x == secteur_sel else 0).tolist()
        else:
            sec_df["opacity"] = 1.0
            pull = [0] * len(sec_df)

        fig_donut = go.Figure(data=[go.Pie(
            labels=sec_df["secteur"],
            values=sec_df["nb_offres"],
            hole=0.5,
            pull=pull,
            marker=dict(colors=SECTEUR_COLORS[:len(sec_df)]),
            textinfo="percent",
            textfont=dict(size=11),
        )])
        fig_donut.update_layout(
            **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ["margin", "xaxis", "yaxis"]},
            height=320,
            showlegend=True,
            legend=dict(
                font=dict(size=10, color=COLORS["subtext"]),
                bgcolor="rgba(0,0,0,0)",
                orientation="v",
                x=1.0, y=0.5,
            ),
            margin=dict(l=0, r=120, t=10, b=10),
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════
# LIGNE 2 — ÉVOLUTION + ENTREPRISES
# ═══════════════════════════════════════════════════════════════════
col_left2, col_right2 = st.columns([1, 1.2])

with col_left2:
    st.markdown("<div class='section-title'>Évolution mensuelle des offres</div>",
                unsafe_allow_html=True)

    if not data["evolution"].empty:
        evol = data["evolution"].sort_values("mois")
        fig_evol = go.Figure()
        fig_evol.add_trace(go.Scatter(
            x=evol["mois_label"],
            y=evol["nb_offres"],
            mode="lines+markers+text",
            text=evol["nb_offres"],
            textposition="top center",
            textfont=dict(size=11, color=COLORS["green"]),
            line=dict(color=COLORS["green"], width=2.5),
            marker=dict(size=8, color=COLORS["green"],
                        line=dict(color=COLORS["panel"], width=2)),
            fill="tozeroy",
            fillcolor="rgba(62, 207, 142, 0.08)",
        ))
        fig_evol.update_layout(
            **PLOTLY_LAYOUT,
            height=280,
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
        )
        st.plotly_chart(fig_evol, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Aucune donnée d'évolution disponible")

with col_right2:
    st.markdown("<div class='section-title'>Top 8 entreprises qui recrutent</div>",
                unsafe_allow_html=True)

    if not data["entreprises"].empty:
        # Si filtre actif sur offres → recalculer top entreprises
        if filtre_actif and not offres.empty and "entreprise" in offres.columns:
            ent_df = (offres["entreprise"]
                      .value_counts()
                      .head(8)
                      .reset_index())
            ent_df.columns = ["entreprise", "nb_offres"]
        else:
            ent_df = data["entreprises"].head(8)

        fig_ent = px.bar(
            ent_df.sort_values("nb_offres"),
            x="nb_offres", y="entreprise",
            orientation="h",
            text="nb_offres",
            color_discrete_sequence=[COLORS["orange"]],
        )
        fig_ent.update_traces(textposition="outside",
                              textfont=dict(color=COLORS["subtext"], size=11))
        fig_ent.update_layout(
            **PLOTLY_LAYOUT,
            height=280,
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
        )
        st.plotly_chart(fig_ent, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════
# LIGNE 3 — CONTRATS + VILLES
# ═══════════════════════════════════════════════════════════════════
col_c, col_v = st.columns(2)

with col_c:
    st.markdown("<div class='section-title'>Répartition des contrats</div>",
                unsafe_allow_html=True)
    if not data["contrats"].empty:
        fig_cont = px.pie(
            data["contrats"],
            names="contrat",
            values="nb_offres",
            hole=0.4,
            color_discrete_sequence=SECTEUR_COLORS,
        )
        fig_cont.update_layout(
            **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ["margin", "xaxis", "yaxis"]},
            height=250,
            showlegend=True,
            legend=dict(font=dict(size=10, color=COLORS["subtext"]),
                        bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=10, b=10),
        )
        st.plotly_chart(fig_cont, use_container_width=True, config={"displayModeBar": False})

with col_v:
    st.markdown("<div class='section-title'>Top villes</div>",
                unsafe_allow_html=True)
    if not data["villes"].empty:
        villes_df = data["villes"].head(8)
        fig_villes = px.bar(
            villes_df.sort_values("nb_offres"),
            x="nb_offres", y="ville",
            orientation="h",
            text="nb_offres",
            color_discrete_sequence=[COLORS["purple"]],
        )
        fig_villes.update_traces(textposition="outside",
                                 textfont=dict(color=COLORS["subtext"], size=11))
        fig_villes.update_layout(
            **PLOTLY_LAYOUT,
            height=250,
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
        )
        st.plotly_chart(fig_villes, use_container_width=True,
                        config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    "<div style='text-align:center;font-size:11px;color:#8892a4;'>"
    "Données scrapées depuis 9 sources · Avril 2026 · "
    "Projet Analyse des Offres d'Emploi — Sénégal"
    "</div>",
    unsafe_allow_html=True
)