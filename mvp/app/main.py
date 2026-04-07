"""RiskPilot MVP — FastAPI entrypoint.

One endpoint: POST /api/briefing.
Takes a CSV of positions, returns a structured family office briefing.
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .briefing import generate_briefing
from .data import enrich_positions, fetch_macro_context

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("riskpilot")

app = FastAPI(title="RiskPilot MVP", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5"),
    }


@app.post("/api/briefing")
async def briefing(
    file: UploadFile = File(...),
    concerns: str = Form(default=""),
    client_name: str = Form(default="Family Office"),
):
    """Generate a weekly risk briefing from an uploaded positions CSV."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(500, "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file.")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    required = {"ticker", "quantity", "asset_class"}
    missing = required - set(df.columns.str.lower())
    if missing:
        raise HTTPException(400, f"CSV missing required columns: {sorted(missing)}. Required: {sorted(required)}")

    df.columns = [c.lower() for c in df.columns]
    log.info("parsed %d positions from %s", len(df), file.filename)

    try:
        enriched = enrich_positions(df)
        macro = fetch_macro_context()
    except Exception as e:
        log.exception("data enrichment failed")
        raise HTTPException(502, f"Market data fetch failed: {e}")

    try:
        result = generate_briefing(
            positions=enriched,
            macro=macro,
            concerns=concerns.strip() or None,
            client_name=client_name.strip() or "Family Office",
        )
    except Exception as e:
        log.exception("briefing generation failed")
        raise HTTPException(502, f"Briefing generation failed: {e}")

    return JSONResponse(
        {
            "briefing": result["briefing"],
            "portfolio_summary": result["portfolio_summary"],
            "macro": macro,
            "model": result["model"],
            "usage": result["usage"],
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
