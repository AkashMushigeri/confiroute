# HANDOFF SUMMARY — CONFIROUTE MILESTONE 2 (50%)

## 1. Milestone Completed
**Milestone 2:** Real Provider Layer (Ollama + Groq), Tier 2 Escalation & Acceptance Routing, FastAPI REST Backend Service, Clinician Human Review Queue, and Upgraded Streamlit Interface (~50% of total project specification).

---

## 2. Technical Architecture
```text
Medical Query + Options
          │
          ▼
┌─────────────────────────┐
│ Tier 1 Small Model      │ (Local Ollama / Mock)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Confidence Estimation   │ ──► S1: Token Prob (Numerically stable softmax)
│ (3 Signals)             │ ──► S2: Self-Consistency (N=3, T=0.7 agreement)
│                         │ ──► S3: Self-Rated Certainty (0-100 parsed to 0-1)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ High-Risk Safety Rule   │ ──► Dosage, Overdose, Cardiac, Pregnancy
└───────────┬─────────────┘
            │
    ┌───────┴───────────────┐
    │ High-Risk Match?       │
    │ YES                   │ NO
    ▼                       ▼
┌─────────────────┐  ┌──────────────────────────────────────────────┐
│ HUMAN REVIEW    │  │ Confidence Bands:                            │
│ (Override: Red) │  │ • Score >= 0.80  -> DIRECT ANSWER (Green)   │
│ Draft Withheld  │  │ • 0.50 <= S < 0.80 -> TIER 2 ESCALATION (Yellow) │
└─────────────────┘  │ • Score < 0.50   -> HUMAN REVIEW (Red)       │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │ Tier 2 Strong Model (Groq API / Free Tier)   │
                     │ • Re-evaluates S2, S3 with dynamic weights   │
                     │ • Tier 2 Score >= 0.80 -> DIRECT (Green)     │
                     │ • Tier 2 Score < 0.80  -> HUMAN (Red)        │
                     │ • API Quota / Offline -> Safe Pending State  │
                     └──────────────────────────────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │ FastAPI REST Backend & SQLite Persistence    │
                     │ • POST /ask, GET /queue, POST /review/{id}   │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │ Streamlit Demo & Clinician Review Queue      │
                     │ • app/Home.py (Traffic light meter)          │
                     │ • app/pages/1_Reviewer_Queue.py (Audit log)  │
                     └──────────────────────────────────────────────┘
```

---

## 3. Files Created & Modified in Milestone 2
- `src/confiroute/llm/providers.py` **[NEW]**: `BaseLLMProvider`, `OllamaProvider`, `GroqProvider`, `MockProvider`, and custom exceptions (`MissingAPIKeyError`, `ProviderUnavailableError`, `RateLimitExceededError`).
- `src/confiroute/llm/base.py` **[MODIFIED]**: Integrated `get_provider()`, latency measurement, and runtime provider override.
- `src/confiroute/llm/__init__.py` **[MODIFIED]**: Exported new provider classes and exceptions.
- `src/confiroute/confidence/combiner.py` **[MODIFIED]**: Added `extract_option_letter()`, provider passthrough, and dynamic token usage aggregation.
- `src/confiroute/routing/router.py` **[MODIFIED]**: Implemented full Tier 2 escalation, Tier 2 acceptance check ($\ge 0.80$), rejection fallback, and error handling.
- `src/confiroute/db/database.py` **[MODIFIED]**: Added review operations (`record_review_decision`, `get_pending_reviews`, `get_resolved_reviews`, `get_query_result`, `get_system_stats`).
- `src/confiroute/db/__init__.py` **[MODIFIED]**: Exported review query functions.
- `src/confiroute/api/main.py` **[NEW]**: FastAPI backend service with Pydantic validation, CORS, `/ask`, `/queue`, `/review/{id}`, `/result/{id}`, `/stats`.
- `src/confiroute/api/__init__.py` **[NEW]**: Package init.
- `app/Home.py` **[MODIFIED]**: Added Provider Selector (Mock vs Real), Ollama/Groq live status check, Tier 2 escalation presentation.
- `app/pages/1_Reviewer_Queue.py` **[NEW]**: Clinician Review Queue with Approve / Edit / Reject workflow, draft withholding, and resolved audit log.
- `requirements.txt` & `pyproject.toml` **[MODIFIED]**: Added `fastapi` and `httpx`.
- `tests/test_providers.py` **[NEW]**: 6 tests for Ollama/Groq providers, 429 backoff, missing keys.
- `tests/test_tier2_routing.py` **[NEW]**: 5 tests for Tier 2 escalation, acceptance, rejection, and error fallbacks.
- `tests/test_reviewer.py` **[NEW]**: 5 tests for clinician review lifecycle (approve, edit, reject).
- `tests/test_api.py` **[NEW]**: 6 tests for FastAPI REST endpoints using `TestClient`.
- `tests/test_routing.py` **[MODIFIED]**: Updated boundary condition test for Tier 1 mapping.
- `README.md` **[MODIFIED]**: Updated architecture, run instructions for FastAPI and Streamlit, Ollama hardware sizing, and Git instructions.

---

## 4. Verification & Test Results
- **Automated Test Suite:** **41 tests passed** in 4.11 seconds (100% pass rate).
- **FastAPI Endpoints Verified:** Tested `/health`, `/ask`, `/queue`, `/review/{id}`, `/result/{id}`, `/stats` with `TestClient`.
- **Database Status:** Full SQLite support for query logging, confidence signals, routing history, review actions, and cost tracking.
- **Offline / Mock Mode:** Fully functional without internet, credit card, or active API keys.

---

## 5. Real Model Integration Status & Recommendations

### Tier 1 (Local Ollama):
- **Provider Code:** Fully implemented in [`providers.py`](file:///c:/Users/akash/Desktop/confiroute-miniproject/confiroute/src/confiroute/llm/providers.py).
- **Hardware Analysis for 8 GB Laptop (~3 GB Free RAM):**
  - **Recommended Model:** `llama3.2:1b`
  - **Approximate Download Size:** ~1.3 GB
  - **Estimated RAM Footprint:** ~1.8 GB RAM (runs safely inside 3 GB available memory).
  - **Suitability:** Fast CPU inference (~20–40 tokens/sec on Intel CPU), official Ollama support.
  - **Alternative:** `qwen2.5:1.5b` (~1.0 GB download).
  - *User Approval Requirement:* As requested, model weights will only be downloaded after user confirmation.

### Tier 2 (Groq Free Tier):
- **Provider Code:** Fully implemented with automatic HTTP 429 exponential backoff in [`providers.py`](file:///c:/Users/akash/Desktop/confiroute-miniproject/confiroute/src/confiroute/llm/providers.py).
- **Model:** `llama-3.3-70b-versatile` (free tier compatible).
- **Status:** Ready. Requires user to add `GROQ_API_KEY` to `.env` (free key from [console.groq.com](https://console.groq.com)).

---

## 6. Commands to Run & Verify
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
.\.venv\Scripts\Activate.ps1

# Run complete test suite (41 tests)
pytest -v

# Run FastAPI Backend Server (Terminal 1)
uvicorn confiroute.api.main:app --port 8000 --reload

# Run Streamlit Web Application (Terminal 2)
streamlit run app/Home.py
```

---

## 7. Next Development Milestone (Milestone 3 / ~70%)
- **Phase 2 Calibration:** Fit logistic regression meta-model on `val.jsonl` features to optimize combined confidence.
- **Phase 3 Threshold Tuning:** Run grid search on validation set to find Pareto-optimal thresholds balancing accuracy, UCER, and escalation rate.
- **Phase 4 Side-by-Side View:** Build `app/pages/2_Side_by_Side.py` comparing unrouted baseline vs ConfiRoute.
- **Phase 5 Full Evaluation:** Execute baseline comparison (B0, B1, B2, B3) and answer-removal test on `test_removed.jsonl`.
