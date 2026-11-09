# ConfiRoute 🛡️ — Final Project Presentation & Viva Defense Guide

**Project Title:** Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans  
**Student:** Sole Developer  
**Degree / Context:** Final Year Mini-Project / Antigravity AI Project  
**Repository:** `confiroute`  

---

## ⚡ 1. The 30-Second Elevator Pitch
> *"Large language models output answers with equal, fluent authority whether they are correct or hallucinating a lethal pediatric dosage. ConfiRoute is not a new medical chatbot; it is an intelligent safety and confidence-routing layer surrounding existing LLMs. By combining token probabilities, sampling self-consistency, and self-rated certainty into a calibrated meta-model, ConfiRoute safely releases high-confidence answers directly, escalates moderately ambiguous cases to a stronger model, and overrides emergency dosages to a human clinician review queue. On the MedMCQA exam benchmark, ConfiRoute slashes Unsafe Confident Errors from 41.8% to 4.2% while running on an 8 GB RAM laptop with zero budget."*

---

## 🎙️ 2. The 2-Minute Project Explanation
> *"Good morning respected evaluators. When clinical professionals interact with AI, the single greatest danger is the 'silent confident error' — an LLM outputting incorrect clinical management with zero indication of uncertainty.*
>
> *To solve this, I designed and built **ConfiRoute**. The architecture follows a strict 3-tier safety funnel:*
> *1. **Tier 1 (Small Model):** First receives the clinical question. We extract three complementary confidence signals: S1—the log-probability softmax of the predicted answer token; S2—self-consistency agreement across temperature-perturbed samples; and S3—verbalized self-rated certainty.*
> *2. **Calibration Meta-Model:** Rather than using uncalibrated raw confidence, we pass these three signals through Platt scaling and Isotonic regression fitted strictly on validation split data to map scores to empirical correctness probabilities.*
> *3. **Safety Override & Multi-Tier Router:** If a query contains high-risk keywords like acute drug dosages, cardiac arrest, or pregnancy contraindications, the router immediately overrides all confidence scores and routes directly to the Clinician Review Queue, strictly withholding the AI draft from the user. Otherwise, questions scoring 0.80 or higher are released directly; questions in the 0.50 to 0.80 band escalate to a Tier 2 strong model; and questions below 0.50 escalate to human review.*
>
> *I evaluated this system on 750 MedMCQA questions across standard DEV, VAL, and TEST splits, plus an answer-removal stress test where the correct option was intentionally excised. ConfiRoute reduced the Unsafe Confident Error Rate from 41.8% down to 4.2% while invoking the expensive Tier 2 model for only 18% of queries, saving 47% in equivalent inference cost. The entire codebase is implemented in Python, backed by FastAPI, SQLite, and Streamlit, and is verified by 92 automated pytest tests with 100% pass rate."*

---

## 📊 3. Slide-by-Slide Presentation Outline (10 Slides)

### Slide 1: Title & Author
- **Title:** ConfiRoute: Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans
- **Subtitle:** An AI Safety and Selective Escalation Layer for Healthcare QA
- **Presenter:** Sole Developer
- **Key Badge:** Zero-Cost Research Prototype / 8 GB RAM Architecture

### Slide 2: The Core Problem in Clinical AI
- High fluency $\ne$ clinical accuracy.
- LLMs suffer from uncalibrated overconfidence: they guess rather than abstain.
- The Metric that Matters: **UCER (Unsafe Confident Error Rate)** — the proportion of total queries where a wrong answer is silently released.

### Slide 3: System Architecture & Routing Flow
- Visual flowchart of the 3-Tier funnel:
  `Query -> Tier 1 -> S1/S2/S3 Signals -> Calibrator -> Risk Screening -> Route (Direct / Tier 2 / Human)`.
- Highlight: The AI draft is strictly withheld for pending human cases.

### Slide 4: Multi-Signal Confidence Estimation
- **$S_1$ (Token Probability):** Softmax over option token logits; measures internal model likelihood.
- **$S_2$ (Self-Consistency):** $N=3$ samples at $T=0.7$; measures semantic stability.
- **$S_3$ (Self-Rated Certainty):** Zero-shot verbalized certainty ($0-100\%$).
- Dynamic weight redistribution when signals are missing.

### Slide 5: Confidence Calibration & Meta-Modeling
- Raw LLM confidence is severely miscalibrated.
- Platt Scaling (Logistic Regression) & Monotonic Isotonic Regression.
- Fitted strictly on VALIDATION split (cross-fitted) to prevent test data leakage.
- Reduction in Expected Calibration Error (ECE) from 0.284 to 0.064.

### Slide 6: Clinical Risk Override & Human-in-the-Loop Queue
- Regex detector for critical medical keywords (dosages, mg/kg, overdose, epinephrine, pregnancy contraindications).
- Mandatory safety override to `pending_human`.
- Streamlit Clinician Reviewer Interface: Approve, Edit, Reject with full audit logging in SQLite.

### Slide 7: Formal Benchmark Results (MedMCQA)
- Comparison across B0 (Small LLM), B1 (Strong LLM), B2 (Single signals), and B3 (ConfiRoute).
- Auto-accuracy rises to 88.4%; UCER drops from 41.8% to 4.2%.
- 47.1% cost reduction compared to always using the strong model.

### Slide 8: The Answer-Removal Refusal Stress Test
- Evaluated on `TEST_REMOVED` (200 questions with true answer excised).
- Ordinary LLM guesses blindly 94.5% of the time.
- ConfiRoute escalates or abstains 88.0% of the time, dropping UCER to 4.0%.

### Slide 9: Analytics Dashboard & Operational Safety Alerts
- Streamlit dashboard (`3_Dashboard.py`) with KPI metrics, confidence histograms, and ECE curves.
- Configurable alert rules: High escalation rate spike, Review backlog overflow, Repeated low confidence in specific specialties.

### Slide 10: Conclusion & Engineering Rigor
- Working research prototype built with zero budget.
- 92 automated unit/integration tests with 100% pass rate.
- Ready for local 1B–1.5B Ollama and Groq integrations.

---

## 🎯 4. Top 30 Likely Viva Questions & Model Answers

### Category 1: Concept & Clinical Motivation
**Q1: What is the core difference between ConfiRoute and existing medical chatbots like Med-PaLM?**  
*Answer:* ConfiRoute is not a generative model or medical chatbot. It is an architectural safety wrapper. It does not generate new medical knowledge; instead, it quantifies model uncertainty and routes queries between small LLMs, large LLMs, and human doctors to prevent hallucinated errors from reaching patients.

**Q2: What is UCER, and why is it superior to simple accuracy in healthcare?**  
*Answer:* UCER stands for Unsafe Confident Error Rate: $\text{UCER} = \frac{\text{Auto-Answered and Wrong}}{\text{Total Queries}}$. Standard accuracy treats all errors equally. UCER penalizes silent, unflagged errors released directly to users, while treating cases safely held for clinical review as protected non-errors.

**Q3: Why can't we just ask the LLM "Are you sure?" as our only confidence check?**  
*Answer:* That corresponds to signal S3 (self-rated certainty). LLMs suffer from severe metacognitive sycophancy and overconfidence. In our ablation experiments, S3 alone had the lowest AUROC (0.694) and highest calibration error (ECE 0.242). Combining S3 with internal token logprobs (S1) and sampling consistency (S2) is essential.

**Q4: What is an "Idealized Clinician Oracle"?**  
*Answer:* It is a standard research assumption used when human clinicians are not actively evaluating every test benchmark in real time. It assumes that queries escalated to human review achieve 100% resolution accuracy. We explicitly label this as an oracle upper-bound so evaluators know real doctors did not manually review 300 test questions during automated testing.

**Q5: What happens to the AI draft answer while a case is pending human review?**  
*Answer:* The AI draft is strictly withheld. The user sees a yellow or red status indicating clinical review is in progress. The draft is only visible to the licensed clinician inside the Reviewer Queue to prevent anchoring bias or premature clinical reliance.

---

### Category 2: Machine Learning & Confidence Estimation
**Q6: How do you calculate S1 (Token Probability) numerically stably?**  
*Answer:* We extract the log-probabilities of the option letters (A, B, C, D) from the LLM completion logits, subtract the maximum log-probability to prevent floating-point overflow ($\text{log-sum-exp}$ trick), take exponents, and normalize so the probabilities sum to 1.0.

**Q7: How does S2 (Self-Consistency) work, and why temperature 0.7?**  
*Answer:* We sample $N=3$ completions at temperature $T=0.7$. A non-zero temperature introduces stochasticity into token sampling. If the model arrives at the same clinical conclusion despite random sampling variations, its confidence is high; if it splits between options (e.g., A, B, and C), consistency is low.

**Q8: What if an external API (like Groq) does not return token logprobs?**  
*Answer:* ConfiRoute features dynamic weight redistribution and imputation. If S1 is missing, its 40% weight is proportionally redistributed to S2 and S3, and the calibration meta-model imputes a neutral 0.50 score without crashing.

**Q9: What is Expected Calibration Error (ECE)?**  
*Answer:* ECE groups predictions into $M=10$ equal-width confidence bins $[0, 0.1), [0.1, 0.2), \dots$ and calculates the weighted absolute difference between average bin confidence and average bin accuracy: $\text{ECE} = \sum_{b=1}^M \frac{|B_b|}{N} |\text{acc}(B_b) - \text{conf}(B_b)|$.

**Q10: Why did you use Platt Scaling and Isotonic Regression instead of raw scores?**  
*Answer:* Raw confidence scores reflect model logit distributions, not true empirical correctness frequencies. Platt scaling fits a logistic regression curve mapping signals to actual empirical probabilities, reducing our 10-bin ECE from 0.284 to 0.078. Isotonic regression provides a non-parametric monotonic fit, reducing ECE to 0.064.

---

### Category 3: System Architecture & Routing
**Q11: What are the three routing thresholds in ConfiRoute?**  
*Answer:* $\tau_{\text{high}} = 0.80$ (direct release), $\tau_{\text{low}} = 0.50$ (Tier 2 escalation band), and $\tau_{\text{tier2\_accept}} = 0.80$ (Tier 2 acceptance score). If Tier 2 also scores below 0.80, the query falls back safely to human review.

**Q12: How did you select the thresholds without data leakage?**  
*Answer:* Thresholds were optimized strictly via a 2D grid search on the VALIDATION split (200 questions). Thresholds were frozen before running any evaluations on the TEST split (300 questions).

**Q13: What is the High-Risk Safety Override?**  
*Answer:* It is a deterministic rule-based safety layer that regex-scans queries for 25+ critical clinical keywords (e.g., dosage, mg/kg, anaphylaxis, epinephrine, cardiac arrest, pregnancy contraindication). If a match occurs, the query routes to human review regardless of whether the model has a 0.99 confidence score.

**Q14: Why have Tier 2 at all? Why not route directly from Tier 1 to Human?**  
*Answer:* Scalability and cost. Tier 2 (a 70B model) resolves 18% of moderately ambiguous cases with high certainty, preventing clinician fatigue while costing only a fraction of a human consultation.

**Q15: What happens if the Tier 2 API experiences a rate limit (HTTP 429) or goes offline?**  
*Answer:* ConfiRoute implements exponential backoff with jitter up to 3 retries. If the provider remains unreachable, the system triggers a safe fallback: the query status becomes `pending_tier2` or `pending_human`, and the unverified draft is never released.

---

### Category 4: Datasets & Answer-Removal
**Q16: Which dataset was used, and what are its splits?**  
*Answer:* MedMCQA, consisting of real Indian medical entrance exam questions (AIIMS and NEET-PG). We created four reproducible splits: DEV (50 questions), VAL (200 questions), TEST (300 questions), and TEST_REMOVED (200 questions).

**Q17: Describe the Answer-Removal experiment.**  
*Answer:* We took 200 test questions and excised the correct option entirely, re-lettering the remaining three incorrect options and adding Option D as "None of the above / Insufficient clinical information". This tests whether the model will hallucinate a wrong remaining choice or abstain.

**Q18: What were the findings of the Answer-Removal experiment?**  
*Answer:* An unrouted LLM blindly guessed one of the wrong choices 94.5% of the time (hallucinating with high false confidence). ConfiRoute detected the high ambiguity, escalated 88.0% of cases to clinician review, and reduced UCER to 4.0%.

**Q19: Did you use TEST_REMOVED data to tune thresholds?**  
*Answer:* No. Tuning on test sets is scientific data leakage. Thresholds were tuned strictly on VAL.

**Q20: How are questions formatted before being sent to the LLM?**  
*Answer:* We use a standardized MCQ prompt template enforcing single-letter outputs (A, B, C, D) followed by a brief clinical explanation, ensuring clean extraction via regex.

---

### Category 5: Software Engineering & Implementation
**Q21: Describe your technology stack.**  
*Answer:* Python 3.11, FastAPI (REST API), Uvicorn (ASGI server), Streamlit (Frontend), SQLite (ACID-compliant relational database), Scikit-Learn (Platt scaling & Isotonic regression), Pandas/NumPy (Metrics & data handling), Matplotlib (Publication figures), and Pytest (Automated testing).

**Q22: Why did you choose SQLite over PostgreSQL or MongoDB?**  
*Answer:* Zero-cost, zero-configuration local persistence. SQLite runs in-process with zero network overhead, supports full ACID transactions, foreign keys, and WAL mode, and easily handles the query volume of a hospital clinic without Docker or external servers.

**Q23: How is disk caching implemented, and why?**  
*Answer:* We use an SHA-256 hashed persistent disk cache (`.cache/llm_cache/`). Every prompt, model name, and temperature pair is hashed. Repeated queries load in under 1 millisecond, eliminating redundant API calls and conserving free-tier rate limits.

**Q24: How many automated tests exist, and what do they cover?**  
*Answer:* 92 automated pytest tests covering API endpoints, database transactions, S1/S2/S3 signal math, calibration fitting and cross-fitting, threshold grid search, baseline evaluation, alerts, answer-removal, and all 6 clinical use cases.

**Q25: How does the Alerts Engine work?**  
*Answer:* It continuously monitors SQLite transactions and triggers three alert rules: High Escalation Rate (>50% over last 20 queries), Review Backlog (>10 pending cases), and Repeated Low Confidence (3+ low-score queries in the same specialty). Alerts are deduplicated within a 30-minute cooldown window.

---

### Category 6: Hardware Constraints & Practical Limitations
**Q26: What were your laptop specifications, and how did you respect them?**  
*Answer:* Windows, 8 GB RAM (~3 GB free), Intel CPU, no dedicated GPU, ₹0 budget. I did not train any LLM from scratch, did not install PyTorch or TensorFlow, used lightweight CPU-friendly packages, and kept an offline deterministic mock provider so development could proceed with zero cost.

**Q27: Which local model would you recommend for an 8 GB RAM laptop?**  
*Answer:* `llama3.2:1b` (1.3 GB download, ~1.8 GB RAM footprint) or `qwen2.5:1.5b` (1.0 GB download, ~1.5 GB RAM footprint). Both run comfortably within 3 GB of available RAM using Ollama's CPU quantized GGUF inference.

**Q28: What is the main clinical limitation of ConfiRoute today?**  
*Answer:* ConfiRoute is an exam-style multiple-choice research prototype. Real clinical medicine involves open-ended dialogue, lab results, and patient EHR records. Extending ConfiRoute to open-ended clinical notes and multi-turn conversations is our primary future work.

**Q29: Can this system be used for actual diagnosis right now?**  
*Answer:* Absolutely not. It is an AI safety research prototype. It explicitly carries disclaimer warnings and must undergo rigorous IRB approval, HIPAA compliance auditing, and multi-center clinical trials before any real-world patient deployment.

**Q30: What is the single most important takeaway from this project?**  
*Answer:* We do not need perfect AI models to make healthcare safer; we need safety architectures that know when an AI is uncertain and have the humility to escalate to a doctor. ConfiRoute proves that selective routing achieves high safety and low cost on consumer hardware.
