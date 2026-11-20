from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

PRODUCTION_COLS = ["thermique", "nucleaire", "eolien", "solaire", "hydraulique", "bioenergies"]
RENEWABLE_COLS = ["eolien", "solaire", "hydraulique", "bioenergies"]

def load_data(path):
    df = pd.read_parquet(path).copy()
    required = {"date_heure", "date", "heure", "jour_semaine", "type_jour", "consommation"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes obligatoires absentes : {sorted(missing)}")
    for col in ["consommation", *PRODUCTION_COLS, "pompage", "ech_physiques", "heure", "jour_semaine"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date_heure"] = pd.to_datetime(df["date_heure"], errors="coerce", utc=True)
    df = df.dropna(subset=["date", "consommation", "heure"]).copy()
    for col in PRODUCTION_COLS:
        if col not in df:
            df[col] = 0.0
        df[col] = df[col].fillna(0).clip(lower=0)
    if "type_jour" not in df:
        df["type_jour"] = np.where(df["date"].dt.dayofweek >= 5, "week-end", "semaine")
    df["annee"] = df["date"].dt.year
    df["mois"] = df["date"].dt.month
    df["jour"] = df["date"].dt.day
    df["heure_entier"] = np.floor(df["heure"]).astype(int)
    df["heure_label"] = df["heure"].map(lambda x: f"{int(x):02d}:{'30' if x % 1 else '00'}")
    df["renouvelable"] = df[RENEWABLE_COLS].sum(axis=1)
    df["production_totale"] = df[PRODUCTION_COLS].sum(axis=1)
    df["part_renouvelable"] = np.where(df.production_totale > 0,
                                      df.renouvelable / df.production_totale * 100, 0)
    df["saison"] = df["mois"].map({12:"Hiver",1:"Hiver",2:"Hiver",3:"Printemps",4:"Printemps",5:"Printemps",
                                   6:"Été",7:"Été",8:"Été",9:"Automne",10:"Automne",11:"Automne"})
    return df.sort_values("date").reset_index(drop=True)

def filter_data(df, start_date, end_date, day_type):
    mask = df["date"].dt.date.between(start_date, end_date)
    if day_type:
        mask &= df["type_jour"].isin(day_type)
    else:
        return df.iloc[0:0].copy()
    return df.loc[mask].copy()

def kpis(df):
    return {
        "consommation_moyenne": float(df["consommation"].mean()),
        "part_renouvelable": float(df["part_renouvelable"].mean()),
    }

def hourly_profile(df):
    return (df.groupby(["type_jour","heure"], as_index=False)
              .agg(consommation=("consommation","mean"), nombre_demi_heures=("consommation","size"))
              .sort_values(["type_jour","heure"])
              .assign(heure_label=lambda x: x["heure"].map(lambda h: f"{int(h):02d}:{'30' if h % 1 else '00'}")))

def seasonal_peaks(df):
    # Pic = maximum de consommation observé dans chaque saison sur la période filtrée.
    return (df.groupby("saison", as_index=False)["consommation"].max()
              .rename(columns={"consommation":"pic_mw"})
              .sort_values("pic_mw", ascending=False))

def renewable_share(df):
    x = df.groupby("heure", as_index=False).agg(renouvelable=("renouvelable","mean"),
                                                production=("production_totale","mean"))
    x["part_renouvelable"] = np.where(x.production > 0, x.renouvelable / x.production * 100, 0)
    x["heure_label"] = x["heure"].map(lambda h: f"{int(h):02d}:{'30' if h % 1 else '00'}")
    return x.sort_values("heure")

def best_four_hour_slots(df):
    """Classe les heures de départ sur une fenêtre de 4 h (8 demi-heures) par jour."""
    if df.empty:
        return pd.DataFrame()
    work = df.sort_values(["date","heure"]).copy()
    rows = []
    for day, group in work.groupby(work["date"].dt.date):
        group = group.sort_values("heure").reset_index(drop=True)
        if len(group) < 8:
            continue
        for i in range(len(group) - 7):
            window = group.iloc[i:i+8]
            # Exiger 8 demi-heures contiguës : écart total = 3 h 30.
            if len(window) != 8 or not np.allclose(np.diff(window["heure"].to_numpy()), 0.5):
                continue
            mean_demand = window["consommation"].mean()
            renew_share = (window["renouvelable"].sum() / window["production_totale"].sum() * 100
                           if window["production_totale"].sum() > 0 else 0)
            start = window.iloc[0]["heure"]
            end = (start + 4) % 24
            rows.append({"date": day, "debut": f"{int(start):02d}:{'30' if start % 1 else '00'}",
                         "fin": f"{int(end):02d}:{'30' if end % 1 else '00'}",
                         "consommation_moyenne_mw": mean_demand,
                         "part_renouvelable": renew_share})
    if not rows:
        return pd.DataFrame()
    candidates = pd.DataFrame(rows)
    # Agrégation par heure de départ pour éviter qu'une journée domine le classement.
    result = candidates.groupby(["debut","fin"], as_index=False).agg(
        consommation_moyenne_mw=("consommation_moyenne_mw","mean"),
        part_renouvelable=("part_renouvelable","mean"),
        nombre_jours=("date","nunique"))
    # Score transparent : demande basse (70 %) + part renouvelable haute (30 %).
    dmin, dmax = result.consommation_moyenne_mw.min(), result.consommation_moyenne_mw.max()
    rmin, rmax = result.part_renouvelable.min(), result.part_renouvelable.max()
    demand_score = 1 - (result.consommation_moyenne_mw - dmin) / (dmax - dmin) if dmax > dmin else 1
    renewable_score = ((result.part_renouvelable - rmin) / (rmax - rmin)) if rmax > rmin else 0.5
    result["score"] = (0.7 * demand_score + 0.3 * renewable_score) * 100
    return result.sort_values("score", ascending=False).reset_index(drop=True)

def train_forecast(df):
    """Random Forest avec split temporel ; la baseline est la moyenne du train."""
    data = df.sort_values("date_heure").copy()
    data["heure_sin"] = np.sin(2*np.pi*data["heure"]/24)
    data["heure_cos"] = np.cos(2*np.pi*data["heure"]/24)
    data["jour_sin"] = np.sin(2*np.pi*data["jour_semaine"]/7)
    data["jour_cos"] = np.cos(2*np.pi*data["jour_semaine"]/7)
    data["mois_sin"] = np.sin(2*np.pi*data["mois"]/12)
    data["mois_cos"] = np.cos(2*np.pi*data["mois"]/12)
    data["weekend"] = (data["type_jour"] == "week-end").astype(int)
    features = ["heure_sin","heure_cos","jour_sin","jour_cos","mois_sin","mois_cos","weekend"]
    X, y = data[features], data["consommation"]
    split = int(len(data)*0.8)
    if split < 10 or len(data)-split < 2:
        raise ValueError("Pas assez de données pour entraîner et tester le modèle.")
    model = RandomForestRegressor(n_estimators=120, max_depth=14, min_samples_leaf=3,
                                  random_state=42, n_jobs=-1)
    model.fit(X.iloc[:split], y.iloc[:split])
    pred = model.predict(X.iloc[split:])
    actual = y.iloc[split:].to_numpy()
    baseline = np.repeat(float(y.iloc[:split].mean()), len(actual))
    predictions = pd.DataFrame({"date_heure":data["date_heure"].iloc[split:].values,
                                "reel":actual, "prediction":pred})
    return {"mae":float(mean_absolute_error(actual,pred)),
            "rmse":float(np.sqrt(mean_squared_error(actual,pred))),
            "baseline_mae":float(mean_absolute_error(actual,baseline)),
            "n_test":len(actual), "predictions":predictions}
