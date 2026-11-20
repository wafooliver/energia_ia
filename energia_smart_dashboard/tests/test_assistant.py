import pandas as pd

from src.assistant import build_energy_context


def test_build_energy_context_contains_filtered_period_and_kpis():
    dates = pd.date_range("2025-01-06", periods=16, freq="30min")
    df = pd.DataFrame({
        "date": dates.normalize(),
        "heure": [i / 2 for i in range(16)],
        "type_jour": ["semaine"] * 16,
        "consommation": [100 + i for i in range(16)],
        "part_renouvelable": [25.0] * 16,
        "saison": ["Hiver"] * 16,
        "renouvelable": [20.0] * 16,
        "production_totale": [80.0] * 16,
    })
    context = build_energy_context(df)
    assert "06/01/2025" in context
    assert "Consommation moyenne" in context
    assert "Créneaux de quatre heures" in context or "meilleurs créneaux" in context.lower()
