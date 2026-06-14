from datetime import datetime
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

    raw_stats = get_expense_stats(session["user_id"])
    stats = {
        "total_spent": "₹{:,.0f}".format(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category": raw_stats["top_category"] if raw_stats["top_category"] else "—",
    }

    expenses = get_expenses_by_user(session["user_id"])

    categories = get_category_breakdown(session["user_id"])
    return render_template("profile.html", user=user, stats=stats,
                           expenses=expenses, categories=categories)


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
