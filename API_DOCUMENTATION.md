# ConfiRoute API Specification

Base URL: `http://127.0.0.1:8000` (Local) or your deployed production domain.
Interactive Swagger UI: `http://127.0.0.1:8000/docs`

---

## 1. Authentication Endpoints

### `POST /auth/login`
Authenticate a clinician or administrator with email and password.
* **Request Body:**
  ```json
  {
    "email": "clinician@confiroute.ai",
    "password": "Clinical2026!",
    "remember_me": true
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "token": "cr_sess_...",
    "user": {
      "id": "usr_clinician_01",
      "email": "clinician@confiroute.ai",
      "name": "Dr. Sarah Chen",
      "role": "reviewer",
      "department": "Emergency Medicine"
    },
    "message": "Clinician session successfully established."
  }
  ```

### `GET /auth/me`
Verify session token and retrieve authenticated user profile.
* **Header:** `Authorization: Bearer <token>`
* **Response (200 OK):**
  ```json
  {
    "user": {
      "id": "usr_clinician_01",
      "email": "clinician@confiroute.ai",
      "name": "Dr. Sarah Chen",
      "role": "reviewer",
      "department": "Emergency Medicine"
    }
  }
  ```

### `POST /auth/logout`
Revoke active session token.
* **Header:** `Authorization: Bearer <token>`
* **Response (200 OK):** `{"message": "Session terminated successfully."}`

### `POST /auth/register`
Register a new clinician or reviewer account.
* **Request Body:**
  ```json
  {
    "email": "new_doctor@hospital.org",
    "password": "SecurePassword2026!",
    "name": "Dr. Eleanor Vance",
    "role": "reviewer",
    "department": "Cardiology"
  }
  ```
* **Response (200 OK):** Returns new user object and session token.

---

## 2. Confidence Routing & Inference

### `POST /ask`
Submit a clinical question for multi-signal confidence evaluation and routing.
* **Request Body:**
  ```json
  {
    "question": "What is the primary contraindication for prescribing beta-blockers in acute decompensated heart failure?",
    "options": {
      "A": "Mild peripheral edema",
      "B": "Severe bradycardia or cardiogenic shock",
      "C": "Controlled hypertension",
      "D": "Chronic stable angina"
    },
    "subject": "Cardiology",
    "model_key": "tier1"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "query_id": "q-...",
    "route": "direct",
    "status": "completed",
    "color": "green",
    "final_answer": "Option B — Severe bradycardia or cardiogenic shock",
    "ai_draft_answer": "Option B — Severe bradycardia or cardiogenic shock",
    "scores": {
      "s1": 0.94,
      "s2": 1.0,
      "s3": 0.90,
      "combined": 0.946
    },
    "is_high_risk": false,
    "risk_reason": null,
    "reason": "High confidence (0.946 >= 0.80) -> Direct Answer",
    "tier_used": "tier1"
  }
  ```

---

## 3. Human Clinician Review Queue

### `GET /queue`
Retrieve pending cases awaiting clinical review.
* **Query Params:** `limit` (default: 50).
* **Response (200 OK):** Array of pending medical cases with original questions and AI drafts.

### `POST /review/{query_id}`
Review and resolve an escalated case (approve, edit, or reject).
* **Header:** `Authorization: Bearer <token>`
* **Request Body:**
  ```json
  {
    "reviewer_name": "Dr. Sarah Chen",
    "decision": "edit",
    "corrected_answer": "Option B — Verified against current clinical cardiology practice.",
    "notes": "Correction verified and approved."
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "query_id": "q-...",
    "decision": "edited",
    "updated_status": "reviewed_edited",
    "final_answer": "Option B — Verified against current clinical cardiology practice.",
    "reviewer_name": "Dr. Sarah Chen",
    "message": "Case updated with clinician correction: released to user."
  }
  ```

### `GET /reviews/history`
Retrieve historical clinical reviews audit log.
* **Response (200 OK):** Array of resolved review items with decisions, notes, and reviewer names.

---

## 4. Persistent Conversations (With User Isolation)

### `GET /conversations`
List conversations for the current authenticated user.
* **Header:** `Authorization: Bearer <token>`
* **Response (200 OK):** Array of conversation sessions.

### `POST /conversations`
Create or update a conversation session.
* **Header:** `Authorization: Bearer <token>`
* **Request Body:**
  ```json
  {
    "id": "sess_1795098000",
    "title": "Pediatric Inquiries",
    "subject": "Pediatrics"
  }
  ```

### `GET /conversations/{conversation_id}`
Retrieve a conversation and all its messages.
* **Header:** `Authorization: Bearer <token>`
* **Response (200 OK):** Conversation object with ordered `messages` array.
* **Status 403 Forbidden:** Returned if another user attempts to view a private conversation.

### `POST /conversations/{conversation_id}/messages`
Persist a user or AI assistant message turn.
* **Header:** `Authorization: Bearer <token>`
* **Request Body:**
  ```json
  {
    "role": "user",
    "content": "Patient with acute respiratory distress, wheezing.",
    "subject": "Pediatrics"
  }
  ```

### `DELETE /conversations/{conversation_id}`
Delete a conversation and its messages.
* **Header:** `Authorization: Bearer <token>`
* **Status 403 Forbidden:** Returned if requesting user is not the conversation owner or an admin.

---

## 5. Administrator Governance Endpoints

*All endpoints in this section require `role: "admin"`.*

### `GET /admin/users`
List all registered users, roles, departments, active status, and registration dates.
* **Header:** `Authorization: Bearer <admin_token>`

### `GET /admin/stats`
Return system-wide statistics: total users, active accounts, conversations, messages, routing decisions breakdown, safety catches, and reviews.
* **Header:** `Authorization: Bearer <admin_token>`

### `GET /admin/conversations`
Retrieve all conversations across all clinicians with user attribution.
* **Header:** `Authorization: Bearer <admin_token>`

### `GET /admin/reviews`
Retrieve full history of human reviews across all reviewers.
* **Header:** `Authorization: Bearer <admin_token>`

### `GET /routing/logs`
Retrieve raw routing evaluations with confidence scores ($S_1, S_2, S_3$), model tier, risk flags, and latencies.
* **Header:** `Authorization: Bearer <token>`
