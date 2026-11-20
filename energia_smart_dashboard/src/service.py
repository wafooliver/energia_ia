"""Services partagés par l'API REST et le serveur MCP ENERGIA."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from datetime import date

import pandas as pd

from .energy import (
    best_four_hour_slots, filter_data, hourly_profile, kpis,
    load_data, renewable_share, seasonal_peaks,
)
from .assistant import build_energy_context, answer_with_groq, get_groq_config

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(os.getenv("ENERGIA_DATA_PATH", ROOT / "data" / "energie.parquet"))


@lru_cache(maxsize=1)
def get_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Fichier de données absent : {DATA_PATH}. Lancez python scripts/download_data.py"
        )
    return load_data(DATA_PATH)


def get_view(start_date: date | None = None, end_date: date | None = None,
             day_types: list[str] | None = None) -> pd.DataFrame:
    df = get_dataset()
    start = start_date or df["date"].min().date()
    end = end_date or df["date"].max().date()
    if start > end:
        raise ValueError("start_date doit être antérieure ou égale à end_date")
    allowed = {"semaine", "week-end"}
    selected = day_types if day_types is not None else list(allowed)
    if not selected or not set(selected).issubset(allowed):
        raise ValueError("day_types doit contenir 'semaine' et/ou 'week-end'")
    return filter_data(df, start, end, selected)


def dashboard_summary(start_date=None, end_date=None, day_types=None) -> dict:
    view = get_view(start_date, end_date, day_types)
    if view.empty:
        return {"observations": 0, "message": "Aucune donnée pour ces filtres."}
    stats = kpis(view)
    slots = best_four_hour_slots(view)
    best = slots.iloc[0].to_dict() if not slots.empty else None
    return {
        "periode_debut": str(view["date"].min().date()),
        "periode_fin": str(view["date"].max().date()),
        "observations": int(len(view)),
        "consommation_moyenne_mw": round(stats["consommation_moyenne"], 2),
        "part_renouvelable_moyenne_pct": round(stats["part_renouvelable"], 2),
        "meilleur_creneau_4h": best,
        "note": "Indicateur régional historique ; ne garantit ni prix bas ni disponibilité locale.",
    }


def get_slots(start_date=None, end_date=None, day_types=None, limit: int = 10) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("limit doit être compris entre 1 et 100")
    result = best_four_hour_slots(get_view(start_date, end_date, day_types))
    if result.empty:
        return []
    return result.head(limit).to_dict(orient="records")


def get_profile(start_date=None, end_date=None, day_types=None) -> list[dict]:
    result = hourly_profile(get_view(start_date, end_date, day_types))
    return result.to_dict(orient="records")


def get_peaks(start_date=None, end_date=None, day_types=None) -> list[dict]:
    result = seasonal_peaks(get_view(start_date, end_date, day_types))
    return result.to_dict(orient="records")


def get_renewables(start_date=None, end_date=None, day_types=None) -> list[dict]:
    result = renewable_share(get_view(start_date, end_date, day_types))
    return result.to_dict(orient="records")


def ask_energy_assistant(question: str, start_date=None, end_date=None,
                         day_types=None, history=None) -> str:
    if not question or len(question) > 4000:
        raise ValueError("La question doit contenir entre 1 et 4 000 caractères.")
    context = build_energy_context(get_view(start_date, end_date, day_types))
    api_key, model = get_groq_config()
    return answer_with_groq(question, context, history=history, api_key=api_key, model=model)
