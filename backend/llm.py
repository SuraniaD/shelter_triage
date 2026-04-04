"""
llm.py — Ollama Cloud integration for triage report generation.
Uses Ollama's native /api/chat endpoint.
"""

import json
import time
import logging

import httpx
from pydantic_settings import BaseSettings

from backend.models import IntakeRequest, TriageReportData

logger = logging.getLogger(__name__)


class OllamaSettings(BaseSettings):
    ollama_api_key: str
    ollama_base_url: str = "https://ollama.com/api"
    ollama_model: str = "llama3.1:8b"

    class Config:
        env_file = "../.env"
        extra = "ignore"


settings = OllamaSettings()

TRIAGE_SYSTEM_PROMPT = """You are an expert animal shelter triage specialist with 15+ years of experience.
Your role is to analyze animal intake information and produce a structured, actionable triage report
that non-technical shelter staff can act on immediately — no veterinary jargon unless clearly explained.

You MUST respond with ONLY a valid JSON object. No preamble, no explanation, no markdown fences.
Return raw JSON only."""

TRIAGE_USER_TEMPLATE = """Analyze this animal intake and return a triage report as JSON.

INTAKE DETAILS:
- Intake ID: {intake_code}
- Species: {species}
- Age: {age}
- Breed/Description: {breed}
- Sex: {sex}
- Intake Source: {source}
- Observed Behavior: {behavior}
- Medical/Physical Notes: {medical}
- Additional Context: {context}

Return ONLY this JSON structure (no extra text):
{{
  "urgency_tier": 1,
  "urgency_reason": "1-2 sentence plain-language reason for this tier",
  "placement_type": "Short placement name (e.g. Isolation Ward, Foster Home, General Population)",
  "placement_icon": "one relevant emoji",
  "placement_description": "One sentence: what this placement means in practice for staff",
  "behavioral_flags": [
    {{"label": "flag name", "severity": "urgent"}}
  ],
  "medical_flags": [
    {{"label": "flag name", "severity": "caution"}}
  ],
  "next_steps": [
    "Step 1: specific, plain-language action",
    "Step 2: specific, plain-language action",
    "Step 3: specific, plain-language action"
  ],
  "summary": "2-3 sentence plain-language summary a new staff member can immediately act on"
}}

Severity options: urgent, caution, info, positive
Urgency tier options: 1 (Critical - immediate vet/safety risk), 2 (Urgent - same-day assessment), 3 (Stable - standard processing)

Be compassionate, practical, and specific."""


async def generate_triage_report(intake: IntakeRequest) -> tuple[TriageReportData, int]:
    user_prompt = TRIAGE_USER_TEMPLATE.format(
        intake_code=intake.intake_code,
        species=intake.species,
        age=intake.estimated_age or "Unknown",
        breed=intake.breed or "Not specified",
        sex=intake.sex or "Unknown",
        source=intake.intake_source,
        behavior=intake.observed_behavior,
        medical=intake.medical_notes or "None provided",
        context=intake.additional_context or "None",
    )

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.ollama_api_key}",
        "Content-Type": "application/json",
    }

    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/chat",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    latency_ms = int((time.perf_counter() - start) * 1000)
    result = response.json()

    raw_content: str = result["message"]["content"].strip()

    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.strip()

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("LLM returned non-JSON: %s", raw_content[:500])
        raise ValueError(f"LLM returned invalid JSON: {e}") from e

    try:
        report = TriageReportData(**data)
    except Exception as e:
        logger.error("LLM JSON failed Pydantic validation: %s | Data: %s", e, data)
        raise ValueError(f"LLM response failed validation: {e}") from e

    logger.info(
        "Triage generated | intake=%s | tier=%s | latency=%dms",
        intake.intake_code, report.urgency_tier, latency_ms
    )
    return report, latency_ms


async def check_ollama_reachable() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            r = await client.get(
                f"{settings.ollama_base_url}/tags",
                headers={"Authorization": f"Bearer {settings.ollama_api_key}"},
            )
            return r.status_code == 200
    except Exception:
        return False
