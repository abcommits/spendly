# Spec: Registration

## Overview
Implement user registration so new visitors can create a Spendly account. This step wires up the `POST /register` handler, validates the submitted form data, hashes the password, inserts the new user into the database, and redirects to the login page on success. It also adds a `create_user()` helper to `database/db.py` to keep DB logic out of routes.

## Depends on
- Step 01 — Database Setup (`get_db()`, `init_db()`, `users` table must exist)

## Routes
- `POST /register` — handles registration form submission — public

## Database changes
No new tables or columns. The `users` table created in Step 01 already has all required columns (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates
- **Modify:** `templates/register.html` — form `action` already points to `POST /register`; add flash message support for errors (duplicate email, validation failures). No structural changes needed — the `{% if error %}` block is already present.

## Files to change
- `app.py` — add `POST /register` route handler; import `session`, `redirect`, `url_for`, `request`, `flash` from Flask; import `create_user` and `get_user_by_email` from `database.db`
- `database/db.py` — add `create_user(name, email, password)` and `get_user_by_email(email)` helpers

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security` (already in requirements) provides `generate_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterized queries only — never f-strings or `%` formatting in SQL
- Hash passwords with `werkzeug.security.generate_password_hash` before inserting
- Never store plaintext passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py` only — route function must not contain SQL
- Use `abort(400)` for malformed requests, not bare string returns
- Duplicate email must show a user-friendly error on the form (re-render `register.html` with `error=` context), not a 500
- On success, redirect to `/login` using `url_for('login')`
- Flask `secret_key` must be set on the app for `session`/`flash` to work — add it to `app.py` if missing

## Definition of done
- [ ] Submitting the form with a unique email and valid data creates a new row in the `users` table with a hashed (not plaintext) password
- [ ] Submitting with an email that already exists re-renders the registration form with an error message visible on the page
- [ ] Submitting with missing name, email, or password shows a validation error (or HTML5 `required` prevents submission)
- [ ] Successful registration redirects the browser to `/login`
- [ ] App starts without errors after the change
- [ ] No raw SQL appears inside `app.py` route functions
