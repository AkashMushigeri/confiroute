# ConfiRoute Database Architecture & Setup Guide

This document describes the unified database architecture for **ConfiRoute**, supporting both **Supabase PostgreSQL** in cloud deployments and local **SQLite** for development and automated testing.

---

## 1. Architecture & Selection Rationale

ConfiRoute uses **SQLAlchemy ORM** coupled with connection pooling to abstract the underlying database dialect:
* **Production / Cloud:** Supabase PostgreSQL provides transactional ACID guarantees, persistent storage that survives container redeployments, connection pooling (`pool_size=10, max_overflow=20`), and role-based access control.
* **Development / Testing:** Local SQLite (`data/confiroute.db`) provides zero-latency offline operation with WAL (Write-Ahead Logging) and thread-safe operations.

The backend dynamically selects the database engine based on the `DATABASE_URL` environment variable:
* If `DATABASE_URL` starts with `postgresql://` or `postgres://`, ConfiRoute routes queries through `psycopg2` to Supabase.
* If `DATABASE_URL` is unset or points to `sqlite://`, it seamlessly connects to the local database file.

---

## 2. Table Schemas & Relationships

### Core Application Tables

```
 users (1) <─────── (1) profiles
   │
   ├── (1) <─────── (N) user_sessions
   │
   ├── (1) <─────── (N) conversations ─────── (1) <─── (N) conversation_messages
   │                         │                                      │
   │                         └── (1) <─── (N) routing_logs <────────┘
   │                         │                     │
   ├── (1) <─────── (N) human_reviews <────────────┘
   │
   └── (1) <─────── (N) audit_logs
```

### Table 1: `users`
Stores authenticated clinical practitioners, reviewers, and administrators.
* `id` (VARCHAR 64, PK): Unique prefixed identifier (`usr_...`).
* `name` (VARCHAR 255): Full clinician name and title (e.g. `Dr. Sarah Chen, MD`).
* `email` (VARCHAR 255, UNIQUE, Indexed): Login identifier.
* `password_hash` (VARCHAR 255): PBKDF2 HMAC-SHA256 hash.
* `salt` (VARCHAR 64): Cryptographic per-user random hex salt.
* `role` (VARCHAR 32): Role-based access control (`admin`, `reviewer`, `clinician`).
* `department` (VARCHAR 128): Hospital specialty department.
* `is_active` (BOOLEAN): Soft-disable switch for account deactivation.
* `created_at` / `updated_at` (TIMESTAMP): Audit timestamps.

### Table 2: `profiles`
Extended profile information.
* `id` (VARCHAR 64, PK): Profile ID.
* `user_id` (VARCHAR 64, FK -> `users.id` ON DELETE CASCADE).
* `full_name` (VARCHAR 255): Formatted display name.
* `profile_image` (TEXT): Base64 or URL avatar.
* `created_at` / `updated_at` (TIMESTAMP).

### Table 3: `conversations`
Persistent multi-turn chat sessions with strict user isolation.
* `id` (VARCHAR 64, PK): Session ID (`sess_...`).
* `user_id` (VARCHAR 64, FK -> `users.id` ON DELETE SET NULL).
* `title` (VARCHAR 255): Clinical inquiry title.
* `subject` (VARCHAR 128): Specialty (e.g. `Cardiology`, `General Medicine`).
* `status` (VARCHAR 32): `active`, `archived`.
* `created_at` / `updated_at` (TIMESTAMP).

### Table 4: `conversation_messages`
Individual message turns within a conversation.
* `id` (VARCHAR 64, PK): Message ID (`msg_...`).
* `conversation_id` (VARCHAR 64, FK -> `conversations.id` ON DELETE CASCADE).
* `user_id` (VARCHAR 64, FK -> `users.id` ON DELETE SET NULL).
* `role` (VARCHAR 32): `user` or `assistant`.
* `content` (TEXT): Clinical question or generated response text.
* `options_json` (TEXT): JSON-encoded multiple choice alternatives.
* `subject` (VARCHAR 128): Specialty classification.
* `query_id` (VARCHAR 64, FK -> `queries.id` ON DELETE SET NULL): Linked routing result.
* `created_at` (TIMESTAMP).

### Table 5: `routing_logs`
Confidence-aware routing audit log.
* `id` (VARCHAR 64, PK): Log identifier (`rout_...`).
* `conversation_id` (VARCHAR 64, FK -> `conversations.id` ON DELETE SET NULL).
* `message_id` (VARCHAR 64, FK -> `conversation_messages.id` ON DELETE SET NULL).
* `query_id` (VARCHAR 64, FK -> `queries.id` ON DELETE SET NULL).
* `selected_model` (VARCHAR 128): Executed LLM (`llama3.2:3b`, `gpt-oss-120b`).
* `confidence_score` (FLOAT): Combined calibrated confidence score ($C$).
* `s1` (FLOAT): Token log-probability score ($S_1$).
* `s2` (FLOAT): Self-consistency agreement score ($S_2$).
* `s3` (FLOAT): Introspective self-rated certainty ($S_3$).
* `risk_level` (VARCHAR 32): `standard`, `high`.
* `is_high_risk` (BOOLEAN): High-risk clinical keyword override flag.
* `routing_decision` (VARCHAR 32): `direct`, `tier2`, `human`.
* `escalation_reason` (TEXT): Explanation for escalation or hold.
* `latency` (FLOAT): Execution latency in milliseconds.
* `created_at` (TIMESTAMP).

### Table 6: `human_reviews`
Records human clinician review interventions and corrections.
* `id` (VARCHAR 64, PK): Review ID (`hrev_...`).
* `conversation_id` (VARCHAR 64, FK -> `conversations.id`).
* `message_id` (VARCHAR 64, FK -> `conversation_messages.id`).
* `query_id` (VARCHAR 64, FK -> `queries.id` ON DELETE CASCADE).
* `reviewer_id` (VARCHAR 64, FK -> `users.id` ON DELETE SET NULL).
* `reviewer_name` (VARCHAR 255): Clinician auditor display name.
* `review_status` (VARCHAR 32): `pending`, `approved`, `edited`, `rejected`.
* `decision` (VARCHAR 32): `approved`, `edited`, `rejected`.
* `original_response` (TEXT): AI draft answer held at gate.
* `corrected_response` (TEXT): Human clinician corrected guidance.
* `reviewer_feedback` / `notes` (TEXT): Clinical audit justification.
* `created_at` / `updated_at` (TIMESTAMP).

### Table 7: `audit_logs`
Security and administrative compliance audit trail.
* `id` (VARCHAR 64, PK): Audit log ID (`aud_...`).
* `user_id` (VARCHAR 64, FK -> `users.id` ON DELETE SET NULL).
* `action` (VARCHAR 64): `user_login`, `user_register`, `conversation_delete`, `review_submit`.
* `resource_type` (VARCHAR 64): `auth`, `conversation`, `review`, `user`.
* `resource_id` (VARCHAR 64): Target entity ID.
* `details_json` (TEXT): Additional context metadata.
* `created_at` (TIMESTAMP).

---

## 3. Setup Instructions

### Option A: Local Development (SQLite)
No cloud database setup required. SQLite initializes automatically at `data/confiroute.db`:
```powershell
# Set in .env
DATABASE_URL=sqlite:///data/confiroute.db
```

### Option B: Cloud Database (Supabase PostgreSQL)
1. **Create Supabase Project:**
   - Log in to [Supabase Dashboard](https://supabase.com/dashboard) and create a project (e.g. `confiroute-prod`).
2. **Retrieve Connection String:**
   - Go to **Project Settings** → **Database** → **Connection String** → **URI**.
   - Select **Mode: Session** (Port `5432`) or **Mode: Transaction** (Port `6543`).
3. **Configure Environment Variable:**
   ```bash
   DATABASE_URL=postgresql+psycopg2://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```
4. **Initialize Schema & Seed Default Accounts:**
   Run the database initialization script:
   ```powershell
   .\.venv\Scripts\python.exe -c "from confiroute.db.connection import init_cloud_and_local_db; init_cloud_and_local_db(); print('Cloud database initialized!')"
   ```

---

## 4. Viewing Stored Data

### Via Supabase Web Dashboard
* Log in to [Supabase Studio](https://supabase.com/dashboard/project/_/editor).
* Open the **Table Editor** to inspect `users`, `conversations`, `conversation_messages`, `routing_logs`, and `human_reviews` in real-time.

### Via ConfiRoute Admin Dashboard
* Log in to the ConfiRoute frontend with administrator credentials:
  * **Email:** `admin@confiroute.ai`
  * **Password:** `AdminSecure2026!`
* Navigate to the **Admin Console** tab to view live user directories, conversation histories, routing logs, and clinical reviews.
