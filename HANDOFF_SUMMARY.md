# HANDOFF SUMMARY — CONFIROUTE MILESTONE 3 (~70%)

## 1. Milestone Status & Overview
- **Project:** ConfiRoute — Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans.
- **Milestone Scope:** Milestone 3 (~70% development scope completed).
- **Previous Milestone:** Milestone 2 (~50% completed, 41 passing tests).
- **Current Test Suite:** **65 passing automated tests** (0 failures, 100% pass rate).
- **Git Branch:** `main`. Local commit hash to be updated.
- **Budget Expended:** ₹0.00 (Zero paid cloud services, lightweight CPU-compatible dependencies).

---

## 2. Technical Deliverables Completed in Milestone 3

### A. Live Provider & Hardware Assessment (Task 1 & Task 2)
1. **Ollama Status:**
   - Evaluated on Windows host: Ollama is currently **not installed / not running on port 11434**.
   - Hardware analysis for Intel CPU, 8 GB RAM (~3 GB free):
     - **Recommendation 1:** `llama3.2:1b` (1.3 GB download, ~1.8 GB RAM footprint).
     - **Recommendation 2:** `qwen2.5:1.5b` (1.0 GB download, ~1.5 GB RAM footprint).
     - **Safety constraint respected:** No model downloaded without developer authorization.
2. **Groq Status:**
   - `.env.example` verified; free-tier models supported: `llama-3.3-70b-versatile` and `llama-3.1-8b-instant`.
   - Exponential backoff with jitter and disk caching intact.
3. **Offline / Mock Mode:** Completely deterministic, instant, and preserves ₹0 development workflow.

### B. Resumable Confidence Data Collector (Task 3)
- **Module:** [`scripts/collect_confidence_data.py`](file:///C:/Users/akash/Desktop/confiroute-miniproject/confiroute/scripts/collect_confidence_data.py)
- **Features:**
  - Evaluates MedMCQA splits (`dev`, `val`, `test`, `test_removed`).
  - Supports `--provider mock|ollama|groq` and `--limit N`.
  - Resumable: skips already evaluated question IDs on disk.
  - Per-row flush to CSV: ensures progress is never lost if interrupted.
  - Strict safety guard: runs with $N > 20$ require explicit `--confirm` flag to prevent accidental quota exhaustion or CPU lockup.
  - Clearly logs `is_mock=True/False` to prevent confusing mock data with experimental results.

### C. Confidence Calibration Meta-Model (Task 4)
- **Module:** [`src/confiroute/confidence/calibration.py`](file:///C:/Users/akash/Desktop/confiroute-miniproject/confiroute/src/confiroute/confidence/calibration.py)
- **Features:**
  - `ConfidenceCalibrator` supporting `method="platt"`, `method="isotonic"`, and `method="weighted_average"`.
  - Platt scaling fits a Logistic Regression meta-model mapping $[S_1, S_2, S_3]$ to empirical probability of correctness.
  - Isotonic Regression calibrates monotonic empirical accuracy against composite weighted confidence.
  - Dynamic missing signal imputation: imputes missing signals (e.g. when S1 token logprobs are unavailable) with neutral 0.50 without crashing.
  - K-Fold cross-fitting (`cross_fit_predict`) to evaluate validation split without data leakage.
  - Serialization and deserialization via `joblib.dump` / `joblib.load`.
  - Synthetic validation feature generation helper for automated testing.

### D. Comprehensive Evaluation Benchmark Metrics (Task 5)
- **Module:** [`src/confiroute/eval/metrics.py`](file:///C:/Users/akash/Desktop/confiroute-miniproject/confiroute/src/confiroute/eval/metrics.py)
- **Metrics Implemented:**
  1. `compute_auto_accuracy`: Accuracy strictly among direct/auto answers.
  2. `compute_ucer`: Unsafe Confident Error Rate $= \frac{\text{auto} \land \text{wrong}}{\text{total queries}}$.
  3. `compute_ucer_high`: UCER strictly among high-confidence auto-released answers ($\ge 0.80$).
  4. `compute_ece`: Expected Calibration Error over 10 equal-width bins with boundary handling.
  5. `compute_escalation_rate`: Fraction of queries held for Tier 2 escalation or human clinician review.
  6. `compute_auroc`: ROC-AUC distinguishing correct from incorrect answers.
  7. `compute_all_metrics`: Unified aggregator returning counts, accuracy, UCER, ECE, AUROC, mean latency (ms), and equivalent cost ($).

### E. Threshold Grid Search & Pareto Optimization (Task 6)
- **Module:** [`src/confiroute/routing/thresholds.py`](file:///C:/Users/akash/Desktop/confiroute-miniproject/confiroute/src/confiroute/routing/thresholds.py)
- **Features:**
  - `simulate_routing_for_thresholds`: Evaluates routing decisions across candidates under risk overrides.
  - `grid_search_thresholds`: Performs grid search over $(\tau_{\text{low}}, \tau_{\text{high}})$ pairs where $\tau_{\text{high}} > \tau_{\text{low}}$.
  - Multi-objective tuning:
    - `"min_ucer"` subject to maximum clinician escalation rate ($\le 40\%$).
    - `"max_utility"` optimizing $\text{Accuracy} - \lambda \cdot \text{Escalation Rate}$.
  - Strict scientific partition: tuning restricted strictly to VALIDATION split to prevent TEST leakage.
  - `save_thresholds`: Persists chosen thresholds and metadata to JSON.

### F. Side-by-Side Comparative Demonstration (Task 7 & Task 8)
- **Streamlit Page:** [`app/pages/2_Side_by_Side.py`](file:///C:/Users/akash/Desktop/confiroute-miniproject/confiroute/app/pages/2_Side_by_Side.py)
- **Features:**
  - Directly demonstrates contrast between raw unrouted LLM (Baseline B0) and ConfiRoute (System B3).
  - 4 Preset clinical scenarios:
    1. *High-Confidence Factual Query:* Both answer correctly; ConfiRoute confirms certainty $\ge 0.80$ and safely releases.
    2. *Ambiguous / Hallucination-Prone Question:* Unrouted LLM answers blindly with zero caveats; ConfiRoute measures low confidence ($< 0.50$) and escalates.
    3. *Answer-Removal Setting:* Correct option removed; unrouted LLM hallucinates; ConfiRoute detects uncertainty.
    4. *High-Risk Emergency Dosage:* Contains pediatric / emergency dosage keywords; ConfiRoute overrides score and halts release for human review.
  - Interactive custom question editor with side-by-side comparative cards and color-coded status badges.
- **Homepage Improvements:** Updated [`app/Home.py`](file:///C:/Users/akash/Desktop/confiroute-miniproject/confiroute/app/Home.py) with navigation pills to Reviewer Queue and Side-by-Side page, plus active threshold and calibration indicators in the sidebar.

### G. Expanded Automated Test Suite (Task 9)
- **New Test Modules:**
  - `tests/test_calibration.py`: 9 unit tests (Platt scaling, isotonic regression, imputation, cross-fitting, joblib save/load, error handling).
  - `tests/test_metrics.py`: 7 unit tests (Hand-calculated cases for auto-accuracy, UCER, UCER_high, 10-bin ECE, escalation rate, AUROC, unified metrics).
  - `tests/test_thresholds.py`: 4 unit tests (routing simulation, min_ucer search, max_utility search, JSON persistence).
  - `tests/test_side_by_side.py`: 4 unit tests (preset scenario structure, unrouted vs routed behavior across confidence levels and emergency overrides).
- **Total Test Count:** **65 tests passed in 3.07 seconds**.

---

## 3. Directory Structure After Milestone 3

```text
confiroute/
├── app/
│   ├── Home.py                       # Enhanced homepage with calibration sidebar & quick nav
│   └── pages/
│       ├── 1_Reviewer_Queue.py       # Clinician human review interface
│       └── 2_Side_by_Side.py         # Side-by-side comparative demo (B0 vs B3)
├── reports/
│   └── tables/
│       └── mock_dev_confidence.csv   # Verified confidence evaluation logs
├── scripts/
│   ├── init_db.py                    # SQLite database initializer
│   ├── run_demo.py                   # 20-question pipeline runner
│   └── collect_confidence_data.py    # Resumable evaluation data collector
├── src/confiroute/
│   ├── api/                          # FastAPI REST endpoints (/ask, /queue, /review, /stats)
│   ├── confidence/
│   │   ├── calibration.py            # Platt scaling, isotonic regression, joblib persistence
│   │   ├── combiner.py               # Dynamic signal redistribution combiner
│   │   ├── consistency.py            # S2: Self-consistency agreement
│   │   ├── self_rating.py            # S3: Self-rated certainty extractor
│   │   └── token_prob.py             # S1: Numerically stable softmax
│   ├── data/                         # MedMCQA loader and dataset split generators
│   ├── db/                           # SQLite transactions, schema, and review helpers
│   ├── eval/
│   │   └── metrics.py                # Auto-accuracy, UCER, UCER_high, 10-bin ECE, AUROC
│   ├── llm/                          # Unified LLM provider interface, disk cache, pricing
│   └── routing/
│       ├── risk_rules.py             # Clinical keyword risk screening
│       ├── router.py                 # Multi-tier routing engine
│       └── thresholds.py             # Validation-split grid search threshold tuner
└── tests/                            # 65 automated pytest tests
```

---

## 4. Verification & Command Checklist

To verify the Milestone 3 implementation from PowerShell:

```powershell
# 1. Activate environment
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
.\.venv\Scripts\Activate.ps1

# 2. Run the complete 65-test suite
pytest -v

# 3. Test confidence data collection (mock mode, 3 samples)
python scripts/collect_confidence_data.py --split dev --provider mock --limit 3

# 4. Start FastAPI service
uvicorn confiroute.api.main:app --port 8000 --reload

# 5. Launch Streamlit UI
streamlit run app/Home.py
```

---

## 5. Scope for Next Milestone (Milestone 4 — ~70% to 100%)
1. **Full Benchmark Experimentation:** Run evaluation on complete VAL (200) and TEST (300) splits, computing official comparison table between B0 (unrouted Tier 1), B1 (Tier 1 + S1 only), B2 (Tier 1 + composite confidence), and B3 (ConfiRoute multi-tier + safety layer).
2. **Answer-Removal Setting Analysis:** Evaluate hallucination rate on `TEST_REMOVED` (200) split to demonstrate refusal and human escalation behavior.
3. **Report Generation & Visualizations:** Generate publication-ready figures (Reliability diagram calibration curves, Pareto trade-off curves, routing decision Sankey diagrams, cost vs accuracy curves).
4. **Final Packaging & Export:** Complete documentation, reproducible execution scripts, and final submission archive.
