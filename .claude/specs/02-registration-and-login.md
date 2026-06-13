# Spec: Registration and Login

## Overview
Complete the auth entry points so users can create an account and sign in to Spendly. Registration (`POST /register`) is already implemented. This spec adds the `POST /login` handler: it validates credentials, starts a Flask session, and redirects to `/profile` on success. It also adds the `check_password` DB helper needed for credential verification. Together these two POST routes form the full auth entry flow before session-protected pages are introduced in later steps.

## Depends on
- Step 01 — Database Setup (`get_db()`, `init_db()`, `users` table)
- Step 02 — Registration (`create_user`, `get_user_by_email` already in `database/db.py`)

## Routes
- `POST /login` — validates email + password, sets `session["user_id"]`, redirects to `/profile` on success — public

## Database changes
No new tables or columns. All required fields exist on the `users` table.

## Templates
- **Modify:** `templates/login.html` — already has `{% if error %}` block and `action="/login"` with `method="POST"`; no structural changes needed.

## Files to change
- `app.py` — add `session` to Flask imports; import `check_password` from `database.db`; convert `GET /login` to `GET+POST` with full handler logic
- `database/db.py` — add `check_password(email, password)` helper

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is already available.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterized queries only — never f-strings or `%` in SQL
- Verify passwords with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py` only — no SQL inside route functions
- Store only `user_id` (integer) in the session — never store name, email, or password_hash
- On bad credentials, re-render `login.html` with `error=` — do not reveal whether email or password was wrong (use a generic message)
- On success, redirect to `url_for("profile")`
- `app.secret_key` is already set from the registration step

## Definition of done
- [ ] Submitting the login form with the demo user credentials (`demo@spendly.app` / any wrong password) shows the generic error message
- [ ] Submitting with a valid email + correct password sets `session["user_id"]` and redirects to `/profile`
- [ ] Submitting with an email that does not exist shows the generic error message
- [ ] No raw SQL appears inside `app.py` route functions
- [ ] `check_password()` lives in `database/db.py` and uses `check_password_hash`
- [ ] App starts without errors after the change
