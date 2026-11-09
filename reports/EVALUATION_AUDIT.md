# ConfiRoute — Evaluation Integrity & Experimental Evidence Audit

**Audit Date:** November 10, 2026  
**Auditor:** Senior AI/ML Engineer & Systems Architect (Google Antigravity)  
**Target Repository:** `c:\Users\akash\Desktop\confiroute-miniproject\confiroute`  
**Git Baseline Commit:** `b74f63c`  
**Automated Test Suite Status:** **92 / 92 Passed** (100% pass rate in 7.08s)  
**Primary Finding:** **The codebase is 100% engineering-complete, but 0.0% of reported benchmark statistics represent genuine AI model inference. All reported metrics are synthetic demonstration projections.**

---

## 1. Executive Summary & Audit Mandate

An independent forensic audit was conducted on all empirical claims, benchmark tables, ablation statistics, answer-removal results, and underlying storage artifacts in ConfiRoute.

The audit verified two distinct layers of the project:
1. **Engineering Layer (VERIFIED COMPLETE):** All routing engines, multi-signal extractors ($S_1, S_2, S_3$), Platt scaling, isotonic regression, threshold grid search, SQLite persistence, FastAPI endpoints, Streamlit dashboard, alert rules, and 92 automated pytest tests are fully functional, verified, and passing without regressions.
2. **Experimental Evaluation Layer (UNSUPPORTED / PENDING REAL INFERENCE):** Every quantitative percentage reported in `PROJECT_REPORT.md` and `RESULTS_SUMMARY.md` (e.g., 58.2% B0 accuracy, 88.4% B3 accuracy, 4.2% UCER, 0.064 ECE) is **unsupported by real model evidence**. They are simulated demonstration projections derived from hardcoded dictionaries in `plots.py` and `3_Dashboard.py`, rather than measured tallies of 300 test questions evaluated on genuine LLMs.

---

## 2. Forensic Item-by-Item Reconciliation

### A. Baseline Comparison Table (Reported: $N=300$ TEST Questions)
- **Claimed in `PROJECT_REPORT.md` (Section 11) & `RESULTS_SUMMARY.md` (Section 1):**
  - B0 Auto-Accuracy: 58.2%, UCER: 41.8%, ECE: 0.284
  - B1 Auto-Accuracy: 76.4%, UCER: 23.6%, ECE: 0.196
  - B2-S1 Auto-Accuracy: 68.4%, UCER: 18.2%, ECE: 0.210
  - B2-S2 Auto-Accuracy: 71.2%, UCER: 15.4%, ECE: 0.175
  - B2-S3 Auto-Accuracy: 64.0%, UCER: 21.0%, ECE: 0.242
  - B3 ConfiRoute Auto-Accuracy: 88.4%, UCER: 4.2%, ECE: 0.064
- **Actual Evidence on Disk (`reports/tables/baseline_comparison.csv`):**
  - **Sample count:** Exactly **3 questions** (`total_queries: 3`), evaluated on `dev.jsonl` using `provider="mock"`.
  - **Actual values on disk:** `auto_accuracy: 0.0`, `ucer: 1.0` (for B0/B1), `ucer: 0.3333` (for B3), `human_escalation_rate: 0.6667`.
- **Mathematical Impossibility:**
  - In a discrete sample of $N=300$ questions, accuracy must be an integer fraction $k / 300$, yielding steps of $0.333\%$ ($1/300 \approx 0.003333$).
  - Reported $58.2\%$ would require $174.6$ correct questions.
  - Reported $88.4\%$ would require $265.2$ correct questions.
  - Reported $4.2\%$ UCER would require $12.6$ incorrect questions.
  - **Verdict:** The reported values are synthetic decimals invented as illustrative target placeholders, not raw experimental counts.

---

### B. Signal & Calibration Ablation Study (Reported: $N=200$ VAL Questions)
- **Claimed in `RESULTS_SUMMARY.md` (Section 2):**
  - $S_1$ AUROC: 0.732, ECE: 0.210
  - $S_2$ AUROC: 0.768, ECE: 0.175
  - $S_3$ AUROC: 0.694, ECE: 0.242
  - Platt Scaling AUROC: 0.842, ECE: 0.078
  - Isotonic Regression AUROC: 0.846, ECE: 0.064
- **Actual Evidence on Disk (`reports/tables/ablation_results.csv`):**
  - **Sample count:** Exactly **3 questions** (`total_queries: 3`), evaluated using `MockProvider`.
  - **Actual values on disk:** Every signal combination has `auroc: 0.5000` (chance level due to degenerate 3-sample size), `ece_10_bin: 0.5663` to `0.7500`, and `ucer: 0.3333` to `0.6667`.
- **Verdict:** The reported ablation table in `RESULTS_SUMMARY.md` is synthetic.

---

### C. Answer-Removal Refusal Stress Test (Reported: $N=200$ `TEST_REMOVED` Questions)
- **Claimed in `PROJECT_REPORT.md` (Section 12) & `RESULTS_SUMMARY.md` (Section 3):**
  - Unrouted LLM Guess Rate: 94.5% ($189/200$)
  - Unrouted LLM UCER: 94.5%
  - ConfiRoute Escalation Rate: 88.0% ($176/200$)
  - ConfiRoute UCER: 4.0% ($8/200$)
  - UCER Safety Reduction: 95.8%
- **Actual Evidence on Disk (`reports/tables/answer_removal_results.csv`):**
  - **Sample count:** Exactly **3 questions** (`total_queries: 3`), evaluated using `MockProvider`.
  - **Actual values on disk:** `unrouted_guesses_count: 3` ($100\%$), `routed_human_escalation_count: 3` ($100\%$), `routed_ucer: 0.0`, `ucer_reduction_percent: 100.0%`.
- **Verdict:** The 200-question answer-removal experiment has never been run on real models or the full 200-item split. The reported 94.5% and 88.0% numbers are synthetic demonstration placeholders.

---

### D. LLM Disk Cache Audit (`.cache/llm_cache/`)
- **Total Cache Entries:** **291 files**
- **Audit Script Command:**
  ```python
  import json
  from pathlib import Path
  files = list(Path('.cache/llm_cache').glob('*.json'))
  mock_count = sum(1 for f in files if json.loads(f.read_text()).get('is_mock'))
  # Result: mock_count = 291 / 291 (100.0%)
  ```
- **Real Model Inferences Cached:** **0 entries (0.0%)**
- **Verdict:** Not a single genuine request to Ollama, Groq, or any external neural network exists in the cache.

---

### E. SQLite Database Audit (`data/confiroute.db`)
- **Total Queries Logged:** 53 rows
- **Total Signals Logged:** 53 rows
- **Total Routes Logged:** 53 rows
- **Total Reviews Logged:** 11 rows
- **Total Real Cost Recorded:** Exactly **$0.00** across all 53 records (`WHERE real_cost > 0` returns 0).
- **Verdict:** All database queries were generated by the 20-question mock demo script (`scripts/run_demo.py`) and UI testing clicks.

---

## 3. Root Cause Analysis

Where did the reported numbers come from?
1. In `src/confiroute/eval/plots.py` (lines 118–127), default fallback tables were written as synthetic illustrative projections so that `plot_baseline_comparison()` and `plot_cost_vs_accuracy()` would render representative visual plots when `baseline_comparison.csv` was absent.
2. In `app/pages/3_Dashboard.py` (lines 169–178), the identical fallback table was embedded so the dashboard would render sample charts before benchmarks were executed.
3. During Milestone 4 documentation writing, these illustrative fallback values were inadvertently transferred into `PROJECT_REPORT.md` and `RESULTS_SUMMARY.md` as if they were final empirical results from a 300-question test split run.
4. ConfiRoute's test-batch safety guard (which blocks runs $> 20$ questions unless `--confirm` is passed) correctly prevented unauthorized large batch runs on the host laptop, leaving only 3-sample test CSVs on disk.

---

## 4. Current Hardware & Infrastructure Blockers

| Component | Status | Blocker Description | Action Required |
|:---|:---:|:---|:---|
| **Tier 1 (Local Ollama)** | ❌ NOT INSTALLED | `Get-Command ollama` fails. Port 11434 is closed. No local model weights exist on disk. | User must install Ollama and download a lightweight model (`llama3.2:1b` or `qwen2.5:1.5b`). |
| **Tier 2 (Cloud Groq)** | ❌ KEY MISSING | No `.env` file exists in `confiroute/`. `GROQ_API_KEY` is not configured. | User must provide a free Groq API key in `.env`. |
| **MedMCQA Splits** | ✅ READY | `data/processed/` contains `dev.jsonl` (50), `val.jsonl` (200), `test.jsonl` (300), and `test_removed.jsonl` (200). | Ready for batch evaluation. |
| **Evaluation Pipelines** | ✅ READY | `run_baselines.py`, `ablation.py`, `answer_removal.py`, and `plots.py` are fully functional and resumable. | Ready to run once providers are live. |

---

## 5. Corrective Action: Relabeling All Reports

To preserve scientific integrity:
1. `reports/RESULTS_SUMMARY.md` has been updated to explicitly label all baseline tables as **[SIMULATED TARGET PROJECTION / DEMO PLACEHOLDER]**.
2. `reports/PROJECT_REPORT.md` has been updated with a prominent **Scientific Integrity Notice** stating that empirical claims reflect simulated architectural baselines, with real model evaluations marked as `[TBD: PENDING REAL MODEL RUN]`.
3. `app/pages/3_Dashboard.py` has been updated to clearly watermark demonstration tables as `[SIMULATED BENCHMARK PROJECTIONS]`.

---

## 6. Actionable Real-Model Testing Plan

To advance ConfiRoute from engineering-complete to genuine empirical research completion, execute the following phased plan.

### Phase 1: Environment Setup & Single-Query Smoke Tests
Do NOT run large batches. First prove that single-query inference succeeds.

#### A. Ollama (Tier 1 Local CPU Inference)
1. Download Ollama for Windows from [ollama.com](https://ollama.com).
2. Install and launch Ollama.
3. Pull the lightweight 1B model (Download: ~1.3 GB, RAM footprint: ~1.8 GB, fits safely inside 3 GB available memory):
   ```powershell
   ollama pull llama3.2:1b
   ```
4. Verify port 11434 is active:
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 11434
   ```
5. Test a single genuine inference query:
   ```powershell
   cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
   .\.venv\Scripts\python -c "
   from confiroute.llm.base import ask_llm
   resp = ask_llm(model_key='tier1', prompt='Answer with option letter: What is the cause of scurvy? A: Vitamin C deficiency, B: Iron deficiency', provider='ollama')
   print(f'Text: {resp.text}, Model: {resp.model}, Latency: {resp.latency_ms:.1f}ms, is_mock: {resp.is_mock}')
   "
   ```
   *Expected output: `is_mock: False`, actual model name `llama3.2:1b`, latency > 0.*

#### B. Groq (Tier 2 Cloud Inference — ₹0 Budget)
1. Sign up for a free Groq account at [console.groq.com](https://console.groq.com) (no credit card required).
2. Generate a free API key.
3. Create `.env` file in `confiroute/`:
   ```powershell
   copy .env.example .env
   ```
4. Add your API key into `.env`:
   ```text
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
5. Test a single genuine Groq Tier 2 inference query:
   ```powershell
   .\.venv\Scripts\python -c "
   from confiroute.llm.base import ask_llm
   resp = ask_llm(model_key='tier2', prompt='Answer with single letter: What cell produces insulin? A: Beta cells, B: Alpha cells', provider='groq')
   print(f'Text: {resp.text}, Model: {resp.model}, Latency: {resp.latency_ms:.1f}ms, is_mock: {resp.is_mock}')
   "
   ```
   *Expected output: `is_mock: False`, actual model `llama-3.3-70b-versatile`, latency ~300-800ms.*

---

### Phase 2: Small Real-Model Validation Batch ($N = 10$ Questions)
*Requires explicit user approval before execution.*
- Evaluate 10 questions from `dev.jsonl` using genuine Ollama and Groq inference:
  ```powershell
  python scripts/collect_confidence_data.py --split dev --provider ollama --limit 10
  ```
- Inspect latency, memory usage, and token consumption to verify the laptop remains stable and responsive.

---

### Phase 3: Full Benchmark Execution (Resumable)
Once Phase 2 confirms stability:
1. **VAL Split ($N=200$):** Run evaluation on validation set, fit Platt scaling and Isotonic regression calibrators, and optimize thresholds $(\tau_{\text{low}}, \tau_{\text{high}})$. Freeze thresholds.
2. **TEST Split ($N=300$):** Run blind evaluation across B0, B1, B2-S1, B2-S2, B2-S3, and B3 using frozen thresholds.
3. **TEST_REMOVED Split ($N=200$):** Run answer-removal experiment to measure true model hallucination and refusal rates.
4. **Generate Figures & Final Reports:** Re-run `python -m confiroute.eval.plots` to generate publication charts from genuine CSV outputs.

---

## 7. Audit Conclusion
ConfiRoute's codebase is structurally sound, mathematically verified, and fully tested (92/92 tests passing). However, in accordance with the highest standards of scientific and academic integrity, **no research claims will be treated as final until genuine model inference is executed and backed by verifiable per-question records.**
