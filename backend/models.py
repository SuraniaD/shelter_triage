from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, UUID4
from datetime import datetime


# ── Auth ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    full_name: Optional[str] = None
    role: str = "staff"

class RefreshRequest(BaseModel):
    refresh_token: str


# ── Intake ───────────────────────────────────────────────────────

class IntakeRequest(BaseModel):
    intake_code: str = Field(..., description="e.g. INK-47291")
    species: str
    estimated_age: Optional[str] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    intake_source: str
    observed_behavior: str = Field(..., min_length=10)
    medical_notes: Optional[str] = None
    additional_context: Optional[str] = None


# ── Triage Report ────────────────────────────────────────────────

class BehavioralFlag(BaseModel):
    label: str
    severity: Literal["urgent", "caution", "info", "positive"]

class TriageReportData(BaseModel):
    urgency_tier: Literal[1, 2, 3]
    urgency_reason: str
    placement_type: str
    placement_icon: str
    placement_description: str
    behavioral_flags: List[BehavioralFlag] = []
    medical_flags: List[BehavioralFlag] = []
    next_steps: List[str] = []
    summary: str

class TriageReportResponse(TriageReportData):
    id: str
    intake_id: str
    model_used: str
    latency_ms: Optional[int] = None
    created_at: datetime

class IntakeResponse(BaseModel):
    id: str
    intake_code: str
    species: str
    estimated_age: Optional[str]
    breed: Optional[str]
    sex: Optional[str]
    intake_source: str
    observed_behavior: str
    medical_notes: Optional[str]
    additional_context: Optional[str]
    submitted_by: str
    created_at: datetime
    triage_report: Optional[TriageReportResponse] = None


# ── List / Pagination ────────────────────────────────────────────

class IntakeSummaryItem(BaseModel):
    id: str
    intake_code: str
    species: str
    estimated_age: Optional[str]
    breed: Optional[str]
    intake_source: str
    created_at: datetime
    submitted_by_name: Optional[str]
    urgency_tier: Optional[int]
    placement_type: Optional[str]
    summary: Optional[str]

class IntakeListResponse(BaseModel):
    items: List[IntakeSummaryItem]
    total: int
    page: int
    page_size: int


# ── Health ───────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    supabase_reachable: bool
