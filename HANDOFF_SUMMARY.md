# HANDOFF SUMMARY — CONFIROUTE MILESTONE 1 (30%)

## 1. Milestone Completed
**Milestone 1:** Architecture Foundation, Mock LLM Engine, Triple Confidence Estimation, Risk Rules, Routing Engine, SQLite Persistence, and Streamlit Demo Interface (~30% of complete project scope).

---

## 2. Technical Architecture
```text
Question + Options -> ask_llm(Tier 1 Mock)
                   -> S1: Token Probability (Softmax over candidate logprobs)
                   -> S2: Self-Consistency (N=3 samples, Temp=0.7 agreement)
                   -> S3: Self-Rated Certainty (0-100 parsed to 0-1)
                   -> Combined Score (Redistributed weighted average)
                   -> High-Risk Regex Screening (Overdose, Dosage, Cardiac, Pregnancy)
                   -> Router:
                        • High-risk -> Human Review (Red, AI draft withheld)
                        • Score >= 0.80 -> Direct Answer (Green)
                        • 0.50 <= Score < 0.80 -> Tier 2 Escalation (Yellow, pending_tier2)
                        • Score < 0.50 -> Human Review (Red, pending_human)
                   -> Logged to SQLite (queries, signals, routes, costs)
                   -> Streamlit UI (Traffic light badges, presets, query history)
```

---

## 3. Files Created & Modified
- `config.yaml`: Central configuration (models, thresholds, weights, pricing, risk rules).
- `requirements.txt`: Lightweight CPU-friendly dependencies (numpy, pandas, pyyaml, streamlit, pytest, requests, pyarrow).
- `.env.example`: Template for future Groq/Gemini API keys.
- `.gitignore`: Ignoring `.venv`, `.env`, `.cache`, `data/raw`, SQLite `.db` files.
- `pyproject.toml`: Editable package configuration for `src/confiroute`.
- `src/confiroute/config.py`: Structured configuration loader.
- `src/confiroute/data/medmcqa_loader.py`: Parquet loader, option converter (`index_to_letter`), and validator.
- `src/confiroute/data/make_splits.py`: Split builder for DEV (50), VAL (200), and TEST (300).
- `src/confiroute/data/make_removed.py`: Split builder for TEST_REMOVED (200).
- `src/confiroute/llm/base.py`: Provider-agnostic `ask_llm()` and `LLMResponse` dataclass.
- `src/confiroute/llm/mock_provider.py`: Deterministic mock generator (sampling, logprobs, self-rating).
- `src/confiroute/llm/cache.py`: SHA-256 persistent disk cache.
- `src/confiroute/llm/pricing.py`: Zero-cost ($0.00) vs reference equivalent cost computation.
- `src/confiroute/confidence/token_prob.py`: S1 numerically stable softmax calculator.
- `src/confiroute/confidence/consistency.py`: S2 majority agreement fraction calculator.
- `src/confiroute/confidence/self_rating.py`: S3 robust regex parser for 0-100 scores.
- `src/confiroute/confidence/combiner.py`: Dynamic weight redistribution and `get_confidence()` orchestrator.
- `src/confiroute/routing/risk_rules.py`: High-risk regex pattern detector.
- `src/confiroute/routing/router.py`: `route_query()` and `RouteDecision` dataclass.
- `src/confiroute/db/schema.sql`: DDL for 6 SQLite tables.
- `src/confiroute/db/database.py`: Parameterized transactions and query helpers.
- `app/Home.py`: Streamlit demo application with presets and query history.
- `scripts/init_db.py`: CLI database initialization.
- `scripts/run_demo.py`: 20-question pipeline test and summary reporter.
- `tests/test_data.py`, `tests/test_llm.py`, `tests/test_confidence.py`, `tests/test_routing.py`, `tests/test_db.py`: 20 unit tests.
- `README.md`: Comprehensive setup and architecture guide.

---

## 4. Test & Verification Results
- **Pytest Suite:** 20 passed in 1.71s (100% pass rate).
- **MedMCQA Splits Created:**
  - DEV: 50 questions
  - VAL: 200 questions (disjoint from DEV)
  - TEST: 300 questions (from official validation split)
  - TEST_REMOVED: 200 questions (correct option deleted, re-lettered A-C)
- **Pipeline Demo Run (20 Questions):**
  - Direct Answers (Green): 5 (25.0%)
  - Tier 2 Escalated (Yellow): 10 (50.0%)
  - Human Review (Red): 5 (25.0%)
  - High-Risk Overrides: 0
  - Actual Money Spent: $0.00
  - Equivalent Reference Cost: $0.001129 USD
- **Database Status:** 6 tables created and populated (`queries`, `signals`, `routes`, `costs`, `reviews`, `alerts`).
- **Streamlit Web Demo:** Runs at `http://localhost:8501`, verified HTTP 200 OK.

---

## 5. Commands to Run & Verify
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
.\.venv\Scripts\Activate.ps1
pytest -v
python scripts/run_demo.py 20
streamlit run app/Home.py
```

---

## 6. Known Limitations
- Tier 1 and Tier 2 currently run in deterministic **Mock Mode** per Milestone 1 requirements.
- Logistic regression calibration meta-model (Phase 2) is not yet fitted.
- Clinician review queue UI (`pages/1_Reviewer_Queue.py`) is scheduled for Phase 4.

---

## 7. Next Development Step
**Phase 1 & Phase 2 Integration:** Connect local Ollama (Llama 3.2 3B or Qwen 2.5 3B) for Tier 1 with logprobs, connect Groq free-tier API for Tier 2, and fit logistic regression calibration on the VAL split.
