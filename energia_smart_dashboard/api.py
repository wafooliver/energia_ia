"""API REST FastAPI pour ENERGIA."""
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.service import (
    dashboard_summary, get_dataset, get_peaks, get_profile, get_renewables,
    get_slots, ask_energy_assistant,
)

app = FastAPI(
    title="ENERGIA API",
    description="API d'analyse énergétique régionale et d'aide à la recharge de flottes électriques.",
    version="1.0.0",
)
DayType = list[Literal["semaine", "week-end"]]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    start_date: date | None = None
    end_date: date | None = None
    day_types: DayType | None = None
    history: list[dict[str, str]] = Field(default_factory=list, max_length=8)


@app.get("/health", tags=["Système"])
def health():
    try:
        df = get_dataset()
        return {"status": "ok", "service": "energia-api", "rows": len(df)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/summary", tags=["Énergie"])
def summary(start_date: date | None = None, end_date: date | None = None,
            day_types: DayType | None = None):
    return safe_call(dashboard_summary, start_date, end_date, day_types)


@app.get("/api/v1/slots", tags=["Énergie"])
def slots(start_date: date | None = None, end_date: date | None = None,
          day_types: DayType | None = None, limit: int = 10):
    return safe_call(get_slots, start_date, end_date, day_types, limit)


@app.get("/api/v1/profile", tags=["Énergie"])
def profile(start_date: date | None = None, end_date: date | None = None,
            day_types: DayType | None = None):
    return safe_call(get_profile, start_date, end_date, day_types)


@app.get("/api/v1/seasonal-peaks", tags=["Énergie"])
def peaks(start_date: date | None = None, end_date: date | None = None,
          day_types: DayType | None = None):
    return safe_call(get_peaks, start_date, end_date, day_types)


@app.get("/api/v1/renewables", tags=["Énergie"])
def renewables(start_date: date | None = None, end_date: date | None = None,
               day_types: DayType | None = None):
    return safe_call(get_renewables, start_date, end_date, day_types)


@app.post("/api/v1/assistant/chat", tags=["Assistant IA"])
def assistant_chat(payload: ChatRequest):
    try:
        answer = ask_energy_assistant(
            payload.question, payload.start_date, payload.end_date,
            payload.day_types, payload.history,
        )
        return {"answer": answer, "model_provider": "Groq"}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Service IA indisponible : {exc}") from exc
