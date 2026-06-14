from flask import Flask, render_template, request, redirect, url_for, session
from database.db import init_db, seed_db, get_user_by_email, create_user, check_password

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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Priya Sharma",
        "email": "priya@example.com",
        "member_since": "January 2026",
        "initials": "PS",
    }
    stats = {
        "total_spent": "₹8,900",
        "transaction_count": 6,
        "top_category": "Utilities",
    }
    expenses = [
        {"date": "06 Jun 2026", "description": "Zepto quick delivery",    "category": "Groceries", "amount": "₹1,200"},
        {"date": "05 Jun 2026", "description": "Pharmacy — paracetamol",  "category": "Medical",   "amount": "₹250"},
        {"date": "04 Jun 2026", "description": "Dinner at Hao Ming",      "category": "Dining",    "amount": "₹780"},
        {"date": "03 Jun 2026", "description": "Electricity bill — June", "category": "Utilities", "amount": "₹4,500"},
        {"date": "02 Jun 2026", "description": "Ola ride to office",      "category": "Transport", "amount": "₹320"},
        {"date": "01 Jun 2026", "description": "Big Bazaar weekly shop",  "category": "Groceries", "amount": "₹1,850"},
    ]
    categories = [
        {"name": "Utilities", "amount": "₹4,500", "pct": 51},
        {"name": "Groceries", "amount": "₹3,050", "pct": 34},
        {"name": "Dining",    "amount": "₹780",   "pct": 9},
        {"name": "Transport", "amount": "₹320",   "pct": 4},
        {"name": "Medical",   "amount": "₹250",   "pct": 3},
    ]
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
