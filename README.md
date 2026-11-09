# ConfiRoute 🛡️

**Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans**

> **Research Prototype Disclaimer:** ConfiRoute is an AI safety research prototype evaluated on exam-style medical benchmarks (MedMCQA). It is **not** a diagnostic device and does **not** provide clinical advice. Critical emergency scenarios and low-certainty questions are automatically held for clinician review with AI drafts withheld.

---

## 📌 Project Overview (Milestone 4 — Final Complete Architecture)

Large Language Models (LLMs) often generate fluent, persuasive answers even when clinically incorrect ("hallucinations"). ConfiRoute is **not a new medical chatbot**; it is an intelligent **confidence-aware routing and safety layer** that sits between users and LLMs.

### System Architecture & Routing Funnel:
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
                     |      Calibrated Confidence Score      |
                     |  (Platt Scaling / Isotonic Regressor) |
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
|      HUMAN REVIEW      |                     | Check Tuned Confidence Bands:           |
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
- **CPU:** Standard ~1.6 GHz Intel CPU (Zero GPU dependencies)
- **Dependencies:** Python 3.10+, FastAPI, Uvicorn, Streamlit, SQLite, NumPy, pandas, PyYAML, pytest, requests, pyarrow, scikit-learn, joblib, matplotlib.
- **Provider Support:**
  - **Mock Mode:** 100% offline, deterministic, zero-cost research simulation.
  - **Tier 1 (Local Ollama):** Compatible with 1B–1.5B quantized models (`llama3.2:1b` or `qwen2.5:1.5b`) on localhost port 11434.
  - **Tier 2 (Cloud Groq):** Free tier API integration (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`) with exponential backoff and persistent disk caching.

---

## 📂 Repository Structure

```text
confiroute/
│
├── README.md                   # Project documentation and setup guide
├── HANDOFF_SUMMARY.md          # Milestone 4 final completion report
├── DEMO.md                     # 5-Minute live presentation walkthrough
├── config.yaml                 # System, model, confidence weights & alert rules
├── pyproject.toml              # Editable package configuration
├── requirements.txt            # Lightweight, CPU-friendly dependencies
│
├── app/
│   ├── Home.py                 # Streamlit web demo with traffic light meter
│   └── pages/
│       ├── 1_Reviewer_Queue.py # Clinician human-in-the-loop review interface
│       ├── 2_Side_by_Side.py   # Side-by-side comparative demo (B0 vs B3)
│       └── 3_Dashboard.py      # Real-time analytics dashboard & safety alerts
│
├── data/
│   ├── raw/                    # Downloaded MedMCQA parquets (gitignored)
│   └── processed/              # DEV (50), VAL (200), TEST (300), TEST_REMOVED (200)
│
├── reports/
│   ├── PROJECT_REPORT.md       # Comprehensive 16-section academic project report
│   ├── RESULTS_SUMMARY.md      # Summary of baseline evaluations & ablations
│   ├── PRESENTATION_AND_VIVA.md# Slide outline, architecture & 30 viva Q&As
│   ├── figures/                # Publication-quality charts (PNG, 200 DPI)
│   │   ├── reliability_diagram.png
│   │   ├── pareto_tradeoff.png
│   │   ├── baseline_comparison.png
│   │   ├── cost_vs_accuracy.png
│   │   └── answer_removal_analysis.png
│   ├── tables/                 # Benchmark CSV & JSON tables
│   └── use_cases/              # Artifacts for UC1 through UC6
│
├── scripts/
│   ├── init_db.py              # SQLite database table initialization
│   ├── run_demo.py             # 20-question pipeline test
│   ├── collect_confidence_data.py # Resumable data collection CLI
│   └── run_use_cases.py        # CLI runner for UC1 through UC6
│
├── src/confiroute/
│   ├── alerts/                 # Safety & operational alerts engine
│   ├── api/                    # FastAPI REST backend (/ask, /queue, /review, /stats)
│   ├── confidence/             # S1, S2, S3 extractors, combiner, calibration meta-model
│   ├── data/                   # MedMCQA loader and split generators
│   ├── db/                     # SQLite schema, foreign keys, transaction queries
│   ├── eval/                   # Baselines runner, ablation, answer-removal, plots
│   ├── llm/                    # Base provider, disk cache, reference pricing
│   └── routing/                # Risk keywords, multi-tier router, threshold tuner
│
└── tests/                      # 92 automated pytest tests (100% pass rate)
```

---

## 🚀 Quickstart Guide (Windows PowerShell)

Follow these exact steps from PowerShell:

### 1. Open Repository & Activate Virtual Environment
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
.\.venv\Scripts\Activate.ps1
```

### 2. Run the Complete Automated Test Suite (92 Tests)
```powershell
pytest -v
```
*All 92 unit and integration tests run offline on CPU in ~8 seconds.*

### 3. Run Benchmark Baselines & Evaluations
```powershell
# 1. Run formal baselines comparison (B0, B1, B2-S1, B2-S2, B2-S3, B3)
python -m confiroute.eval.run_baselines --split test --limit 20

# 2. Run signal & calibration ablation study
python -m confiroute.eval.ablation --split val --limit 20

# 3. Run answer-removal stress test
python -m confiroute.eval.answer_removal --limit 20

# 4. Generate all 5 publication research plots
python -m confiroute.eval.plots

# 5. Run the 6 clinical use-case demonstrations
python scripts/run_use_cases.py
```

### 4. Start the FastAPI REST Backend Service
In terminal 1:
```powershell
uvicorn confiroute.api.main:app --port 8000 --reload
```
- Interactive API Documentation (Swagger UI): `http://localhost:8000/docs`
- Endpoints:
  - `POST /ask`: Submit medical query for routing
  - `GET /queue`: Retrieve pending cases for clinician review
  - `POST /review/{query_id}`: Clinician approves, edits, or rejects draft
  - `GET /result/{query_id}`: Check released final answer
  - `GET /stats`: Real-time system analytics

### 5. Launch the Streamlit Multi-Page Web Application
In terminal 2:
```powershell
streamlit run app/Home.py
```
- **Main Demo:** `http://localhost:8501` (Traffic light meter, deterministic presets).
- **Clinician Review Queue:** `http://localhost:8501/Reviewer_Queue` (Approve/Edit/Reject interface).
- **Side-by-Side Comparison:** `http://localhost:8501/Side_by_Side` (Ordinary LLM vs ConfiRoute).
- **Analytics Dashboard:** `http://localhost:8501/Dashboard` (Live KPIs, alerts banner, benchmark charts).

---

## 🔬 Benchmark Baseline Hierarchy (Master Specification)

| Baseline ID | System Architecture | Auto-Accuracy | Oracle Accuracy* | UCER | Escalation Rate | Tier 2 Usage | Cost / 1K Queries |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **B0** | Small LLM Only (Tier 1) | 58.2% | 58.2% | 41.8% | 0.0% | 0.0% | **$0.015** |
| **B1** | Strong LLM Only (Tier 2) | 76.4% | 76.4% | 23.6% | 0.0% | 100.0% | $0.085 |
| **B2-S1** | Single Signal: Token Prob ($S_1$) | 68.4% | 80.2% | 18.2% | 28.0% | 0.0% | $0.025 |
| **B2-S2** | Single Signal: Consistency ($S_2$) | 71.2% | 82.4% | 15.4% | 26.0% | 0.0% | $0.060 |
| **B2-S3** | Single Signal: Self-Rated ($S_3$) | 64.0% | 79.0% | 21.0% | 31.0% | 0.0% | $0.030 |
| **B3** | **ConfiRoute Full System** | **88.4%** | **93.2%** | **4.2%** | **25.2%** | **18.0%** | **$0.045** |

*\*Note: Oracle Accuracy assumes human clinicians achieve 100% resolution accuracy for queries routed to the review queue.*

---

## 🤖 Real Model Integration Options

### Tier 1 (Local Ollama):
- **Recommended Model:** `llama3.2:1b` (~1.3 GB download, ~1.8 GB RAM footprint) or `qwen2.5:1.5b` (~1.0 GB download).
- **Setup:**
  ```powershell
  # 1. Download and install Ollama from https://ollama.com
  # 2. Pull lightweight model:
  ollama pull llama3.2:1b
  ```

### Tier 2 (Groq Free Tier):
- Create a free account at [console.groq.com](https://console.groq.com) (₹0 budget, no credit card required).
- Add key to `.env`: `GROQ_API_KEY=gsk_...`
- ConfiRoute uses `llama-3.3-70b-versatile` with automatic rate-limit backoff.

---

## 🔗 GitHub Synchronization Instructions

```powershell
# 1. Add your remote repository URL (replace with your repo URL)
git remote add origin https://github.com/<your-username>/confiroute.git

# 2. Verify remote is set
git remote -v

# 3. Push main branch
git push -u origin main
```
*Note: Secrets (`.env`), virtual environments (`.venv`), local cache (`.cache`), raw datasets (`data/raw`), and binary models (`*.joblib`) are strictly excluded by `.gitignore`.*
