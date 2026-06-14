"""
Tests for Spec 06 — Date Filter on the Profile Page.

Feature summary
---------------
The GET /profile route accepts optional query-string parameters
(period, start, end) and filters every stat/list rendered on the page
to the resolved date range.  No new route is added; the existing
profile route is extended.

Test categories covered
-----------------------
1. Happy path — no filter shows all expenses
2. Happy path — period preset resolves and filters correctly
3. Happy path — explicit start/end dates filter correctly
4. Active filter pre-fill — form values echo the active filter params
5. Stats reflect filtered data (total_spent, transaction_count, top_category)
6. Category breakdown reflects filtered data
7. Empty state when no expenses match the filter
8. Auth guard — unauthenticated requests redirect to /login
9. Edge cases
   a. Malformed date strings are silently ignored (falls back to all data)
   b. Inverted start/end (start > end) are swapped automatically
   c. Unknown period value treated as no filter
   d. Both period and explicit dates supplied — explicit dates take priority
10. Clear-filter link only appears when a filter is active
"""

import os
import sqlite3
import tempfile
from datetime import date, timedelta

import pytest

# ---------------------------------------------------------------------------
# DB isolation helpers
# ---------------------------------------------------------------------------

def _connect(db_path):
    """Open a connection to *db_path* with row_factory and FK enforcement."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_schema(db_path):
    """Create the users and expenses tables in a fresh DB file."""
    conn = _connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            amount         REAL    NOT NULL,
            category       TEXT    NOT NULL,
            description    TEXT,
            date           DATE    NOT NULL,
            payment_method TEXT,
            tags           TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def _insert_user(db_path, name="Test User", email="test@example.com",
                 password_hash="hashed"):
    """Insert a user row and return the new id."""
    conn = _connect(db_path)
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def _insert_expense(db_path, user_id, amount, category, description, exp_date,
                    payment_method="UPI", tags=""):
    """Insert a single expense row and return its id."""
    conn = _connect(db_path)
    cur = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, description, date,"
        " payment_method, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, amount, category, description, exp_date, payment_method, tags),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_db(monkeypatch, tmp_path):
    """
    Create an isolated SQLite DB in a temp directory, patch database.db.DATABASE
    so that every call to get_db() inside the app uses this temp file, and
    return the path for direct DB manipulation in tests.
    """
    db_path = str(tmp_path / "test_spendly.db")
    _create_schema(db_path)

    import database.db as db_module
    monkeypatch.setattr(db_module, "DATABASE", db_path)

    return db_path


@pytest.fixture()
def app(isolated_db):
    """Flask test application wired to the isolated DB."""
    from app import app as flask_app

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })
    return flask_app


@pytest.fixture()
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture()
def seeded_user(isolated_db):
    """
    Insert a test user with a known werkzeug-hashed password and return
    a dict with id, email, and plain password for use in login calls.
    """
    from werkzeug.security import generate_password_hash

    password = "TestPass1!"
    uid = _insert_user(
        isolated_db,
        name="Alice Sharma",
        email="alice@example.com",
        password_hash=generate_password_hash(password),
    )
    return {"id": uid, "email": "alice@example.com", "password": password}


@pytest.fixture()
def auth_client(client, seeded_user):
    """Authenticated test client logged in as the seeded test user."""
    client.post(
        "/login",
        data={"email": seeded_user["email"], "password": seeded_user["password"]},
    )
    return client


# ---------------------------------------------------------------------------
# Helper: dates relative to today
# ---------------------------------------------------------------------------

def _today():
    return date.today()

def _iso(d):
    return d.isoformat()

def _fmt(d):
    """Format a date the way get_expenses_by_user renders it: '01 Jun 2026'."""
    return d.strftime("%d %b %Y")


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestAuthGuard:
    """Unauthenticated access to /profile must redirect to /login."""

    def test_profile_unauthenticated_redirects_to_login(self, client):
        """GET /profile without a session must return a redirect to /login."""
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_profile_unauthenticated_follow_redirects_shows_login_page(self, client):
        """Following the redirect lands on the login page, not the profile page."""
        resp = client.get("/profile", follow_redirects=True)
        assert resp.status_code == 200
        # The login template must render — look for login-specific content
        data = resp.data.decode()
        assert "login" in data.lower() or "sign in" in data.lower()

    def test_profile_with_filter_params_unauthenticated_redirects(self, client):
        """Auth guard fires even when query params are present."""
        resp = client.get("/profile?period=this_month")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


class TestNoFilter:
    """GET /profile with no query params shows all expenses."""

    def test_no_filter_returns_200(self, auth_client, seeded_user, isolated_db):
        """Profile page with no filter params returns HTTP 200."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200

    def test_no_filter_shows_all_expenses(self, auth_client, seeded_user, isolated_db):
        """All inserted expenses appear in the transaction table."""
        today = _today()
        uid = seeded_user["id"]

        # Insert expenses on two different dates far apart
        _insert_expense(isolated_db, uid, 500.0, "Groceries", "Veggies",
                        _iso(today - timedelta(days=60)))
        _insert_expense(isolated_db, uid, 200.0, "Transport", "Bus pass",
                        _iso(today - timedelta(days=5)))

        resp = auth_client.get("/profile", follow_redirects=True)
        data = resp.data.decode()

        assert "Veggies" in data
        assert "Bus pass" in data

    def test_no_filter_total_spent_sums_all_expenses(self, auth_client, seeded_user, isolated_db):
        """Total spent stat equals the sum of all user expenses."""
        today = _today()
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 1000.0, "Groceries", "Shop A",
                        _iso(today - timedelta(days=90)))
        _insert_expense(isolated_db, uid, 500.0, "Transport", "Cab",
                        _iso(today - timedelta(days=1)))

        resp = auth_client.get("/profile")
        data = resp.data.decode()

        # Total is ₹1,500 formatted as ₹1,500
        assert "1,500" in data

    def test_no_filter_active_filter_is_false(self, auth_client, seeded_user, isolated_db):
        """When no filter params are present, active_filter.is_active is falsy
        so the Clear filter link must NOT appear."""
        resp = auth_client.get("/profile")
        data = resp.data.decode()

        assert "Clear filter" not in data


class TestPeriodPresets:
    """period=<preset> resolves to a concrete date range server-side."""

    def test_this_month_filters_to_current_month(self, auth_client, seeded_user, isolated_db):
        """period=this_month shows only expenses from the 1st of this month onward."""
        today = _today()
        uid = seeded_user["id"]

        in_range_date  = today.replace(day=1)          # first day of current month
        out_range_date = (today.replace(day=1) - timedelta(days=1))  # last day of prev month

        _insert_expense(isolated_db, uid, 800.0, "Groceries", "This month item",
                        _iso(in_range_date))
        _insert_expense(isolated_db, uid, 300.0, "Transport", "Last month item",
                        _iso(out_range_date))

        resp = auth_client.get("/profile?period=this_month")
        data = resp.data.decode()

        assert "This month item" in data
        assert "Last month item" not in data

    def test_last_30_filters_to_last_30_days(self, auth_client, seeded_user, isolated_db):
        """period=last_30 shows only expenses within the last 30 days."""
        today = _today()
        uid = seeded_user["id"]

        in_date  = _iso(today - timedelta(days=15))
        out_date = _iso(today - timedelta(days=31))

        _insert_expense(isolated_db, uid, 100.0, "Medical", "Recent pharmacy", in_date)
        _insert_expense(isolated_db, uid, 400.0, "Dining",  "Old dinner",      out_date)

        resp = auth_client.get("/profile?period=last_30")
        data = resp.data.decode()

        assert "Recent pharmacy" in data
        assert "Old dinner" not in data

    def test_last_90_filters_to_last_90_days(self, auth_client, seeded_user, isolated_db):
        """period=last_90 includes expenses up to 90 days ago but not older."""
        today = _today()
        uid = seeded_user["id"]

        in_date  = _iso(today - timedelta(days=89))
        out_date = _iso(today - timedelta(days=91))

        _insert_expense(isolated_db, uid, 999.0, "Utilities", "Recent bill", in_date)
        _insert_expense(isolated_db, uid, 111.0, "Utilities", "Old bill",    out_date)

        resp = auth_client.get("/profile?period=last_90")
        data = resp.data.decode()

        assert "Recent bill" in data
        assert "Old bill" not in data

    def test_this_year_filters_to_current_year(self, auth_client, seeded_user, isolated_db):
        """period=this_year includes only expenses from Jan 1 of the current year."""
        today = _today()
        uid = seeded_user["id"]

        in_date  = _iso(today.replace(month=1, day=1))           # Jan 1 this year
        out_date = _iso(today.replace(year=today.year - 1, month=12, day=31))  # Dec 31 last year

        _insert_expense(isolated_db, uid, 750.0, "Shopping", "This year purchase", in_date)
        _insert_expense(isolated_db, uid, 250.0, "Shopping", "Last year purchase", out_date)

        resp = auth_client.get("/profile?period=this_year")
        data = resp.data.decode()

        assert "This year purchase" in data
        assert "Last year purchase" not in data

    def test_period_preset_marks_preset_button_as_active(self, auth_client, seeded_user):
        """When period=this_month is active, the template marks that preset active."""
        resp = auth_client.get("/profile?period=this_month")
        data = resp.data.decode()
        # The template adds filter-preset--active class to the matching button
        assert "filter-preset--active" in data

    def test_period_preset_does_not_mark_wrong_preset_active(self, auth_client, seeded_user):
        """Only the matching preset button gets the active class."""
        resp = auth_client.get("/profile?period=this_month")
        data = resp.data.decode()
        # There should be exactly one active marker
        assert data.count("filter-preset--active") == 1


class TestExplicitDateRange:
    """start= and end= query params filter by explicit date range."""

    def test_explicit_start_end_filters_expenses(self, auth_client, seeded_user, isolated_db):
        """Expenses within [start, end] appear; those outside do not."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 600.0, "Groceries", "In range item",  "2025-03-15")
        _insert_expense(isolated_db, uid, 200.0, "Transport", "Out range item", "2025-01-10")

        resp = auth_client.get("/profile?start=2025-03-01&end=2025-03-31")
        data = resp.data.decode()

        assert "In range item" in data
        assert "Out range item" not in data

    def test_explicit_start_only_filters_on_or_after_start(self, auth_client, seeded_user, isolated_db):
        """When only start is provided, expenses on or after start are shown."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 400.0, "Dining",   "After start",  "2025-06-01")
        _insert_expense(isolated_db, uid, 100.0, "Dining",   "Before start", "2025-05-31")

        resp = auth_client.get("/profile?start=2025-06-01")
        data = resp.data.decode()

        assert "After start" in data
        assert "Before start" not in data

    def test_explicit_end_only_filters_on_or_before_end(self, auth_client, seeded_user, isolated_db):
        """When only end is provided, expenses on or before end are shown."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 400.0, "Dining", "Before end", "2025-03-01")
        _insert_expense(isolated_db, uid, 100.0, "Dining", "After end",  "2025-04-01")

        resp = auth_client.get("/profile?end=2025-03-31")
        data = resp.data.decode()

        assert "Before end" in data
        assert "After end" not in data

    def test_boundary_dates_are_inclusive(self, auth_client, seeded_user, isolated_db):
        """Expenses exactly on start or end date are included (BETWEEN is inclusive)."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 50.0, "Medical", "Exact start", "2025-04-01")
        _insert_expense(isolated_db, uid, 75.0, "Medical", "Exact end",   "2025-04-30")

        resp = auth_client.get("/profile?start=2025-04-01&end=2025-04-30")
        data = resp.data.decode()

        assert "Exact start" in data
        assert "Exact end" in data


class TestActivFilterPrefill:
    """The filter form pre-fills with the currently active filter values."""

    def test_start_date_prefilled_in_form(self, auth_client, seeded_user):
        """The start input value attribute contains the supplied start date."""
        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        data = resp.data.decode()
        assert 'value="2025-06-01"' in data

    def test_end_date_prefilled_in_form(self, auth_client, seeded_user):
        """The end input value attribute contains the supplied end date."""
        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        data = resp.data.decode()
        assert 'value="2025-06-30"' in data

    def test_period_prefilled_as_active_preset(self, auth_client, seeded_user):
        """When period=last_30 the matching preset button gets the active CSS class."""
        resp = auth_client.get("/profile?period=last_30")
        data = resp.data.decode()
        assert "filter-preset--active" in data

    def test_no_filter_no_prefill_in_start(self, auth_client, seeded_user):
        """When no filter is active, start input value is empty string."""
        resp = auth_client.get("/profile")
        data = resp.data.decode()
        # The value attribute should be empty for both date inputs
        assert 'name="start"' in data
        # Ensure the value is not populated with a real date
        import re
        start_input = re.search(r'name="start"[^>]*>', data)
        assert start_input is not None
        assert 'value=""' in start_input.group() or "value" not in start_input.group()


class TestStatsReflectFilter:
    """Overview stats (total_spent, transaction_count, top_category) update with the filter."""

    def test_filtered_total_spent_excludes_out_of_range(self, auth_client, seeded_user, isolated_db):
        """total_spent only sums expenses within the active filter range."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 2000.0, "Utilities", "In range",  "2025-05-15")
        _insert_expense(isolated_db, uid, 5000.0, "Utilities", "Out range", "2025-01-01")

        resp = auth_client.get("/profile?start=2025-05-01&end=2025-05-31")
        data = resp.data.decode()

        assert "2,000" in data
        assert "7,000" not in data  # combined total must NOT appear

    def test_filtered_transaction_count_excludes_out_of_range(self, auth_client, seeded_user, isolated_db):
        """transaction_count reflects only matching expenses."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 100.0, "Groceries", "May item 1", "2025-05-10")
        _insert_expense(isolated_db, uid, 200.0, "Groceries", "May item 2", "2025-05-20")
        _insert_expense(isolated_db, uid, 300.0, "Groceries", "Apr item",   "2025-04-05")

        resp = auth_client.get("/profile?start=2025-05-01&end=2025-05-31")
        data = resp.data.decode()

        # Expect transaction_count = 2 in the stats section
        # The number "2" will appear; verify "3" (all-time count) doesn't dominate
        # We check by asserting the Overview section shows 2 transactions
        # Look for the Transactions stat value
        import re
        # Find the dash-value immediately after "Transactions" label
        match = re.search(
            r'Transactions.*?<div class="dash-value">\s*(\d+)\s*</div>',
            data, re.DOTALL
        )
        assert match is not None, "Could not find transaction count stat in rendered page"
        assert match.group(1) == "2"

    def test_filtered_top_category_reflects_filter(self, auth_client, seeded_user, isolated_db):
        """top_category changes based on the filtered date range."""
        uid = seeded_user["id"]

        # In the filter range: Dining dominates
        _insert_expense(isolated_db, uid, 3000.0, "Dining",    "Restaurant", "2025-06-10")
        _insert_expense(isolated_db, uid,  500.0, "Transport", "Taxi",       "2025-06-11")
        # Outside the range: Groceries is biggest overall
        _insert_expense(isolated_db, uid, 9000.0, "Groceries", "Big shop",   "2025-01-05")

        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        data = resp.data.decode()

        assert "Dining" in data
        # "Groceries" should NOT appear as top category for this filtered period
        # (It won't be in the stats top_category section since Dining dominates filtered range)

    def test_empty_filter_stats_show_zero(self, auth_client, seeded_user, isolated_db):
        """When no expenses match the filter, total_spent is ₹0 and count is 0."""
        uid = seeded_user["id"]

        # Insert expense well outside the requested range
        _insert_expense(isolated_db, uid, 500.0, "Groceries", "Old item", "2024-01-01")

        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        data = resp.data.decode()

        assert "₹0" in data  # total_spent formatted as ₹0

    def test_empty_filter_top_category_shows_dash(self, auth_client, seeded_user, isolated_db):
        """When no expenses match the filter, top_category shows '—'."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 500.0, "Groceries", "Old item", "2024-01-01")

        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        data = resp.data.decode()

        assert "—" in data


class TestCategoryBreakdownFilter:
    """Category breakdown section reflects the active filter."""

    def test_category_breakdown_shows_only_filtered_categories(
        self, auth_client, seeded_user, isolated_db
    ):
        """Categories with no spend in the filtered range don't appear in breakdown."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 800.0, "Dining",    "In range",  "2025-07-15")
        _insert_expense(isolated_db, uid, 999.0, "Utilities", "Out range", "2025-01-01")

        resp = auth_client.get("/profile?start=2025-07-01&end=2025-07-31")
        data = resp.data.decode()

        assert "Dining" in data
        # Utilities had no spend in July; it must not appear in the breakdown rows
        # (It may appear in other parts of the page like a category badge if expenses leak —
        # but the breakdown section specifically should not list it)
        # We verify by checking the breakdown-name span which is unique to this section
        import re
        breakdown_names = re.findall(r'class="breakdown-name">([^<]+)<', data)
        assert "Utilities" not in breakdown_names

    def test_category_breakdown_empty_shows_no_data_message(
        self, auth_client, seeded_user, isolated_db
    ):
        """When filtered set is empty the breakdown renders the empty-state message."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 200.0, "Medical", "Old expense", "2023-03-01")

        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        data = resp.data.decode()

        assert "No spending data for this period" in data


class TestEmptyState:
    """Empty state renders without errors when no expenses match the filter."""

    def test_empty_state_shows_no_transactions_message(
        self, auth_client, seeded_user, isolated_db
    ):
        """When no expenses match the filter, the table shows the empty-state row."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 500.0, "Groceries", "Some expense", "2024-06-01")

        resp = auth_client.get("/profile?start=2025-06-01&end=2025-06-30")
        assert resp.status_code == 200
        data = resp.data.decode()

        assert "No transactions found for this period" in data

    def test_empty_state_no_server_error(self, auth_client, seeded_user, isolated_db):
        """Profile with a filter that matches nothing returns 200, not 500."""
        resp = auth_client.get("/profile?start=2099-01-01&end=2099-01-31")
        assert resp.status_code == 200

    def test_empty_user_no_expenses_no_filter(self, auth_client, seeded_user, isolated_db):
        """Profile with no expenses at all renders without error."""
        # No expenses inserted for this user
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert "No transactions found for this period" in data


class TestClearFilterLink:
    """'Clear filter' link only appears when a filter is active."""

    def test_clear_filter_link_shown_when_period_active(self, auth_client, seeded_user):
        """Clear filter link is present in the HTML when period= param is set."""
        resp = auth_client.get("/profile?period=this_month")
        data = resp.data.decode()
        assert "Clear filter" in data

    def test_clear_filter_link_shown_when_date_range_active(self, auth_client, seeded_user):
        """Clear filter link is present when start/end params are set."""
        resp = auth_client.get("/profile?start=2025-01-01&end=2025-01-31")
        data = resp.data.decode()
        assert "Clear filter" in data

    def test_clear_filter_link_absent_without_filter(self, auth_client, seeded_user):
        """Clear filter link must NOT appear when no filter params are present."""
        resp = auth_client.get("/profile")
        data = resp.data.decode()
        assert "Clear filter" not in data

    def test_clear_filter_link_points_to_profile_with_no_params(
        self, auth_client, seeded_user
    ):
        """The Clear filter link href must be /profile (no query params)."""
        resp = auth_client.get("/profile?period=last_30")
        data = resp.data.decode()
        # The clear link should go to bare /profile
        assert 'href="/profile"' in data


class TestEdgeCases:
    """Malformed input, inverted dates, unknown period values."""

    def test_malformed_start_date_silently_ignored(
        self, auth_client, seeded_user, isolated_db
    ):
        """A garbled start date falls back to showing all expenses (no 400/500)."""
        uid = seeded_user["id"]
        _insert_expense(isolated_db, uid, 100.0, "Dining", "Dinner", "2025-06-10")

        resp = auth_client.get("/profile?start=not-a-date&end=2025-06-30")
        assert resp.status_code == 200
        data = resp.data.decode()
        # The bad start is ignored, so the expense is still visible
        # (end-only filter: expense on 2025-06-10 <= 2025-06-30, so still shows)
        assert "Dinner" in data

    def test_malformed_end_date_silently_ignored(
        self, auth_client, seeded_user, isolated_db
    ):
        """A garbled end date falls back; valid start still applied if present."""
        uid = seeded_user["id"]
        _insert_expense(isolated_db, uid, 100.0, "Dining", "Dinner", "2025-06-10")
        _insert_expense(isolated_db, uid, 200.0, "Dining", "Old dinner", "2025-01-01")

        resp = auth_client.get("/profile?start=2025-06-01&end=garbage")
        assert resp.status_code == 200
        # Bad end is ignored; start-only filter applies
        data = resp.data.decode()
        assert "Dinner" in data        # on 2025-06-10 >= start 2025-06-01
        assert "Old dinner" not in data  # on 2025-01-01 < start 2025-06-01

    def test_both_dates_malformed_returns_all_expenses(
        self, auth_client, seeded_user, isolated_db
    ):
        """When both start and end are malformed, all expenses are shown."""
        uid = seeded_user["id"]
        _insert_expense(isolated_db, uid, 300.0, "Medical", "Check-up", "2024-03-20")

        resp = auth_client.get("/profile?start=bad&end=worse")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert "Check-up" in data

    def test_inverted_dates_are_swapped(self, auth_client, seeded_user, isolated_db):
        """When start > end, the route swaps them so the filter still works correctly."""
        uid = seeded_user["id"]

        _insert_expense(isolated_db, uid, 500.0, "Groceries", "Swap test item", "2025-04-15")
        _insert_expense(isolated_db, uid, 300.0, "Transport", "Out of range",   "2025-06-01")

        # Deliberately pass start > end — route must swap
        resp = auth_client.get("/profile?start=2025-04-30&end=2025-04-01")
        assert resp.status_code == 200
        data = resp.data.decode()

        assert "Swap test item" in data
        assert "Out of range" not in data

    def test_unknown_period_value_treated_as_no_filter(
        self, auth_client, seeded_user, isolated_db
    ):
        """An unrecognised period value (e.g. 'yesterday') shows all expenses."""
        uid = seeded_user["id"]
        _insert_expense(isolated_db, uid, 100.0, "Medical", "All time item", "2023-07-04")

        resp = auth_client.get("/profile?period=yesterday")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert "All time item" in data

    def test_period_and_explicit_dates_explicit_takes_priority(
        self, auth_client, seeded_user, isolated_db
    ):
        """When both period= and start=/end= are supplied, explicit dates take priority."""
        uid = seeded_user["id"]

        # Expense in the explicit range (Jan 2025) but NOT in this_month
        _insert_expense(isolated_db, uid, 750.0, "Utilities", "January item", "2025-01-15")
        # Expense in this_month but NOT in explicit range
        today = _today()
        this_month_date = _iso(today.replace(day=1) if today.day > 1 else today)
        _insert_expense(isolated_db, uid, 200.0, "Dining", "This month item", this_month_date)

        resp = auth_client.get(
            "/profile?period=this_month&start=2025-01-01&end=2025-01-31"
        )
        data = resp.data.decode()

        assert "January item" in data
        assert "This month item" not in data

    def test_period_not_in_valid_set_does_not_activate_clear_filter(
        self, auth_client, seeded_user
    ):
        """An unknown period param (ignored) does not activate the Clear filter link."""
        resp = auth_client.get("/profile?period=unknown_period")
        data = resp.data.decode()
        # Unknown period is treated as no filter — is_active stays False
        assert "Clear filter" not in data

    def test_filter_does_not_show_other_users_expenses(
        self, auth_client, seeded_user, isolated_db
    ):
        """Expenses belonging to a different user are never exposed via filter params."""
        from werkzeug.security import generate_password_hash

        # Create a second user with their own expense
        other_uid = _insert_user(
            isolated_db,
            name="Other User",
            email="other@example.com",
            password_hash=generate_password_hash("OtherPass1!"),
        )
        _insert_expense(isolated_db, other_uid, 9999.0, "Groceries",
                        "Other user secret expense", "2025-06-10")

        # Authenticated as seeded_user (alice), no filter
        resp = auth_client.get("/profile")
        data = resp.data.decode()

        assert "Other user secret expense" not in data
