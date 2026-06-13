import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = os.path.join(os.path.dirname(__file__), "spendly.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
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


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


def check_password(email, password):
    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def create_user(name, email, password):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def seed_db():
    conn = get_db()

    conn.execute("""
        INSERT OR IGNORE INTO users (name, email, password_hash)
        VALUES ('Demo User', 'demo@spendly.app', 'demo')
    """)
    conn.commit()

    user = conn.execute("SELECT id FROM users WHERE email = 'demo@spendly.app'").fetchone()
    uid = user["id"]

    sample_expenses = [
        (uid, 1850.00, "Groceries",  "Big Bazaar weekly shop",     "2026-06-01", "UPI",         "household"),
        (uid,  320.00, "Transport",  "Ola ride to office",         "2026-06-02", "UPI",         "work,commute"),
        (uid, 4500.00, "Utilities",  "Electricity bill — June",    "2026-06-03", "Net Banking",  "bills"),
        (uid,  780.00, "Dining",     "Dinner at Hao Ming",         "2026-06-04", "Credit Card",  ""),
        (uid,  250.00, "Medical",    "Pharmacy — paracetamol",     "2026-06-05", "Cash",         "health"),
        (uid, 1200.00, "Groceries",  "Zepto quick delivery",       "2026-06-06", "UPI",         "household"),
    ]

    conn.executemany("""
        INSERT INTO expenses (user_id, amount, category, description, date, payment_method, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, sample_expenses)

    conn.commit()
    conn.close()
