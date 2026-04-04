"""
db.py — Supabase client and all database operations.
No auth — uses service_role key for all reads and writes.
"""

import logging
from typing import Optional
from datetime import datetime

from supabase import create_client, Client
from pydantic_settings import BaseSettings

from models import (
    IntakeRequest,
    TriageReportData,
    IntakeResponse,
    TriageReportResponse,
    IntakeSummaryItem,
)

logger = logging.getLogger(__name__)


class SupabaseSettings(BaseSettings):
    supabase_url: str
    supabase_service_key: str

    class Config:
        env_file = "../.env"
        extra = "ignore"


_settings = SupabaseSettings()
_client: Client = create_client(_settings.supabase_url, _settings.supabase_service_key)


def get_client() -> Client:
    return _client


# ── Intakes ──────────────────────────────────────────────────────

async def insert_intake(intake: IntakeRequest, user_id: str) -> str:
    """Insert a new intake record. Returns the new row UUID."""
    data = {
        "intake_code": intake.intake_code,
        "submitted_by": user_id,
        "species": intake.species,
        "estimated_age": intake.estimated_age,
        "breed": intake.breed,
        "sex": intake.sex,
        "intake_source": intake.intake_source,
        "observed_behavior": intake.observed_behavior,
        "medical_notes": intake.medical_notes,
        "additional_context": intake.additional_context,
    }
    result = _client.table("intakes").insert(data).execute()
    if not result.data:
        raise RuntimeError("Failed to insert intake record")
    return result.data[0]["id"]


async def insert_triage_report(
    intake_id: str,
    report: TriageReportData,
    model_used: str,
    latency_ms: Optional[int],
) -> str:
    """Insert a triage report linked to an intake. Returns new row UUID."""
    data = {
        "intake_id": intake_id,
        "urgency_tier": report.urgency_tier,
        "urgency_reason": report.urgency_reason,
        "placement_type": report.placement_type,
        "placement_icon": report.placement_icon,
        "placement_description": report.placement_description,
        "behavioral_flags": [f.model_dump() for f in report.behavioral_flags],
        "medical_flags": [f.model_dump() for f in report.medical_flags],
        "next_steps": report.next_steps,
        "summary": report.summary,
        "model_used": model_used,
        "latency_ms": latency_ms,
    }
    result = _client.table("triage_reports").insert(data).execute()
    if not result.data:
        raise RuntimeError("Failed to insert triage report")
    return result.data[0]["id"]


async def get_intake_with_report(intake_id: str) -> Optional[IntakeResponse]:
    """Fetch a single intake + its triage report by intake UUID."""
    result = (
        _client.table("intakes")
        .select("*, triage_reports(*)")
        .eq("id", intake_id)
        .is_("deleted_at", "null")
        .single()
        .execute()
    )
    if not result.data:
        return None
    return _row_to_intake_response(result.data)


async def list_intakes(page: int = 1, page_size: int = 20) -> tuple[list[IntakeSummaryItem], int]:
    """Paginated list of intakes. Returns (items, total_count)."""
    offset = (page - 1) * page_size

    count_result = (
        _client.table("intakes")
        .select("id", count="exact")
        .is_("deleted_at", "null")
        .execute()
    )
    total = count_result.count or 0

    result = (
        _client.table("intakes")
        .select("*, triage_reports(urgency_tier, placement_type, summary)")
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    items = [_row_to_summary_item(row) for row in (result.data or [])]
    return items, total


async def soft_delete_intake(intake_id: str) -> bool:
    """Soft-delete an intake by setting deleted_at. Returns True if found."""
    result = (
        _client.table("intakes")
        .update({"deleted_at": datetime.utcnow().isoformat()})
        .eq("id", intake_id)
        .is_("deleted_at", "null")
        .execute()
    )
    return bool(result.data)


async def check_supabase_reachable() -> bool:
    try:
        _client.table("intakes").select("id").limit(1).execute()
        return True
    except Exception:
        return False


# ── Row mappers ──────────────────────────────────────────────────

def _row_to_intake_response(row: dict) -> IntakeResponse:
    report_row = row.get("triage_reports")
    report = None
    if report_row:
        from models import BehavioralFlag
        report = TriageReportResponse(
            id=report_row["id"],
            intake_id=report_row["intake_id"],
            urgency_tier=report_row["urgency_tier"],
            urgency_reason=report_row["urgency_reason"],
            placement_type=report_row["placement_type"],
            placement_icon=report_row.get("placement_icon", "🏠"),
            placement_description=report_row["placement_description"],
            behavioral_flags=[BehavioralFlag(**f) for f in (report_row.get("behavioral_flags") or [])],
            medical_flags=[BehavioralFlag(**f) for f in (report_row.get("medical_flags") or [])],
            next_steps=report_row.get("next_steps") or [],
            summary=report_row["summary"],
            model_used=report_row["model_used"],
            latency_ms=report_row.get("latency_ms"),
            created_at=report_row["created_at"],
        )
    return IntakeResponse(
        id=row["id"],
        intake_code=row["intake_code"],
        species=row["species"],
        estimated_age=row.get("estimated_age"),
        breed=row.get("breed"),
        sex=row.get("sex"),
        intake_source=row["intake_source"],
        observed_behavior=row["observed_behavior"],
        medical_notes=row.get("medical_notes"),
        additional_context=row.get("additional_context"),
        submitted_by=row["submitted_by"],
        created_at=row["created_at"],
        triage_report=report,
    )


def _row_to_summary_item(row: dict) -> IntakeSummaryItem:
    report = row.get("triage_reports") or {}
    # triage_reports comes back as a list when using nested select
    if isinstance(report, list):
        report = report[0] if report else {}
    return IntakeSummaryItem(
        id=row["id"],
        intake_code=row["intake_code"],
        species=row["species"],
        estimated_age=row.get("estimated_age"),
        breed=row.get("breed"),
        intake_source=row["intake_source"],
        created_at=row["created_at"],
        submitted_by_name=None,
        urgency_tier=report.get("urgency_tier"),
        placement_type=report.get("placement_type"),
        summary=report.get("summary"),
    )
