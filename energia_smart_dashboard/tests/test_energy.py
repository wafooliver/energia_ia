import pandas as pd
from src.energy import filter_data, kpis, hourly_profile

def sample():
    return pd.DataFrame({
        "date": pd.to_datetime(["2025-01-06","2025-01-06","2025-01-11"]),
        "consommation":[100,120,80],
        "part_renouvelable":[20,30,40],
        "type_jour":["semaine","semaine","week-end"],
        "heure":[0.0,0.5,1.0],
    })

def test_filter_data_by_day_type():
    result = filter_data(sample(), pd.Timestamp("2025-01-01").date(),
                         pd.Timestamp("2025-01-31").date(), ["semaine"])
    assert len(result) == 2

def test_kpis():
    result = kpis(sample())
    assert result["consommation_moyenne"] == 100
    assert round(result["part_renouvelable"], 2) == 30

def test_hourly_profile():
    result = hourly_profile(sample())
    assert len(result) == 3
    assert "heure_label" in result.columns
