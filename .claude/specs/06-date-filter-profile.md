# Spec: Date Filter for Profile Page

## Overview
This step adds a date range filter to the profile page so users can narrow their transaction history and spending stats to a specific time window. Currently the profile page shows all-time expenses; after this step a user can pick a start date, end date, or a preset period (e.g. "This Month", "Last 30 Days") and the transaction table, total-spent stat, transaction count, top category, and category breakdown all update to reflect only the matching expenses. The filter is applied server-side — the page reloads with query-string parameters, keeping the implementation in plain Flask with no JS required.

## Depends on
- Step 01 — Database Setup (`get_db()`, `init_db()`, `users` and `expenses` tables)
- Step 02 — Registration + Login (session management)
- Step 05 — Backend Routes for Profile Page (live DB helpers: `get_user_by_id`, `get_expenses_by_user`, `get_expense_stats`, `get_category_breakdown`)

## Routes
No new routes. The existing `GET /profile` route is extended to accept optional query-string parameters.

- `GET /profile?start=YYYY-MM-DD&end=YYYY-MM-DD` — filter expenses to the given date range, render `profile.html` — logged-in only
- `GET /profile?period=this_month` — shortcut preset that resolves to a date range server-side — logged-in only
- `GET /profile` (no params) — existing behaviour, shows all expenses — logged-in only

Supported `period` values: `this_month`, `last_30`, `last_90`, `this_year`.

## Database changes
No new tables or columns. Filtering is handled by adding `WHERE date BETWEEN ? AND ?` clauses to the existing queries using the `date` column already present on the `expenses` table.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter bar above the "Recent Transactions" section containing:
    - A `<form method="GET" action="{{ url_for('profile') }}">` wrapper
    - A preset `<select name="period">` with options: All Time, This Month, Last 30 Days, Last 90 Days, This Year
    - A date `<input type="date" name="start">` and `<input type="date" name="end">`
    - A submit button ("Apply") and a reset link ("Clear") that goes to `url_for('profile')`
  - The filter form must pre-fill `period`, `start`, and `end` with the currently active filter values (passed from the route as `active_filter`)
  - The Overview stats section must reflect the filtered date range (not all-time)
  - No structural changes to the transaction table or category breakdown — they already loop over `expenses` and `categories` which will now be filtered

## Files to change
- `app.py` — update the `profile()` view to:
  1. Read `start`, `end`, and `period` from `request.args`
  2. Resolve `period` presets into concrete `start`/`end` date strings
  3. Pass `start` and `end` to all four DB helpers
  4. Pass `active_filter` dict (`{"period": ..., "start": ..., "end": ...}`) to the template
- `database/db.py` — update four existing helpers to accept optional `start` and `end` parameters:
  - `get_expenses_by_user(user_id, start=None, end=None)`
  - `get_expense_stats(user_id, start=None, end=None)`
  - `get_category_breakdown(user_id, start=None, end=None)`
  - (No change needed to `get_user_by_id`)

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
- Date filtering must use SQL `BETWEEN ? AND ?` with the `date` column
- When `start`/`end` are `None`, the helpers must return the same results as before (no regression)
- `period` presets must be resolved in `app.py`, not in `database/db.py`
- The `start` and `end` values passed to helpers must be `"YYYY-MM-DD"` strings
- If the user supplies both `period` and `start`/`end` explicit dates, explicit dates take priority
- The filter form must use `GET`, not `POST` — filters must be bookmarkable via URL
- The Clear link must be a plain `<a>` pointing to `url_for('profile')` with no params
- Category fill colour classes (`category-fill-{{ cat.name | lower }}`) must be preserved unchanged

## Definition of done
- [ ] Visiting `/profile` with no params shows all expenses (no regression)
- [ ] Selecting "This Month" and clicking Apply reloads the page with `?period=this_month` in the URL
- [ ] The transaction table, total spent, transaction count, top category, and category breakdown all reflect only expenses within the filtered date range
- [ ] Entering explicit start/end dates and clicking Apply filters correctly
- [ ] The filter form pre-fills with the currently active filter values after applying
- [ ] Clicking "Clear" removes all filter params and shows the full expense list
- [ ] If no expenses match the filter, the transaction table shows an empty state (no Python error)
- [ ] Stats (total spent, transaction count) show `₹0` / `0` / `—` when the filtered set is empty
- [ ] No raw SQL appears inside `app.py`
- [ ] App starts without errors after the change
