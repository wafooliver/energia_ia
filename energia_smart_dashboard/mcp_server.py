"""Serveur MCP ENERGIA : expose les indicateurs comme outils à un agent compatible MCP."""
from datetime import date
from mcp.server.fastmcp import FastMCP

from src.service import dashboard_summary, get_slots, get_profile, get_peaks, get_renewables

mcp = FastMCP(
    "ENERGIA MCP",
    instructions=(
        "Outils d'analyse du système électrique régional Centre-Val de Loire. "
        "Les indicateurs sont historiques et régionaux ; ils ne garantissent pas "
        "le prix de marché ni la disponibilité locale des bornes."
    ),
    host="127.0.0.1",
    port=8001,
)


@mcp.tool()
def get_energy_summary(start_date: str = "", end_date: str = "", day_types: list[str] | None = None) -> dict:
    """Retourne les KPI régionaux. Dates au format YYYY-MM-DD ; dates vides = période complète."""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return dashboard_summary(start, end, day_types)


@mcp.tool()
def find_best_charging_slots(start_date: str = "", end_date: str = "", day_types: list[str] | None = None, limit: int = 5) -> list[dict]:
    """Classe les meilleurs créneaux historiques consécutifs de 4 heures."""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return get_slots(start, end, day_types, limit)


@mcp.tool()
def get_consumption_profile(start_date: str = "", end_date: str = "", day_types: list[str] | None = None) -> list[dict]:
    """Retourne le profil moyen de consommation par heure et type de jour."""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return get_profile(start, end, day_types)


@mcp.tool()
def get_seasonal_consumption_peaks(start_date: str = "", end_date: str = "", day_types: list[str] | None = None) -> list[dict]:
    """Retourne les pics de consommation observés par saison."""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return get_peaks(start, end, day_types)


@mcp.tool()
def get_renewable_production_profile(start_date: str = "", end_date: str = "", day_types: list[str] | None = None) -> list[dict]:
    """Retourne la part renouvelable moyenne selon l'heure."""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return get_renewables(start, end, day_types)


if __name__ == "__main__":
    # Transport MCP HTTP (Streamable HTTP), port 8001 par défaut.
    mcp.run(transport="streamable-http")
