from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (charts, dashas, interpret, panchanga, predictions,
                      strength, transits)

app = FastAPI(
    title="Kundali Engine API",
    version="0.1.0",
    description="Deterministic Vedic astrology calculation engine.",
)

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(charts.router)
app.include_router(dashas.router)
app.include_router(transits.router)
app.include_router(predictions.router)
app.include_router(interpret.router)
app.include_router(panchanga.router)
app.include_router(strength.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kundali-engine"}
