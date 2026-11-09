# ConfiRoute 🛡️

**Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans**

> **Research Prototype Disclaimer:** ConfiRoute is an AI safety research prototype evaluated on exam-style medical benchmarks (MedMCQA). It is **not** a diagnostic device and does **not** provide clinical advice. Critical emergency scenarios and low-certainty questions are held for clinician review.

---

## 📌 Project Concept

Large Language Models (LLMs) often generate fluent, persuasive answers even when clinically incorrect ("hallucinations"). ConfiRoute is **not a new medical chatbot**; it is an intelligent **routing and safety layer** that sits between users and LLMs.

### System Flow:
```text
                     +---------------------------------------+
                     |          User Medical Query           |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |          Tier 1 (Small LLM)           |
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
+------------------------+                     | • Score < 0.50 -> HUMAN REVIEW (🔴)     |
                                               +-----------------------------------------+
```

---

## 💻 Hardware & Zero-Cost Constraints

ConfiRoute is designed to run efficiently on standard consumer hardware with **₹0 budget**:
- **Operating System:** Windows 10/11 (PowerShell)
- **RAM:** 8 GB (~3 GB free memory)
- **CPU:** Standard ~1.6 GHz Intel CPU (no GPU required)
- **Dependencies:** Python 3.10+, SQLite, Streamlit, NumPy, pandas, PyYAML, pytest.
- **Milestone 1 State:** Architecture uses a deterministic **Mock LLM engine** to simulate model outputs, log-probabilities, self-consistency sampling, and self-evaluations without large downloads or GPU dependencies.
- **Cost Policy:** Real cost is strictly **$0.00**; reference per-token pricing is tracked for cross-tier economic comparison.

---

## 📂 Repository Structure

```text
confiroute/
│
├── README.md                   # Project documentation and setup guide
├── HANDOFF_SUMMARY.md          # Milestone 1 handoff report
├── requirements.txt            # Lightweight, CPU-friendly dependencies
├── .env.example                # Template for future API keys
├── .gitignore                  # Git ignore rules for venv, caches, db, data/raw
├── config.yaml                 # System, model, confidence weights & risk rules
├── pyproject.toml              # Editable package configuration
│
├── data/
│   ├── raw/                    # Downloaded Hugging Face parquets (gitignored)
│   └── processed/              # DEV (50), VAL (200), TEST (300), TEST_REMOVED (200)
│
├── src/
│   └── confiroute/
│       ├── __init__.py         # Package root
│       ├── config.py           # Configuration loader
│       │
│       ├── data/
│       │   ├── medmcqa_loader.py   # Parquet loader & record validator
│       │   ├── make_splits.py      # Split generator (DEV 50, VAL 200, TEST 300)
│       │   └── make_removed.py     # Answer-removal test set generator (200)
│       │
│       ├── llm/
│       │   ├── base.py             # ask_llm() unified interface & LLMResponse
│       │   ├── mock_provider.py    # Deterministic mock engine with logprobs
│       │   ├── cache.py            # SHA-256 persistent disk cache
│       │   └── pricing.py          # Real ($0) vs equivalent reference cost
│       │
│       ├── confidence/
│       │   ├── token_prob.py       # S1: Numerically stable log-prob softmax
│       │   ├── consistency.py      # S2: Self-consistency majority agreement
│       │   ├── self_rating.py      # S3: Robust 0-100 certainty regex parser
│       │   └── combiner.py         # Dynamic weight redistribution & combiner
│       │
│       ├── routing/
│       │   ├── risk_rules.py       # Regex detector for dosage, overdose, cardiac
│       │   └── router.py           # Threshold router & RouteDecision dataclass
│       │
│       └── db/
│           ├── schema.sql          # 6 SQLite tables with foreign keys & indices
│           └── database.py         # Thread-safe database transactions & query logs
│
├── app/
│   └── Home.py                 # Streamlit web demo with traffic light meter
│
├── scripts/
│   ├── init_db.py              # CLI database table initialization
│   └── run_demo.py             # 20-question pipeline test & summary stats
│
├── tests/
│   ├── test_data.py            # Dataset validation & answer indexing tests
│   ├── test_llm.py             # Mock LLM, caching & pricing tests
│   ├── test_confidence.py     # S1, S2, S3 & combiner redistribution tests
│   ├── test_routing.py         # Risk detection & threshold boundary tests
│   └── test_db.py              # SQLite table creation & transaction tests
│
├── reports/
│   ├── figures/                # Visual charts for future phases
│   └── tables/                 # Evaluation metric tables
└── notebooks/                  # Interactive experimentation notebooks
```

---

## 🚀 Quickstart Guide (Windows PowerShell)

Follow these exact steps from PowerShell:

### 1. Clone or Open the Repository
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
```

### 2. Activate Virtual Environment
```powershell
# Create venv if not already created
python -m venv .venv

# Activate in PowerShell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
pip install -e .
```

### 4. Initialize the SQLite Database
```powershell
python scripts/init_db.py
```
*Creates `data/confiroute.db` with 6 tables: `queries`, `signals`, `routes`, `reviews`, `costs`, `alerts`.*

### 5. Build Dataset Splits
```powershell
python src/confiroute/data/make_splits.py
python src/confiroute/data/make_removed.py
```
*Generates genuine MedMCQA splits in `data/processed/`: `dev.jsonl` (50), `val.jsonl` (200), `test.jsonl` (300), and `test_removed.jsonl` (200).*

### 6. Run the Automated Test Suite
```powershell
pytest -v
```
*Executes all 20 unit tests across data, LLM caching, confidence signals, risk screening, and SQLite.*

### 7. Run the 20-Question Pipeline Demo
```powershell
python scripts/run_demo.py 20
```
*Processes 20 DEV questions, computes confidence signals, applies risk checks, logs decisions to SQLite, and prints distribution statistics.*

### 8. Launch the Streamlit Web Application
```powershell
streamlit run app/Home.py
```
*Opens `http://localhost:8501` featuring the interactive ConfiRoute interface, deterministic test presets, traffic light status badges, and recent query history.*

---

## 🔮 Future Phases & Real LLM Integration

When transitioning to real inference in subsequent phases:
1. **Tier 1 (Local Ollama):**
   - Download Ollama for Windows from [ollama.com](https://ollama.com).
   - Pull candidate small model: `ollama pull llama3.2:3b` or `ollama pull qwen2.5:3b`.
   - Call via local API (`http://localhost:11434/api/generate`) with `logprobs=True`.
2. **Tier 2 (Groq Free Tier):**
   - Create a free account at [console.groq.com](https://console.groq.com).
   - Add your free API key to `.env` as `GROQ_API_KEY=gsk_...`.
   - Uses OpenAI-compatible client for `gpt-oss-120b` or `llama-3.3-70b-versatile`.
3. **Fallback Plan:**
   - If CPU latency is too slow for Tier 1 locally, run Tier 1 on a free Kaggle / Colab GPU notebook using Hugging Face `transformers` to retrieve logprobs directly.
