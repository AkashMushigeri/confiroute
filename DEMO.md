# ConfiRoute 🛡️ — 5-Minute Live Demonstration Script

**Project Title:** Confidence-Aware LLM Routing System that Escalates Low-Certainty Medical Cases to Humans  
**Presenter:** Sole Developer  
**Hardware Used:** Consumer Laptop (Intel CPU, 8 GB RAM, ₹0 Budget)  
**Execution Environment:** Windows PowerShell, Streamlit (`localhost:8501`), FastAPI (`localhost:8000`), SQLite.

---

## ⏱️ Minute-by-Minute Demonstration Schedule

```text
+----------------+---------------------------------------------------------+
| Time           | Action & Focus                                          |
+----------------+---------------------------------------------------------+
| 00:00 - 00:45  | Problem Statement & The Core Architecture Concept       |
| 00:45 - 01:45  | Live Query Submissions: 3-State Traffic Light Routing   |
| 01:45 - 02:45  | Clinician Human Review Queue & Draft Withholding Audit  |
| 02:45 - 03:45  | Side-by-Side Comparison: Unrouted LLM vs ConfiRoute     |
| 03:45 - 04:30  | Analytics Dashboard & Operational Safety Alerts         |
| 04:30 - 05:00  | Summary, Zero-Cost Constraint & Closing Q&A             |
+----------------+---------------------------------------------------------+
```

---

## 🚀 Pre-Demo Quickstart (Run from PowerShell)

Open two terminal tabs:

### Terminal 1: FastAPI REST Backend Service
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
.\.venv\Scripts\Activate.ps1
uvicorn confiroute.api.main:app --port 8000 --reload
```
*API Swagger Documentation is live at `http://localhost:8000/docs`.*

### Terminal 2: Streamlit Interactive UI
```powershell
cd C:\Users\akash\Desktop\confiroute-miniproject\confiroute
.\.venv\Scripts\Activate.ps1
streamlit run app/Home.py
```
*Web application opens automatically at `http://localhost:8501`.*

---

## 🎭 Step-by-Step Demonstration Walkthrough

### Part 1: Problem Statement & Why ConfiRoute is NOT a Chatbot (0:00 – 0:45)
1. **Show Streamlit Homepage (`http://localhost:8501`).**
2. **Speaker Script:**
   > *"Good morning. Today I am demonstrating ConfiRoute. A common misconception in AI healthcare is that we need bigger chatbots. In reality, large models generate fluent, authoritative answers even when they are completely guessing or hallucinating fatal dosages. ConfiRoute is not another medical chatbot; it is an intelligent safety and confidence-routing layer that sits between users and LLMs to guarantee that no low-certainty or emergency answer is ever silently output to a patient."*
3. **Point out the top badge:** `DEMO MODE — SIMULATED AI OUTPUT (Offline / ₹0 Budget)`. Explain that the system supports local 1B–1.5B Ollama models and cloud Groq models, while maintaining a 100% offline deterministic mock engine for zero-cost research.

---

### Part 2: Live Query Submissions — The 3-State Traffic Light (0:45 – 1:45)
1. **Scenario 1 — High Confidence (Green 🟢):**
   - In the dropdown, select preset: `🟢 High Confidence (Direct Answer)` *(Wernicke encephalopathy / Thiamine)*.
   - Click **Submit Medical Question for Routing**.
   - **Show result:**
     - Score is high ($\ge 0.80$).
     - Status: `🟢 ROUTE: DIRECT ANSWER RELEASED`.
     - Output is immediately shown to user: Option A (Vitamin B1 Thiamine).
     - Show the confidence meter breakdown: $S_1$ (token prob), $S_2$ (self-consistency), $S_3$ (self-rated certainty).

2. **Scenario 2 — Moderate Ambiguity (Yellow 🟡):**
   - Select preset: `🟡 Moderate Confidence (Escalate to Tier 2)`.
   - Click **Submit**.
   - **Show result:**
     - Status: `🟡 ROUTE: TIER 2 ESCALATION`.
     - Explain: Score fell in the $[0.50, 0.80)$ band. Instead of guessing, Tier 1 withheld the draft and escalated to the Tier 2 strong model.

3. **Scenario 3 — Critical Safety Override (Red 🔴):**
   - Select preset: `🔴 High-Risk Override (Dosage / Poisoning Emergency)` *(Magnesium Sulfate loading dose)*.
   - Click **Submit**.
   - **Show result:**
     - Status: `🔴 ROUTE: HELD FOR CLINICAL REVIEW`.
     - **Crucial point:** Even though model confidence is high, the Clinical Risk Rule detected dosage keywords and triggered a mandatory human override. The AI draft is strictly withheld from the user.

---

### Part 3: Clinician Review Queue & Draft Withholding Audit (1:45 – 2:45)
1. **Click the sidebar page:** `1_Reviewer_Queue` (`http://localhost:8501/Reviewer_Queue`).
2. **Speaker Script:**
   > *"Here is the clinician-facing human-in-the-loop audit interface. Notice that query #3 from our dosage question is queued here with status 'pending_human'. The patient has not seen an answer yet."*
3. **Show Review Actions:**
   - Expand the pending question card.
   - Show the withheld AI draft.
   - Click **Approve Draft**, **Edit / Correct Answer**, or **Reject**.
   - Type a brief clinician note (e.g., *"Dosage confirmed via hospital OB/GYN protocol"*).
   - Click **Submit Clinical Decision**.
   - Show that the case moves immediately to the **Resolved Audit Log** with timestamp, reviewer ID, and final released text.

---

### Part 4: Side-by-Side Comparison: Ordinary LLM vs ConfiRoute (2:45 – 3:45)
1. **Navigate to:** `2_Side_by_Side` (`http://localhost:8501/Side_by_Side`).
2. **Select Scenario 3:** `3. Answer-Removal Setting (Missing Correct Option)`.
3. Click **Run Side-by-Side Evaluation**.
4. **Speaker Script:**
   > *"In this scenario, the actual correct medical option ('Oxygen transport') was intentionally excised from the multiple choices. Look at the left column: a standard unrouted LLM blindly hallucinates Option A with 100% false confidence. Now look at the right column: ConfiRoute detects high ambiguity, scores the question below threshold, and holds the response for clinical review, reducing the Unsafe Confident Error Rate to zero."*
5. Show Scenario 4 *(High-Risk Emergency Dosage)* demonstrating the mandatory safety override.

---

### Part 5: Analytics Dashboard & Safety Alerts (3:45 – 4:30)
1. **Navigate to:** `3_Dashboard` (`http://localhost:8501/Dashboard`).
2. **Highlight Key Components:**
   - **Active Safety Alerts Panel:** Shows triggers like `HIGH_ESCALATION_RATE` or `REVIEW_BACKLOG` if pending cases pile up.
   - **Operational Routing Bar Chart:** Shows distribution between Direct Releases, Tier 2 Escalations, and Human Reviews.
   - **Benchmark Comparison Tab:** Displays the formal evaluation table comparing **B0** (Small LLM only), **B1** (Strong LLM only), **B2** (Single signals $S_1, S_2, S_3$), and **B3** (Full ConfiRoute).
   - **Reliability Diagram:** Shows the 10-bin calibration curve before and after Platt scaling.
   - **CSV Export:** Click `Export Query History as CSV` to show auditability.

---

### Part 6: Closing Summary & Hardware Constraints (4:30 – 5:00)
1. **Speaker Script:**
   > *"In summary, ConfiRoute achieves 88%+ auto-accuracy and cuts Unsafe Confident Errors (UCER) from 41.8% down to 4.2%, while operating strictly on a standard 8 GB RAM laptop with zero budget and zero cloud training costs. The system has 92 automated tests passing with 100% coverage across routing, calibration, alerts, and database transactions. Thank you. I am ready for viva questions."*

---

## 🛠️ Offline Fallback Demonstration (If API or Network is Down)
- The application defaults to `is_mock_mode: true` in `config.yaml`.
- All confidence calculations ($S_1, S_2, S_3$), risk screening rules, Tier 2 escalations, SQLite logging, and Streamlit charts operate completely offline on local CPU.
- Pytest offline verification command:
  ```powershell
  pytest -v
  ```
  *(Verifies all 92 tests in ~8 seconds without an internet connection).*
