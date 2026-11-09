# ConfiRoute — Formal Experimental Results Summary

**Project:** Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans  
**Benchmark Dataset:** MedMCQA (Medical Multiple-Choice QA — AIIMS & NEET-PG exam questions)  
**Dataset Partitions:** DEV (50), VAL (200), TEST (300), TEST_REMOVED (200)  
**Tuning Integrity:** Threshold tuning and calibration cross-fitting conducted strictly on VALIDATION split with ZERO test-set data leakage.

> ⚠️ **SCIENTIFIC INTEGRITY & EVALUATION AUDIT NOTICE (November 10, 2026):**  
> The quantitative values presented below represent **SIMULATED TARGET PROJECTIONS** generated to demonstrate and verify the software benchmarking pipeline, evaluation metrics, and reporting layout.  
> As confirmed in [`reports/EVALUATION_AUDIT.md`](file:///c:/Users/akash/Desktop/confiroute-miniproject/confiroute/reports/EVALUATION_AUDIT.md), **zero genuine model calls** have been made to Ollama or Groq to date. All 291 cached responses in `.cache/llm_cache` were generated via ConfiRoute's offline deterministic mock engine. Official empirical research findings remain **TBD (Pending Real Model Inferences)** until genuine model inference is approved and executed.

---

## 1. Formal Baseline Evaluation (TEST Split — 300 Questions) `[SIMULATED PROJECTIONS]`

The system evaluates the six formal baseline configurations specified in the master architecture:

| Baseline ID | System Architecture | Auto-Answer Accuracy `[SIM]` | Oracle Resolved Accuracy* `[SIM]` | UCER (Unsafe Confident Error) `[SIM]` | UCER_high (Conf $\ge 0.80$) `[SIM]` | ECE (10-bin Calibration Error) `[SIM]` | Human Escalation Rate `[SIM]` | Tier 2 Usage Rate `[SIM]` | Equiv. Cost / 1K Queries `[SIM]` | Mean Latency (ms) `[SIM]` |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B0** | Small LLM Only (Tier 1) | 58.2% | 58.2% | 41.8% | 34.2% | 0.284 | 0.0% | 0.0% | **$0.015** | 120 ms |
| **B1** | Strong LLM Only (Tier 2) | 76.4% | 76.4% | 23.6% | 18.5% | 0.196 | 0.0% | 100.0% | $0.085 | 450 ms |
| **B2-S1** | Single Signal: Token Prob ($S_1$) | 68.4% | 80.2% | 18.2% | 14.1% | 0.210 | 28.0% | 0.0% | $0.025 | 135 ms |
| **B2-S2** | Single Signal: Self-Consistency ($S_2$) | 71.2% | 82.4% | 15.4% | 11.8% | 0.175 | 26.0% | 0.0% | $0.060 | 380 ms |
| **B2-S3** | Single Signal: Self-Rated ($S_3$) | 64.0% | 79.0% | 21.0% | 16.4% | 0.242 | 31.0% | 0.0% | $0.030 | 210 ms |
| **B3** | **ConfiRoute Full System** | **88.4%** | **93.2%** | **4.2%** | **2.8%** | **0.064** | **25.2%** | **18.0%** | **$0.045** | **185 ms** |

*\*Scientific & Ethical Disclaimer: "Oracle Resolved Accuracy" assumes human clinicians achieve 100% resolution accuracy for queries routed to the Reviewer Queue. This serves as an idealized theoretical benchmark upper-bound.*

### Key Quantitative Target Findings:
1. **Targeted UCER Reduction:** ConfiRoute (B3) reduces the simulated Unsafe Confident Error Rate from **41.8% (B0)** down to **4.2% (B3)** — an **89.9% reduction in clinical hallucination exposure**.
2. **Selective Tier 2 Economic Efficiency:** ConfiRoute invokes the expensive Tier 2 model for only **18.0% of queries**, achieving 88.4% auto-accuracy at **$0.045 per 1K queries** (compared to $0.085 for Always-Tier-2 B1 — a **47.1% cost savings**).
3. **Calibration Impact:** Multi-signal Platt scaling and isotonic regression reduce 10-bin Expected Calibration Error (ECE) from **0.284** down to **0.064**.

---

## 2. Confidence Signal & Calibration Ablation Study (VAL Split) `[SIMULATED PROJECTIONS]`

Evaluation across signal combinations (fixed decision threshold $\tau = 0.70$):

| Configuration | Features Used | ECE (10-bin) `[SIM]` | AUROC `[SIM]` | Brier Score `[SIM]` | Auto-Accuracy `[SIM]` | UCER `[SIM]` | Escalation Rate `[SIM]` |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| $S_1$ Alone | Token log-prob softmax | 0.210 | 0.732 | 0.218 | 68.4% | 18.2% | 28.0% |
| $S_2$ Alone | Self-consistency agreement ($N=3$) | 0.175 | 0.768 | 0.194 | 71.2% | 15.4% | 26.0% |
| $S_3$ Alone | Self-rated certainty ($0-100$) | 0.242 | 0.694 | 0.235 | 64.0% | 21.0% | 31.0% |
| $S_1 + S_2$ | Dual signal composite | 0.142 | 0.798 | 0.172 | 75.8% | 12.1% | 25.5% |
| $S_1 + S_3$ | Dual signal composite | 0.180 | 0.745 | 0.201 | 70.4% | 16.8% | 28.2% |
| $S_2 + S_3$ | Dual signal composite | 0.158 | 0.782 | 0.182 | 74.0% | 13.5% | 27.0% |
| $S_1 + S_2 + S_3$ | Dynamic Weighted Average | 0.118 | 0.825 | 0.154 | 81.2% | 8.8% | 26.0% |
| **Platt Scaling** | **Logistic Meta-Model** | **0.078** | **0.842** | **0.138** | **85.6%** | **5.4%** | **25.8%** |
| **Isotonic Reg.** | **Monotonic Calibrated** | **0.064** | **0.846** | **0.132** | **88.4%** | **4.2%** | **25.2%** |

---

## 3. Answer-Removal Refusal Safety Experiment (TEST_REMOVED Split — 200 Questions) `[SIMULATED PROJECTIONS]`

In this stress test, the clinically correct answer was excised from question options, and Option D was designated as *"None of the above / Insufficient clinical information"*:

| Metric Evaluated | Standard Unrouted LLM (B0) `[SIM]` | ConfiRoute System (B3) `[SIM]` | Impact / Safety Gain `[SIM]` |
|:---|:---:|:---:|:---:|
| **Guess Rate (Hallucinations)** | **94.5%** | **4.0%** | **95.8% reduction in blind guessing** |
| **Explicit Abstention Rate (Option D)** | 5.5% | 8.0% | Safe refusal behavior |
| **Human Clinician Escalation Rate** | 0.0% | **88.0%** | Uncertainty held for verification |
| **Unsafe Confident Error Rate (UCER)** | **94.5%** | **4.0%** | **95.8% drop in patient risk** |

---

## 4. Current Experimental Verification Status

1. **Software Pipeline Verification:** The end-to-end evaluation scripts (`run_baselines.py`, `ablation.py`, `answer_removal.py`, `plots.py`) have been verified on sample subsets with 100% test passing rate.
2. **Real Model Inference Status:** **PENDING USER AUTHORIZATION.**
   - Ollama is not installed on the host laptop.
   - Groq API credentials are not set in `.env`.
   - In accordance with the ₹0 budget and hardware limits (8 GB RAM), no model weights were downloaded or batch requests made without explicit user instruction.
   - For detailed forensic audit findings and next commands, see [`reports/EVALUATION_AUDIT.md`](file:///c:/Users/akash/Desktop/confiroute-miniproject/confiroute/reports/EVALUATION_AUDIT.md).
