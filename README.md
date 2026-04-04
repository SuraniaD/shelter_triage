# 🐾 Shelter Intake Triage Assistant

An AI-powered triage tool for animal shelter staff. Submit intake details via a Streamlit UI → FastAPI backend interprets free-text notes via **Ollama (llama3.1:8b)** → structured triage report stored in **Supabase**.

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | Streamlit                           |
| Backend    | FastAPI                             |
| Database   | Supabase (PostgreSQL + Auth)        |
| LLM        | Ollama Cloud — `llama3.1:8b`        |
| Auth       | Supabase Auth (email/password)      |

---

## Project Structure

```
shelter-triage/
├── backend/
│   ├── main.py              # FastAPI app — all routes
│   ├── models.py            # Pydantic request/response models
│   ├── llm.py               # Ollama Cloud integration
│   ├── db.py                # Supabase client + queries
│   └── auth.py              # JWT verification middleware
├── frontend/
│   ├── app.py               # Streamlit entry point
│   ├── pages/
│   │   ├── 1_intake.py      # New intake form
│   │   └── 2_history.py     # Past intakes + reports
│   └── utils/
│       ├── api.py           # HTTP calls to FastAPI
│       └── session.py       # Auth session helpers
├── supabase/
│   └── schema.sql           # Full DB schema + RLS policies
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_ORG/shelter-triage.git
cd shelter-triage
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials (see below)
```

### 3. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** → paste and run contents of `supabase/schema.sql`
3. Under **Authentication → Providers**, ensure Email is enabled
4. Copy your **Project URL** and **anon/service_role keys** into `.env`

### 4. Configure Ollama Cloud

1. Sign up at [ollama.com](https://ollama.com) and get your API key
2. Add it to `.env` as `OLLAMA_API_KEY`
3. The app uses model `llama3.1:8b` by default (configurable via `OLLAMA_MODEL`)

### 5. Run

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable                | Description                            |
|-------------------------|----------------------------------------|
| `SUPABASE_URL`          | Your Supabase project URL              |
| `SUPABASE_ANON_KEY`     | Supabase anon/public key               |
| `SUPABASE_SERVICE_KEY`  | Supabase service role key (backend)    |
| `OLLAMA_API_KEY`        | Ollama Cloud API key                   |
| `OLLAMA_BASE_URL`       | Ollama Cloud endpoint                  |
| `OLLAMA_MODEL`          | Model name (default: `llama3.1:8b`)    |
| `JWT_SECRET`            | Supabase JWT secret (for verification) |
| `BACKEND_URL`           | FastAPI URL as seen by Streamlit       |

---

## API Endpoints

| Method | Path                        | Description                        | Auth     |
|--------|-----------------------------|------------------------------------|----------|
| POST   | `/auth/login`               | Login, returns access token        | Public   |
| POST   | `/auth/refresh`             | Refresh access token               | Public   |
| POST   | `/intake`                   | Submit intake + run triage         | Required |
| GET    | `/intake`                   | List all intakes (paginated)       | Required |
| GET    | `/intake/{id}`              | Get single intake + report         | Required |
| DELETE | `/intake/{id}`              | Soft-delete an intake record       | Required |
| GET    | `/health`                   | Health check                       | Public   |

---

## Triage Tiers

| Tier | Label    | Meaning                                                         |
|------|----------|-----------------------------------------------------------------|
| 1    | Critical | Immediate vet attention or immediate safety risk                |
| 2    | Urgent   | Same-day assessment needed; significant behavioral/medical flag |
| 3    | Stable   | Standard intake processing; no acute concerns                   |

---

## Deployment Notes

- **Backend**: Deploy to Railway, Render, or Fly.io. Set all env vars in platform dashboard.
- **Frontend**: Deploy to Streamlit Community Cloud. Point `BACKEND_URL` to deployed FastAPI URL.
- **Database**: Supabase hosted — no additional deployment needed.
- **LLM**: Ollama Cloud — no self-hosting required.

---

## Contributing

PRs welcome. Please open an issue first for major changes.

## License

MIT
