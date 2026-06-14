# Spec: Backend Routes for Profile Page

## Overview
This step replaces the hardcoded static data in the `/profile` route with real database queries. The profile page already has a complete UI (built in Step 4); now `app.py` must pull the authenticated user's actual record from `users`, fetch their expenses from `expenses`, and compute summary stats (total spent, transaction count, top category) — all via helpers in `database/db.py`. No template structure changes are needed; only the data source changes from hardcoded dicts to live DB results.

## Depends on
- Step 01 — Database Setup (`get_db()`, `init_db()`, `users` and `expenses` tables)
- Step 02 — Registration (`create_user`, `get_user_by_email`)
- Step 03 — Login + Logout (session sets `session["user_id"]`; profile route already guards with it)
- Step 04 — Profile Page Design (`templates/profile.html` must exist with correct variable names)

## Routes
No new routes. The existing `GET /profile` route is modified to serve real data.

- `GET /profile` — fetch live user + expense data from DB, render `profile.html` — logged-in only

## Database changes
No new tables or columns. The existing `users` and `expenses` tables already contain all required fields.

## Templates
- **Modify:** none — `templates/profile.html` already accepts `user`, `stats`, `expenses`, and `categories` context variables. The variable names and structure must be preserved exactly so the template renders without changes.

## Files to change
- `app.py` — replace the hardcoded dicts in the `profile()` view with calls to new DB helpers; import the new helpers from `database.db`
- `database/db.py` — add three new helper functions (see Rules below)

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only — never f-strings or `%` in SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py` only — no SQL inside route functions
- The three helpers to add to `database/db.py`:
  1. `get_user_by_id(user_id)` — returns the `users` row for the given id, or `None`
  2. `get_expenses_by_user(user_id)` — returns a list of expense rows for the user, ordered by `date DESC`
  3. `get_expense_stats(user_id)` — returns a dict with keys `total_spent` (float), `transaction_count` (int), `top_category` (str or `None`)
- The `profile()` route must:
  - Read `session["user_id"]`; redirect to `/login` if absent
  - Call `get_user_by_id()` and `abort(404)` if the user is not found
  - Call `get_expenses_by_user()` for the recent transactions list
  - Call `get_expense_stats()` for the summary stats row
  - Compute `categories` breakdown (name, formatted amount, percentage) in the route or via a helper — must mirror the shape the template already expects: `[{"name": ..., "amount": ..., "pct": ...}]`
  - Format `user["created_at"]` into a human-readable string (e.g. `"January 2026"`) before passing to template
  - Format amounts as `₹X,XXX` strings before passing to template
  - Pass `user`, `stats`, `expenses`, `categories` to `render_template` with the same key names as Step 4

## Definition of done
- [ ] Visiting `/profile` without a session redirects to `/login`
- [ ] Logging in as the demo user (`demo@spendly.app`) and visiting `/profile` shows that user's real name and email (not "Priya Sharma")
- [ ] The summary stats (total spent, transaction count, top category) match the actual seeded expenses in the database
- [ ] The transaction history table lists the seeded expenses sorted newest-first
- [ ] The category breakdown percentages add up to 100% (or close, allowing rounding)
- [ ] No hardcoded user data or expense data remains in the `profile()` route function
- [ ] No raw SQL appears inside `app.py`
- [ ] `get_user_by_id`, `get_expenses_by_user`, and `get_expense_stats` exist in `database/db.py`
- [ ] App starts without errors after the change
