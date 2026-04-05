# 🐾 Shelter Intake Triage Assistant

An AI-powered intake triage tool built for animal shelter staff. Staff enter free-text observations about a newly arrived animal — behavior, physical condition, source — and receive an instant structured triage report: urgency tier, recommended placement, behavioral and medical flags, and step-by-step next actions.

No veterinary interpretation needed. No login required. Just open the link and start triaging.
Shelter Intake Triage Assistant- https://shelter-triage.streamlit.app/

---

## The Problem

Animal shelters process hundreds of intakes daily with limited staff capacity. Without structured triage, animals get placed incorrectly, urgent medical or behavioral cases go unidentified, and avoidable euthanasia decisions get made under time pressure. Most existing tools rely on rigid dropdown forms that miss the nuance in what a staff member actually observes.

---

## The Approach

The core insight is that shelter staff already know what they're seeing — they just need a system that can interpret their plain language and turn it into an actionable decision framework immediately.

Rather than forcing structured inputs, the tool accepts free-text behavioral notes and medical observations and passes them to a large language model that has been prompted to think like an experienced triage specialist. The LLM output is constrained to a strict JSON schema so every report has a consistent, predictable structure that the UI can render reliably.

The three-tier urgency system (Critical / Urgent / Stable) maps directly to shelter operational workflows: Tier 1 triggers immediate vet escalation, Tier 2 requires same-day assessment, Tier 3 enters standard processing. This keeps the output actionable rather than advisory.

Temperature is set low (0.2) on the LLM call to prioritize consistent structured output over creative variation — the goal is reliability, not creativity.

---

## Tech Stack

| Layer       | Technology                          | Reason                                                              |
|-------------|-------------------------------------|---------------------------------------------------------------------|
| Frontend    | Streamlit                           | Rapid UI, no JS required, easy for non-technical staff to use       |
| Backend     | FastAPI                             | Async, fast, clean REST API with automatic Swagger docs             |
| Database    | Supabase (PostgreSQL)               | Managed Postgres, built-in RLS, easy to set up, free tier generous  |
| LLM         | Ollama Cloud — `gpt-oss:120b`       | Free hosted inference, no GPU required, strong reasoning capability |
| Deployment  | Render (API) + Streamlit Cloud (UI) | Both have free tiers, GitHub-connected auto-deploy                  |

---

## Project Structure

```
shelter-triage/
├── backend/
│   ├── main.py          # FastAPI app — all 5 routes
│   ├── models.py        # Pydantic v2 request/response models
│   ├── llm.py           # Ollama Cloud integration + prompt engineering
│   └── db.py            # Supabase client + all query functions
├── frontend/
│   ├── app.py           # Entry point — intake form + triage report
│   ├── pages/
│   │   └── 2_history.py # Paginated intake history + detail view
│   └── utils/
│       ├── api.py       # All HTTP calls to FastAPI backend
│       └── session.py   # Session state helpers (no-op, open access)
├── supabase/
│   └── schema.sql       # Full DB schema, RLS policies, indexes
├── requirements.txt
└── README.md
```

---

## Data Architecture

### Tables

**`intakes`** — one row per animal intake submission

| Column               | Type        | Notes                                      |
|----------------------|-------------|--------------------------------------------|
| `id`                 | uuid (PK)   | Auto-generated                             |
| `intake_code`        | text        | Unique e.g. INK-47291, generated frontend  |
| `submitted_by`       | uuid        | Fixed anonymous UUID (no auth)             |
| `species`            | text        | Dog, Cat, Rabbit, etc.                     |
| `estimated_age`      | text        | Free-form age bucket                       |
| `breed`              | text        | Optional                                   |
| `sex`                | text        | Optional                                   |
| `intake_source`      | text        | Owner surrender, stray, impound, etc.      |
| `observed_behavior`  | text        | Free-text — primary LLM input              |
| `medical_notes`      | text        | Free-text — secondary LLM input            |
| `additional_context` | text        | Free-text — tertiary LLM input             |
| `deleted_at`         | timestamptz | Soft delete — null means active            |
| `created_at`         | timestamptz | Auto                                       |

**`triage_reports`** — one row per intake, stores LLM output

| Column                  | Type     | Notes                                        |
|-------------------------|----------|----------------------------------------------|
| `id`                    | uuid (PK)| Auto-generated                               |
| `intake_id`             | uuid (FK)| One-to-one with intakes, cascades on delete  |
| `urgency_tier`          | smallint | 1, 2, or 3                                   |
| `urgency_reason`        | text     | Plain-language tier justification            |
| `placement_type`        | text     | e.g. Isolation Ward, Foster Home             |
| `placement_icon`        | text     | Emoji for UI display                         |
| `placement_description` | text     | One-sentence placement explanation           |
| `behavioral_flags`      | jsonb    | Array of {label, severity} objects           |
| `medical_flags`         | jsonb    | Array of {label, severity} objects           |
| `next_steps`            | jsonb    | Ordered array of plain-language action items |
| `summary`               | text     | 2-3 sentence staff-facing summary            |
| `model_used`            | text     | Model name logged for auditability           |
| `latency_ms`            | integer  | LLM call duration for performance tracking   |
| `created_at`            | timestamptz | Auto                                      |

### Data Flow

```
Staff fills form (free-text behavior + medical notes)
        │
        ▼
Streamlit frontend (app.py)
        │  POST /intake
        ▼
FastAPI backend (main.py)
        │
        ├─── INSERT into intakes (Supabase)
        │
        ├─── POST /api/chat (Ollama Cloud → gpt-oss:120b)
        │         │
        │         └── Returns structured JSON report
        │
        ├─── INSERT into triage_reports (Supabase)
        │
        └─── GET intake + report → return to frontend
                │
                ▼
        Streamlit renders triage report
        (tier badge, placement, flags, next steps, summary)
```

### RLS Policy

Row Level Security is enabled on both tables. Since there is no user authentication, all reads and writes are permitted via the **service_role key** used exclusively by the FastAPI backend. The frontend never communicates with Supabase directly — all data access goes through the API layer.

### Soft Deletes

Intake records are never hard-deleted. Setting `deleted_at` removes them from all queries without destroying the audit trail. All queries filter `WHERE deleted_at IS NULL`.

---

## API Endpoints

| Method | Path              | Description                            |
|--------|-------------------|----------------------------------------|
| POST   | `/intake`         | Submit intake, run triage, return report |
| GET    | `/intake`         | Paginated list of all intakes          |
| GET    | `/intake/{id}`    | Single intake + full triage report     |
| DELETE | `/intake/{id}`    | Soft-delete an intake                  |
| GET    | `/health`         | System connectivity check              |

Interactive docs available at `https://your-render-url.onrender.com/docs`

---

## Triage Tiers

| Tier | Label    | Trigger                                                          | Staff Action                     |
|------|----------|------------------------------------------------------------------|----------------------------------|
| 🔴 1 | Critical | Immediate vet need or safety risk to staff / other animals       | Escalate to vet NOW              |
| 🟡 2 | Urgent   | Significant behavioral or medical concern needing same-day care  | Flag for assessment within hours |
| 🟢 3 | Stable   | No acute concerns identified                                     | Standard intake processing       |

---

## User Journey

### Submitting a New Intake

1. Staff member arrives at the app URL — the intake form loads immediately, no login required
2. A unique Intake ID (e.g. `INK-47291`) is auto-generated — regenerates on every page load and after every submission
3. Staff selects species, age, breed, sex, and intake source from dropdowns
4. Staff types free-text observations into **Observed Behavior** — this is the most important field and the primary input to the LLM
5. Optional: staff adds medical/physical notes and any additional context
6. Staff clicks **▶ Run Triage Assessment**
7. The backend receives the submission, saves the intake record, calls Ollama Cloud, saves the report, and returns the full result — typically in 5–15 seconds
8. The triage report renders on the right panel of the same page:
   - Urgency tier badge (colour-coded)
   - Recommended placement with description
   - Behavioral and medical flag chips
   - Numbered next steps in plain language
   - Staff summary paragraph
9. The intake ID resets automatically — staff can immediately begin the next intake

### Reviewing Past Intakes

1. Staff clicks **Intake History** in the sidebar
2. A paginated list of all past intakes appears on the left, sorted newest first, with tier icons
3. Staff can filter by free text (ID, species, breed) or by urgency tier
4. Clicking any record loads the full intake details and triage report on the right panel
5. Raw intake data (behavior notes, medical notes) is available in a collapsible section for reference

---

## Environment Variables

| Variable              | Used By  | Description                                  |
|-----------------------|----------|----------------------------------------------|
| `SUPABASE_URL`        | Backend  | Supabase project URL                         |
| `SUPABASE_SERVICE_KEY`| Backend  | Service role key — bypasses RLS for writes   |
| `OLLAMA_API_KEY`      | Backend  | Ollama Cloud API key                         |
| `OLLAMA_BASE_URL`     | Backend  | `https://ollama.com/api`                     |
| `OLLAMA_MODEL`        | Backend  | `gpt-oss:120b`                               |
| `BACKEND_URL`         | Frontend | FastAPI URL — set in Streamlit secrets       |

## Deployment

| Service          | Platform              | Config                                              |
|------------------|-----------------------|-----------------------------------------------------|
| Backend (FastAPI)| Render                | Root dir: repo root, Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Frontend (Streamlit) | Streamlit Cloud   | Main file: `frontend/app.py`, Secrets: `BACKEND_URL` |
| Database         | Supabase              | Run `supabase/schema.sql` in SQL Editor             |
| LLM              | Ollama Cloud          | API key from ollama.com dashboard                   |

---

## License

MIT
