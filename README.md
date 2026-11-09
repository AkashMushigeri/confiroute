# ConfiRoute 🛡️

**Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans**

> **Research Prototype Disclaimer:** ConfiRoute is an AI safety research prototype evaluated on exam-style medical benchmarks (MedMCQA). It is **not** a diagnostic device and does **not** provide clinical advice. Critical emergency scenarios and low-certainty questions are held for clinician review.

---

## 📌 Project Overview (Milestone 2 — ~50% Complete)

Large Language Models (LLMs) often generate fluent, persuasive answers even when clinically incorrect ("hallucinations"). ConfiRoute is **not a new medical chatbot**; it is an intelligent **routing and safety layer** that sits between users and LLMs.

### System Architecture & Routing Flow:
```text
                     +---------------------------------------+
                     |          User Medical Query           |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |          Tier 1 (Small LLM)           |
                     |       (Local Ollama or Mock)          |
                     +---------------------------------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
+-------------------+           +-------------------+           +-------------------+
|  S1: Token Prob   |           | S2: Self-Consist. |           | S3: Self-Rating   |
| (Log-Prob Softmax)|           | (N=3 Samples, 0.7)|           |  (Scale 0 to 100) |
+-------------------+           +-------------------+           +-------------------+
         |                               |                               |
         +-------------------------------+-------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |       Combined Confidence Score       |
                     |      (Dynamic Redistributed Wavg)     |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |        High-Risk Safety Check         |
                     | (Dosage, Overdose, Cardiac, Pregnancy)|
                     +---------------------------------------+
                                         |
            +----------------------------+---------------------------+
            | High Risk Detected?                                    |
            | YES                                                    | NO
            v                                                        v
+------------------------+                     +-----------------------------------------+
|      HUMAN REVIEW      |                     | Check Confidence Score Bands:           |
| (Mandatory Override)   |                     | • Score >= 0.80 -> DIRECT ANSWER (🟢)   |
| Status: pending_human  |                     | • 0.50 <= Score < 0.80 -> TIER 2 (🟡)  |
| AI Draft Withheld      |                     | • Score < 0.50 -> HUMAN REVIEW (🔴)     |
+------------------------+                     +-----------------------------------------+
                                                                     |
                                                                     v
                                               +-----------------------------------------+
                                               |       Tier 2 Escalation (Groq API)      |
                                               | • Re-score with available signals (S2,S3)|
                                               | • Tier 2 Score >= 0.80 -> DIRECT (🟢)   |
                                               | • Tier 2 Score < 0.80  -> HUMAN (🔴)    |
                                               +-----------------------------------------+
```

---

## 💻 Hardware & Zero-Cost Constraints

ConfiRoute is engineered to run on standard consumer hardware with **₹0 budget**:
- **Operating System:** Windows 10/11 (PowerShell)
- **RAM:** 8 GB (~3 GB available memory)
- **CPU:** Standard ~1.6 GHz Intel CPU (no dedicated GPU required)
- **Dependencies:** Python 3.10+, FastAPI, Uvicorn, Streamlit, SQLite, NumPy, pandas, PyYAML, pytest, requests, pyarrow.
- **Provider Support:**
  - **Mock Mode:** 100% offline, deterministic, instant response.
  - **Tier 1 (Local Ollama):** Supports 1B–1.5B class models (`llama3.2:1b` or `qwen2.5:1.5b`) on localhost port 11434.
  - **Tier 2 (Cloud Groq):** Free tier API integration (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`) with automatic HTTP 429 exponential backoff.
- **Cost Policy:** Real cost is strictly **$0.00**; reference per-token pricing is tracked for cross-tier economic comparison.

---

## 📂 Repository Structure

```text
confiroute/
│
├── README.md                   # Project documentation and setup guide
├── HANDOFF_SUMMARY.md          # Milestone 2 handoff report
├── requirements.txt            # Lightweight, CPU-friendly dependencies
├── .env.example                # Template for Groq API keys
├── .gitignore                  # Git ignore rules for venv, caches, db, data/raw
├── config.yaml                 # System, model, confidence weights & risk rules
├── pyproject.toml              # Editable package configuration
│
├── data/
│   ├── raw/                    # Downloaded Hugging Face parquets (gitignored)
│   └── processed/              # DEV (50), VAL (200), TEST (300), TEST_REMOVED (200)
│
├── src/confiroute/
│   ├── config.py               # Configuration loader
│   ├── data/                   # medmcqa_loader.py, make_splits.py, make_removed.py
│   ├── llm/
│   │   ├── base.py             # ask_llm() unified interface & LLMResponse
│   │   ├── providers.py        # MockProvider, OllamaProvider, GroqProvider
│   │   ├── mock_provider.py    # Deterministic mock engine with logprobs
│   │   ├── cache.py            # SHA-256 persistent disk cache
│   │   └── pricing.py          # Real ($0) vs equivalent reference cost
│   │
│   ├── confidence/
│   │   ├── token_prob.py       # S1: Numerically stable log-prob softmax
│   │   ├── consistency.py      # S2: Self-consistency majority agreement
│   │   ├── self_rating.py      # S3: Robust 0-100 certainty regex parser
│   │   └── combiner.py         # Dynamic weight redistribution & combiner
│   │
│   ├── routing/
│   │   ├── risk_rules.py       # Regex detector for dosage, overdose, cardiac
│   │   └── router.py           # Threshold router, Tier 2 escalation & safe fallback
│   │
│   ├── db/
│   │   ├── schema.sql          # 6 SQLite tables with foreign keys & indices
│   │   └── database.py         # Thread-safe database transactions & reviewer helpers
│   │
│   └── api/
│       ├── __init__.py
│       └── main.py             # FastAPI backend (/ask, /queue, /review, /result, /stats)
│
├── app/
│   ├── Home.py                 # Streamlit web demo with traffic light meter
│   └── pages/
│       └── 1_Reviewer_Queue.py # Human-in-the-loop clinician review interface
│
├── scripts/
│   ├── init_db.py              # CLI database table initialization
│   └── run_demo.py             # 20-question pipeline test & summary stats
│
└── tests/
    ├── test_data.py            # Dataset validation & answer indexing tests
    ├── test_llm.py             # Mock LLM, caching & pricing tests
    ├── test_confidence.py      # S1, S2, S3 & combiner redistribution tests
    ├── test_routing.py         # Risk detection & threshold boundary tests
    ├── test_db.py              # SQLite schema & transaction tests
    ├── test_providers.py       # Ollama & Groq provider tests (mocked HTTP)
    ├── test_tier2_routing.py   # Tier 2 escalation, acceptance, and fallback tests
    ├── test_reviewer.py        # Clinician review workflow & database status tests
    └── test_api.py             # FastAPI REST endpoints integration tests
```

---

## 🚀 Quickstart Guide (Windows PowerShell)

Follow these exact steps from PowerShell:

### 1. Open the Repository & Activate Virtual Environment
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute

# Activate venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies & Local Package
```powershell
pip install -r requirements.txt
pip install -e .
```

### 3. Run the Automated Test Suite (41 Tests)
```powershell
pytest -v
```
*All 41 unit & integration tests run offline without external API keys or GPU dependencies.*

### 4. Start the FastAPI Backend Service
In terminal 1:
```powershell
uvicorn confiroute.api.main:app --port 8000 --reload
```
- Interactive API Documentation (Swagger UI): `http://localhost:8000/docs`
- Key Endpoints:
  - `POST /ask`: Submit medical query for routing
  - `GET /queue`: Retrieve pending cases for clinician review
  - `POST /review/{query_id}`: Clinician approves, edits, or rejects draft
  - `GET /result/{query_id}`: Check released final answer
  - `GET /stats`: Real-time system analytics

### 5. Launch the Streamlit Web Application
In terminal 2:
```powershell
streamlit run app/Home.py
```
- Main Demo: `http://localhost:8501` (includes deterministic test presets, traffic light status badges, query history).
- Reviewer Queue Page: Available from the sidebar under **1_Reviewer_Queue** (`http://localhost:8501/Reviewer_Queue`).

---

## 🤖 Real AI Model Integration Setup

### Tier 1 (Local Ollama):
For a laptop with 8 GB RAM (~3 GB free), the recommended model is in the 1B–1.5B class:
- **Recommended Model:** `llama3.2:1b` (Download: ~1.3 GB, RAM required: ~1.8 GB).
- **Alternative:** `qwen2.5:1.5b` (Download: ~1.0 GB, RAM required: ~1.5 GB).
- **Setup:**
  1. Install Ollama from [ollama.com](https://ollama.com).
  2. Pull the lightweight model:
     ```powershell
     ollama pull llama3.2:1b
     ```
  3. Ensure Ollama is running (`http://localhost:11434`). ConfiRoute connects automatically.

### Tier 2 (Groq Free Tier):
- Create a free account at [console.groq.com](https://console.groq.com) (₹0 budget, no credit card required).
- Create `.env` file from template:
  ```powershell
  copy .env.example .env
  ```
- Add your key: `GROQ_API_KEY=gsk_...`
- ConfiRoute uses `llama-3.3-70b-versatile` on Groq with automatic exponential backoff for rate limits.

---

## 🔗 GitHub Synchronization Instructions

To connect and push your local repository to GitHub:
```powershell
# 1. Add your remote repository URL (replace with your repo URL)
git remote add origin https://github.com/<your-username>/confiroute.git

# 2. Verify remote is set
git remote -v

# 3. Push main branch
git push -u origin main
```
*Note: Secrets (.env), virtual environment (.venv), local cache (.cache), raw datasets (data/raw), and database files (*.db) are strictly excluded by .gitignore.*
