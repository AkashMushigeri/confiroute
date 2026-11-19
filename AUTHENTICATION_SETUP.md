# ConfiRoute Authentication & Security Guide

This document covers the authentication system, password security, session handling, user isolation, and Role-Based Access Control (RBAC) implemented in ConfiRoute.

---

## 1. Authentication Architecture

ConfiRoute implements application-level authentication integrated with SQLite and Supabase PostgreSQL:

1. **Password Hashing:**
   - Algorithm: **PBKDF2 HMAC-SHA256** with `100,000` iterations.
   - Salt: Per-user cryptographically random 32-byte hex salt generated via `secrets.token_hex(32)`.
   - Passwords are never stored in plain text.
2. **Session Token Management:**
   - Tokens: 32-byte cryptographically secure random URL-safe tokens (`cr_sess_...`).
   - Token Storage: Stored in the `user_sessions` table with an expiration timestamp (`expires_at`).
   - Standard session duration: 7 days (or 30 days when "Remember session" is selected).
3. **Authorization Header:**
   - Clients deliver the session token via standard HTTP header:
     `Authorization: Bearer <token>`
   - The backend validates the token on each request against `user_sessions` and checks expiration.
4. **Token Revocation (Logout):**
   - Calling `POST /auth/logout` deletes the active token record from `user_sessions`.
   - Any subsequent request with that token is immediately rejected with `401 Unauthorized`.

---

## 2. Seed Accounts

For evaluation, three pre-seeded accounts exist:

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Administrator** | `admin@confiroute.ai` | `AdminSecure2026!` *(or `Admin2026!`)* | Full access: Admin Console, User Directory, All Conversations, Reviews, Stats |
| **Clinical Reviewer** | `clinician@confiroute.ai` | `Clinical2026!` *(or `confiroute2026`)* | AI Chat Workspace, Reviewer Queue, Case Approval/Correction/Rejection |
| **Clinical Auditor** | `auditor@confiroute.ai` | `Auditor2026!` | Reviewer Queue, Telemetry, Case Re-evaluation |

---

## 3. Role-Based Access Control (RBAC)

ConfiRoute enforces three distinct clinical roles:
1. `admin`:
   - Can access `/admin/*` endpoints (`/admin/users`, `/admin/stats`, `/admin/conversations`, `/admin/reviews`).
   - Can inspect all system conversations across clinicians.
   - Can register additional administrators.
2. `reviewer`:
   - Can access the Human Review Queue (`/queue`).
   - Can submit clinical review decisions (`POST /review/{query_id}`).
   - Can view historical review audits (`/reviews/history`).
3. `clinician`:
   - Can conduct AI Chat consultations (`POST /ask`).
   - Can manage their own private conversations.
   - Cannot view or delete other clinicians' consultations.

### Privilege Escalation Prevention
When registering via `POST /auth/register`, ordinary users cannot self-assign the `admin` role. If a non-admin client submits `role: "admin"`, the backend automatically downgrades the role to `"reviewer"` unless the request is authorized by an active administrator.

---

## 4. User Data Isolation

Conversations are strictly isolated by `user_id`:
* **Creation:** When an authenticated clinician creates a conversation via `POST /conversations`, it is tagged with their `user_id`.
* **Listing:** `GET /conversations` returns only conversations owned by the authenticated clinician.
* **Retrieval & Modification:** `GET /conversations/{id}`, `POST /conversations/{id}/messages`, and `DELETE /conversations/{id}` verify that `conversation.user_id == user["id"]`. If another user attempts access, the API responds with `403 Forbidden`.
* **Administrative Audit Exception:** System administrators can inspect conversations for safety auditing via `GET /admin/conversations`.

---

## 5. Frontend Authentication Integration

* **Context:** Managed globally in `frontend/src/context/AuthContext.tsx`.
* **Storage:** Tokens are persisted in `localStorage` (or `sessionStorage` if "Remember session" is unchecked).
* **Auto-Validation:** On page load, `api.getMe()` verifies the stored token with the backend. If expired or revoked, the token is cleared and the user is redirected to the luxury login portal.
* **Views:**
  * Login / Registration portal in `frontend/src/pages/LoginPage.tsx`.
  * Quick-fill demo credentials for immediate testing.
