# ConfiRoute Admin Dashboard & Governance Setup

This guide details the administrative dashboard, superuser access controls, and clinical oversight features in ConfiRoute.

---

## 1. Overview & Capabilities

The **Admin Console** provides clinical AI system architects and hospital administrators with comprehensive governance tools:
* **Executive Metrics:** Real-time KPI summaries (Total Registered Clinicians, Active Sessions, Total Conversations, Routing Inquiries, High-Risk Holds, Review Resolution Ratios).
* **User Management Directory:** Searchable catalog of all registered practitioners, displaying names, emails, roles, departments, active status, and account registration dates.
* **Global Conversations Audit:** Oversight of all chat inquiries across clinicians, showing user attribution, titles, medical specialties, message counts, and last activity timestamps.
* **Routing Logs:** Detailed inspection of every confidence evaluation ($S_1$ token logprob, $S_2$ self-consistency, $S_3$ certainty), model key, escalation reasons, and processing latencies.
* **Human Review Oversight:** Log of all clinician interventions, original held responses, clinician corrections, and feedback notes.

---

## 2. Admin Security & Role Enforcement

* **Server-Side Enforcement:** Admin access is strictly enforced server-side using the `require_admin_user` FastAPI dependency. Frontend navigation gates are only visual conveniences; any unauthorized HTTP request to `/admin/*` without an admin token is rejected with `HTTP 403 Forbidden`.
* **Zero Credential Exposure:** User password hashes and salts are stripped from all admin API responses (`password_hash` and `salt` are never serialized in JSON output).
* **Audit Logging:** Administrative operations are recorded in the `audit_logs` table.

---

## 3. How to Access the Admin Dashboard

### Step 1: Log in with Administrator Credentials
Open the ConfiRoute web interface (`http://localhost:5173` or deployed URL) and sign in using the pre-seeded admin account:
* **Email:** `admin@confiroute.ai`
* **Password:** `AdminSecure2026!` *(or `Admin2026!`)*

*(You can also click the "Admin Demo" quick-fill button on the login screen).*

### Step 2: Open Admin Console
Once authenticated as an administrator, an **Admin Console** button with a gold `ADMIN` badge appears in the left navigation sidebar. Click it to enter the dashboard.

---

## 4. Admin API Endpoints

All admin endpoints require an active Bearer session token belonging to an administrator (`role == "admin"`):

| Endpoint | Method | Description |
|---|:---:|---|
| `/admin/users` | `GET` | List all registered accounts with role, department, and active status |
| `/admin/stats` | `GET` | Return system-wide aggregate metrics and routing distributions |
| `/admin/conversations` | `GET` | Inspect all chat inquiries across clinicians |
| `/admin/reviews` | `GET` | View all clinical review decisions and corrections |
| `/routing/logs` | `GET` | Access raw confidence scoring and routing decision logs |
