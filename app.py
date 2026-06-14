from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, abort
from database.db import (init_db, seed_db, get_user_by_email, create_user, check_password,
                         get_user_by_id, get_expense_stats, get_expenses_by_user, get_category_breakdown)

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    if get_user_by_email(email):
        return render_template("register.html", error="An account with that email already exists.")

    create_user(name, email, password)
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="All fields are required.")

    user = check_password(email, password)
    if not user:
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    raw_user = get_user_by_id(session["user_id"])
    if raw_user is None:
        abort(404)

    name_words = raw_user["name"].split()
    initials = "".join(w[0].upper() for w in name_words if w)[:2]
    created_dt = datetime.strptime(raw_user["created_at"][:10], "%Y-%m-%d")
    member_since = created_dt.strftime("%B %Y")

    user = {
        "name": raw_user["name"],
        "email": raw_user["email"],
        "member_since": member_since,
        "initials": initials,
    }

    # Resolve date filter from query string
    period    = request.args.get("period", "").strip()
    start_raw = request.args.get("start",  "").strip()
    end_raw   = request.args.get("end",    "").strip()

    today      = date.today()
    start_date = None
    end_date   = None

    VALID_PERIODS = {"this_month", "last_30", "last_90", "this_year"}

    # Explicit dates are always parsed first — they take priority over period
    try:
        if start_raw:
            datetime.strptime(start_raw, "%Y-%m-%d")
            start_date = start_raw
    except ValueError:
        pass
    try:
        if end_raw:
            datetime.strptime(end_raw, "%Y-%m-%d")
            end_date = end_raw
    except ValueError:
        pass
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    # Only apply period preset when no explicit dates were provided
    period_active = False
    if not start_date and not end_date and period in VALID_PERIODS:
        period_active = True
        if period == "this_month":
            start_date = today.replace(day=1).isoformat()
            end_date   = today.isoformat()
        elif period == "last_30":
            start_date = (today - timedelta(days=30)).isoformat()
            end_date   = today.isoformat()
        elif period == "last_90":
            start_date = (today - timedelta(days=90)).isoformat()
            end_date   = today.isoformat()
        elif period == "this_year":
            start_date = today.replace(month=1, day=1).isoformat()
            end_date   = today.isoformat()

    active_filter = {
        "period":    period if period_active else "",
        "start":     start_date or "",
        "end":       end_date   or "",
        "is_active": bool(start_date or end_date),
    }

    uid = session["user_id"]

    raw_stats = get_expense_stats(uid, start=start_date, end=end_date)
    stats = {
        "total_spent": "₹{:,.0f}".format(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category": raw_stats["top_category"] if raw_stats["top_category"] else "—",
    }

    expenses   = get_expenses_by_user(uid, start=start_date, end=end_date)
    categories = get_category_breakdown(uid, start=start_date, end=end_date)

    return render_template("profile.html", user=user, stats=stats,
                           expenses=expenses, categories=categories,
                           active_filter=active_filter)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
