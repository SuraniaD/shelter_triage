"""
main.py — FastAPI backend for Shelter Intake Triage Assistant.

Routes:
  POST /intake              — Submit intake + run triage
  GET  /intake              — List intakes paginated
  GET  /intake/{id}         — Get single intake + report
  DELETE /intake/{id}       — Soft-delete an intake
  GET  /health              — Health check
"""

import random
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

import backend.db as db
import backend.llm as llm_module
from backend.models import (
    IntakeRequest,
    IntakeResponse,
    IntakeListResponse,
    HealthResponse,
)
from backend.llm import settings as llm_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Shelter Triage API starting up...")
    yield
    logger.info("Shelter Triage API shutting down.")


app = FastAPI(
    title="Shelter Intake Triage API",
    description="AI-powered triage for animal shelter intakes",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Intake Routes ────────────────────────────────────────────────

@app.post("/intake", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED, tags=["Intake"])
async def create_intake(body: IntakeRequest):
    """
    Submit a new animal intake and generate an AI triage report.
    Steps:
      1. Insert intake record into Supabase (retries on duplicate code)
      2. Call Ollama Cloud for triage analysis
      3. Store triage report in Supabase
      4. Return full intake + report
    """
    # 1. Persist intake — retry up to 3 times on duplicate intake_code
    intake_id = None
    for attempt in range(3):
        if attempt > 0:
            body.intake_code = f"INK-{random.randint(10000, 99999)}"
            logger.info("Retrying intake insert with new code: %s", body.intake_code)
        try:
            intake_id = await db.insert_intake(body, ANONYMOUS_USER_ID)
            break
        except Exception as e:
            if attempt < 2 and "23505" in str(e):
                continue
            logger.error("DB intake insert failed: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save intake record")

    # 2. Generate triage via Ollama
    try:
        report_data, latency_ms = await llm_module.generate_triage_report(body)
    except ValueError as e:
        logger.error("LLM parsing error for intake %s: %s", body.intake_code, e)
        raise HTTPException(status_code=502, detail=f"Triage generation failed: {e}")
    except Exception as e:
        logger.error("Ollama call failed for intake %s: %s", body.intake_code, e)
        raise HTTPException(status_code=502, detail="Could not reach AI service. Check Ollama Cloud config.")

    # 3. Persist triage report
    try:
        await db.insert_triage_report(
            intake_id=intake_id,
            report=report_data,
            model_used=llm_settings.ollama_model,
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error("DB report insert failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save triage report")

    # 4. Return full record
    result = await db.get_intake_with_report(intake_id)
    if not result:
        raise HTTPException(status_code=500, detail="Intake saved but could not be retrieved")
    return result


@app.get("/intake", response_model=IntakeListResponse, tags=["Intake"])
async def list_intakes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Return a paginated list of all non-deleted intakes with summary triage info."""
    items, total = await db.list_intakes(page=page, page_size=page_size)
    return IntakeListResponse(items=items, total=total, page=page, page_size=page_size)


@app.get("/intake/{intake_id}", response_model=IntakeResponse, tags=["Intake"])
async def get_intake(intake_id: str):
    """Fetch a single intake and its full triage report by UUID."""
    result = await db.get_intake_with_report(intake_id)
    if not result:
        raise HTTPException(status_code=404, detail="Intake not found")
    return result


@app.delete("/intake/{intake_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Intake"])
async def delete_intake(intake_id: str):
    """Soft-delete an intake record (sets deleted_at timestamp)."""
    deleted = await db.soft_delete_intake(intake_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Intake not found or already deleted")


# ── Health Check ─────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check whether Ollama Cloud and Supabase are reachable."""
    ollama_ok = await llm_module.check_ollama_reachable()
    supabase_ok = await db.check_supabase_reachable()
    return HealthResponse(
        status="ok" if (ollama_ok and supabase_ok) else "degraded",
        ollama_reachable=ollama_ok,
        supabase_reachable=supabase_ok,
    )
