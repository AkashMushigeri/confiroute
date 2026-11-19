# ConfiRoute Cloud Deployment Guide

This guide describes how to deploy ConfiRoute to production cloud infrastructure (Render, Railway, Fly.io, or AWS) using **Supabase PostgreSQL** as the persistent cloud database.

---

## 1. Cloud Architecture Overview

In production:
1. **Frontend:** React SPA built into a single self-contained distribution (`frontend/dist/index.html`).
2. **Backend:** FastAPI application running with Uvicorn worker processes. The FastAPI application serves both REST API endpoints and static frontend assets via single-page application fallback routing.
3. **Database:** Supabase PostgreSQL database handling persistent tables (`users`, `conversations`, `messages`, `routing_logs`, `human_reviews`, `audit_logs`).

---

## 2. Supabase Cloud Database Provisioning

1. Sign up or log in to [Supabase](https://supabase.com).
2. Create a new project:
   * **Project Name:** `confiroute-production`
   * **Database Password:** Generate and securely save a strong password.
   * **Region:** Select the region closest to your cloud hosting service.
3. Obtain the PostgreSQL connection string:
   * Navigate to **Project Settings** → **Database** → **Connection String** → **URI**.
   * Format:
     ```text
     postgresql+psycopg2://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
     ```
   *(If your cloud provider uses IPv4 only, select the Supabase Transaction Pooler on port `6543`).*

---

## 3. Environment Variables Configuration

Set these variables on your cloud hosting platform:

| Variable | Recommended Production Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres` | Cloud database URI |
| `ENVIRONMENT` | `production` | Production mode flag |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `GROQ_API_KEY` | `gsk_...` | Groq LLM inference key (free tier) |
| `SECRET_KEY` | *(Generated random 64-character string)* | Session encryption key |

---

## 4. Build and Start Commands

### Render / Railway / Fly.io Configuration

* **Build Command:**
  ```bash
  pip install -e . && pip install sqlalchemy psycopg2-binary alembic && npm --prefix frontend install && npm --prefix frontend run build
  ```
* **Start Command:**
  ```bash
  uvicorn confiroute.api.main:app --host 0.0.0.0 --port $PORT
  ```

### Automated Table Creation & Seeding
When the backend starts, `confiroute.api.main` calls `init_db()`, which triggers `init_cloud_and_local_db()` via SQLAlchemy. All required tables, foreign keys, indexes, and initial administrator accounts are initialized on the Supabase PostgreSQL database without manual SQL execution.

---

## 5. Verification & Health Check

After deployment:
1. **Health Endpoint:**
   ```bash
   curl https://your-domain.com/health
   ```
   Expect: `{"status": "healthy", "app_name": "ConfiRoute", "version": "0.1.0"}`
2. **Swagger Docs:**
   Visit `https://your-domain.com/docs` to test endpoints interactively.
3. **Admin Verification:**
   Visit `https://your-domain.com` and log in with the administrator account (`admin@confiroute.ai` / `AdminSecure2026!`). Verify that the Admin Console loads system records directly from Supabase PostgreSQL.
