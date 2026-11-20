from pathlib import Path
import sys
import streamlit as st
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from energy import load_data, filter_data, kpis, hourly_profile, seasonal_peaks, renewable_share, best_four_hour_slots, train_forecast
from assistant import build_energy_context, answer_with_groq, get_groq_config

st.set_page_config(page_title="ENERGIA | Centre-Val de Loire", page_icon="⚡", layout="wide")
st.title("ENERGIA — Pilotage intelligent de l'énergie")
st.caption("Aide à la décision pour décaler la recharge d'une flotte électrique | Source : RTE éCO2mix")

DATA_PATH = ROOT / "data" / "energie.parquet"
if not DATA_PATH.exists():
    st.error("Le fichier data/energie.parquet est absent. Lancez d'abord : `python scripts/download_data.py`")
    st.markdown("[Télécharger le Parquet depuis GitHub](https://github.com/jlkhermes38/awp-gabarit/raw/main/data/projets/energie.parquet)")
    st.stop()

@st.cache_data(show_spinner="Chargement et préparation des données…")
def get_data(path):
    return load_data(path)

df = get_data(str(DATA_PATH))
if df.empty:
    st.error("Le fichier ne contient aucune donnée exploitable.")
    st.stop()

# Filtres globaux
with st.sidebar:
    st.header("Filtres globaux")
    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    selected_dates = st.date_input("Période d'analyse", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)
    day_type = st.multiselect("Type de jour", ["semaine", "week-end"],
                              default=["semaine", "week-end"])
    st.divider()
    st.header("Exploration détaillée")
    years = sorted(df["annee"].dropna().unique().tolist())
    selected_year = st.selectbox("Année", years, index=len(years)-1)
    months = sorted(df.loc[df.annee == selected_year, "mois"].dropna().unique().tolist())
    selected_month = st.selectbox("Mois", months)
    days = sorted(df.loc[(df.annee == selected_year) & (df.mois == selected_month), "date"].dt.date.unique())
    selected_day = st.selectbox("Jour", days)

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates

view = filter_data(df, start_date, end_date, day_type)
if view.empty:
    st.warning("Aucune donnée pour cette combinaison de filtres.")
    st.stop()

metrics = kpis(view)
c1, c2, c3 = st.columns(3)
c1.metric("Consommation moyenne", f"{metrics['consommation_moyenne']:,.0f} MW")
c2.metric("Part renouvelable moyenne", f"{metrics['part_renouvelable']:.1f} %")
slots = best_four_hour_slots(view)
if slots.empty:
    best_label = "Données insuffisantes"
else:
    s = slots.iloc[0]
    best_label = f"{s['debut']}–{s['fin']}"
c3.metric("Créneau conseillé (4 h)", best_label)

st.info("**Décision métier :** programmer la recharge de la flotte sur les créneaux où la demande régionale est faible, tout en tenant compte de la contribution des renouvelables. Le classement est un indicateur historique, pas une garantie de disponibilité physique ou de prix bas.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Vue régionale", "Quand consommer ?", "Renouvelables", "Prévision ML", "Assistant IA"
])

with tab1:
    st.subheader("La demande régionale moyenne varie selon l'heure et le type de jour")
    profile = hourly_profile(view)
    fig = px.line(profile, x="heure_label", y="consommation", color="type_jour",
                  markers=True, labels={"heure_label":"Heure (Paris)", "consommation":"Consommation (MW)", "type_jour":"Jour"})
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Profil calculé sur {len(view):,} demi-heures filtrées.")
    st.subheader("Les pics hivernaux et estivaux permettent de comparer les saisons")
    peaks = seasonal_peaks(view)
    if not peaks.empty:
        fig2 = px.bar(peaks, x="saison", y="pic_mw", color="saison",
                      labels={"saison":"Saison", "pic_mw":"Pic de consommation (MW)"})
        st.plotly_chart(fig2, use_container_width=True)
        winter = peaks.loc[peaks.saison == "Hiver", "pic_mw"]
        summer = peaks.loc[peaks.saison == "Été", "pic_mw"]
        if len(winter) and len(summer):
            st.write(f"Écart du pic hiver–été : **{winter.iloc[0]-summer.iloc[0]:,.0f} MW**.")

with tab2:
    st.subheader("Les heures les moins chargées indiquent quand déplacer la recharge")
    profile = hourly_profile(view)
    low = profile.sort_values("consommation").groupby("type_jour").head(3)
    st.dataframe(low[["type_jour","heure_label","consommation","nombre_demi_heures"]], hide_index=True, use_container_width=True)
    st.subheader("Meilleurs créneaux consécutifs de quatre heures")
    st.caption("Classement historique : demande moyenne faible et part renouvelable élevée. Les 8 demi-heures doivent être consécutives dans une même journée.")
    if not slots.empty:
        st.dataframe(slots.head(10), hide_index=True, use_container_width=True)
        fig3 = px.bar(slots.head(10), x="debut", y="score", color="part_renouvelable",
                      hover_data=["fin","consommation_moyenne_mw","part_renouvelable","nombre_jours"],
                      labels={"debut":"Début du créneau","score":"Score d'opportunité","part_renouvelable":"Part renouvelable (%)"})
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Pas assez de demi-heures consécutives pour calculer un créneau.")

with tab3:
    st.subheader("La contribution renouvelable évolue selon les heures et les saisons")
    ren = renewable_share(view)
    fig4 = px.area(ren, x="heure_label", y="part_renouvelable",
                   labels={"heure_label":"Heure (Paris)","part_renouvelable":"Part renouvelable (%)"})
    st.plotly_chart(fig4, use_container_width=True)
    monthly = view.groupby(["annee","mois"], as_index=False).apply(
        lambda g: pd.Series({"part_renouvelable": g["renouvelable"].sum()/g["production_totale"].sum()*100
                             if g["production_totale"].sum() > 0 else 0}), include_groups=False
    ).reset_index(drop=True)
    if not monthly.empty:
        monthly["periode"] = monthly["annee"].astype(str) + "-" + monthly["mois"].astype(str).str.zfill(2)
        fig5 = px.line(monthly, x="periode", y="part_renouvelable", markers=True,
                       labels={"periode":"Mois","part_renouvelable":"Part renouvelable (%)"})
        st.plotly_chart(fig5, use_container_width=True)

with tab4:
    st.subheader("Le modèle estime la consommation à partir du calendrier")
    st.write("Modèle : Random Forest Regressor. Variables : heure, jour de semaine, mois, week-end et saison. Séparation chronologique entraînement/test pour éviter de mélanger passé et futur.")
    if len(view) < 500:
        st.warning("Au moins 500 observations sont recommandées pour entraîner et évaluer le modèle.")
    else:
        with st.spinner("Entraînement et évaluation du modèle…"):
            result = train_forecast(view)
        a, b, c = st.columns(3)
        a.metric("MAE test", f"{result['mae']:,.0f} MW")
        b.metric("RMSE test", f"{result['rmse']:,.0f} MW")
        c.metric("Baseline MAE", f"{result['baseline_mae']:,.0f} MW")
        st.caption(f"Évaluation sur {result['n_test']:,} demi-heures de test. La baseline prédit la moyenne de consommation de l'entraînement.")
        pred = result["predictions"].tail(500)
        fig6 = px.line(pred, x="date_heure", y=["reel","prediction"],
                       labels={"date_heure":"Date","value":"Consommation (MW)","variable":"Série"})
        st.plotly_chart(fig6, use_container_width=True)

with st.expander("Explorer les demi-heures (drill-down : année → mois → jour → demi-heure)"):
    detail = df[(df.annee == selected_year) & (df.mois == selected_month) & (df.date.dt.date == selected_day)]
    st.write(f"**{selected_day}** — {len(detail)} demi-heures")
    cols = [c for c in ["date_heure","heure","consommation","eolien","solaire","nucleaire","thermique","hydraulique","bioenergies","ech_physiques"] if c in detail.columns]
    st.dataframe(detail[cols], use_container_width=True, hide_index=True)

st.divider()
st.caption("Données : RTE, éCO2mix régional — Licence Ouverte 2.0. MW représente une puissance moyenne sur 30 minutes ; l'énergie correspondante en MWh vaut MW × 0,5.")


with tab5:
    st.subheader("ENERGIA AI — Votre assistant énergétique")
    st.write(
        "Posez une question sur les données RTE, les périodes de consommation, les énergies "
        "renouvelables ou la stratégie de recharge. Les réponses s'appuient sur les statistiques "
        "de la période et des filtres actuellement sélectionnés."
    )
    api_key, groq_model = get_groq_config()
    if not api_key:
        st.warning(
            "L'assistant IA n'est pas encore configuré. Ajoutez votre clé GROQ_API_KEY "
            "dans `.streamlit/secrets.toml` ou dans les variables d'environnement. "
            "Ne publiez jamais cette clé sur GitHub."
        )
        st.code('GROQ_API_KEY = "votre_cle_groq"', language="toml")
        st.markdown("Créer une clé sur [Groq Console](https://console.groq.com/keys).")

    if "energia_chat_history" not in st.session_state:
        st.session_state.energia_chat_history = []

    context = build_energy_context(view)
    with st.expander("Voir les données transmises à l'assistant"):
        st.text(context)

    suggestions = [
        "Quelle est l'heure où la consommation est la plus faible ?",
        "Quel est le meilleur créneau de quatre heures pour recharger ?",
        "Que constate-t-on entre les pics d'hiver et d'été ?",
        "Quand la part des énergies renouvelables est-elle la plus forte ?",
    ]
    st.caption("Exemples de questions")
    suggestion_cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        if suggestion_cols[i % 2].button(suggestion, key=f"energia_suggestion_{i}", use_container_width=True):
            st.session_state.energia_pending_question = suggestion

    for message in st.session_state.energia_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Posez votre question sur l'énergie…")
    question = question or st.session_state.pop("energia_pending_question", None)
    if question:
        st.session_state.energia_chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            if not api_key:
                response = (
                    "Je suis prêt à répondre, mais la clé API Groq n'est pas configurée. "
                    "Ajoutez GROQ_API_KEY dans les secrets Streamlit, puis relancez l'application."
                )
                st.warning(response)
            else:
                try:
                    with st.spinner("ENERGIA AI analyse les données sélectionnées…"):
                        response = answer_with_groq(
                            question=question,
                            context=context,
                            history=st.session_state.energia_chat_history[:-1],
                            api_key=api_key,
                            model=groq_model,
                        )
                    st.markdown(response)
                except Exception as exc:
                    response = (
                        "Je n'ai pas pu contacter le service IA. Vérifiez la clé Groq, le nom du "
                        "modèle et votre connexion. Détail technique : " + str(exc)
                    )
                    st.error(response)
        st.session_state.energia_chat_history.append({"role": "assistant", "content": response})

    if st.session_state.energia_chat_history and st.button("Effacer la conversation", key="clear_energia_chat"):
        st.session_state.energia_chat_history = []
        st.rerun()
