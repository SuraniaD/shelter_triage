"""
api.py — All HTTP calls from Streamlit to the FastAPI backend.
No auth headers required.
"""

import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

_HEADERS = {"Content-Type": "application/json"}


# ── Intake ───────────────────────────────────────────────────────

def submit_intake(payload: dict, token=None) -> tuple[dict | None, str | None]:
    try:
        r = requests.post(f"{BACKEND_URL}/intake", json=payload, headers=_HEADERS, timeout=120)
        if r.status_code == 201:
            return r.json(), None
        return None, r.json().get("detail", f"Error {r.status_code}")
    except requests.exceptions.Timeout:
        return None, "Request timed out — the AI model is taking too long. Try again."
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Is the API server running?"
    except Exception as e:
        return None, str(e)


def fetch_intakes(token=None, page: int = 1, page_size: int = 20) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(f"{BACKEND_URL}/intake",
                         params={"page": page, "page_size": page_size},
                         headers=_HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", f"Error {r.status_code}")
    except Exception as e:
        return None, str(e)


def fetch_intake(intake_id: str, token=None) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(f"{BACKEND_URL}/intake/{intake_id}", headers=_HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", f"Error {r.status_code}")
    except Exception as e:
        return None, str(e)


def delete_intake(intake_id: str, token=None) -> tuple[bool, str | None]:
    try:
        r = requests.delete(f"{BACKEND_URL}/intake/{intake_id}", headers=_HEADERS, timeout=10)
        if r.status_code == 204:
            return True, None
        return False, r.json().get("detail", f"Error {r.status_code}")
    except Exception as e:
        return False, str(e)


def fetch_health() -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return r.json()
    except Exception:
        return {"status": "unreachable", "ollama_reachable": False, "supabase_reachable": False}
