# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt   # install dependencies
python app.py                      # start dev server at http://localhost:5001
pytest                             # run all tests
pytest tests/test_foo.py::test_bar # run a single test
```

## Architecture

**Spendly** is a Flask expense-tracker web app targeting Indian users (₹ currency). It follows a traditional MVC structure:

- `app.py` — all Flask routes; student-facing placeholder routes are annotated with step numbers (Step 3, Step 4, …)
- `database/db.py` — SQLite database module; students implement `get_db()`, `init_db()`, and `seed_db()`
- `templates/` — Jinja2 templates; `base.html` is the master layout (navbar, footer, Google Fonts)
- `static/css/style.css` — single 692-line stylesheet; uses CSS variables (`--ink`, `--paper`, `--accent`, `--danger`) and component classes (`.btn-primary`, `.btn-ghost`, `.btn-dark`)
- `static/js/main.js` — vanilla JS placeholder; no frontend framework

The database layer (SQLite via `sqlite3`) is the only persistence mechanism — no ORM. `get_db()` must set `row_factory = sqlite3.Row` and enable foreign keys.

## Current Implementation State

- **Done:** landing page, auth form templates, full CSS design system, legal pages (terms, privacy)
- **Not yet implemented:** database schema, auth POST handlers (login/register), expense CRUD, user profile, logout — these are staged as numbered curriculum steps in `app.py`

## Design System

Typography: DM Serif Display (headings), DM Sans (body). Responsive breakpoints at 900px and 600px. The YouTube "See how it works" modal is currently wired to a placeholder video ID in `landing.html`.
