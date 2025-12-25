import os
import sqlite3
from datetime import datetime, date
from functools import wraps
import re


from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

from werkzeug.security import generate_password_hash, check_password_hash
from modules.email_utils import send_email

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "farhan-secret-key"
app.config["DATABASE"] = os.path.join(app.root_path, "database.db")

# -----------------------------------------------------------------------------
# Database helper
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return user

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login first")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
def is_strong_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[^A-Za-z0-9]", password)
    )

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", user=current_user())

# ---------------- AUTH ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            flash("Email already exists")
            conn.close()
            return redirect(url_for("signup"))

        conn.execute(
            "INSERT INTO users (name,email,password_hash,created_at) VALUES (?,?,?,?)",
            (name, email, generate_password_hash(password), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        flash("Account created")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]   # ✅ THIS LINE
    return redirect(url_for("index"))


        flash("Invalid credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------- BIKE RENTAL ----------------
@app.route("/bike-rental")
@login_required
def bike_rental():
    conn = get_db()
    bikes = conn.execute("SELECT * FROM bikes").fetchall()
    conn.close()
    return render_template("bike_home.html", bikes=bikes)

@app.route("/bike-rental/<int:bike_id>", methods=["GET", "POST"])
@login_required
def bike_detail(bike_id):
    conn = get_db()
    bike = conn.execute("SELECT * FROM bikes WHERE id=?", (bike_id,)).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        start = request.form["start_date"]
        end = request.form["end_date"]

        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        total = days * bike["price_per_day"]

        conn.execute("""
            INSERT INTO bike_bookings
            (bike_id, customer_name, email, phone, start_date, end_date, total_price, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (bike_id, name, email, phone, start, end, total, datetime.now().isoformat()))
        conn.commit()
        booking_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return redirect(url_for("bike_booking_success", booking_id=booking_id))

    conn.close()
    return render_template("bike_detail.html", bike=bike)

@app.route("/bike-booking/<int:booking_id>")
@login_required
def bike_booking_success(booking_id):
    conn = get_db()
    booking = conn.execute("""
        SELECT b.name, bk.*
        FROM bike_bookings bk
        JOIN bikes b ON b.id = bk.bike_id
        WHERE bk.id=?
    """, (booking_id,)).fetchone()
    conn.close()
    return render_template("bike_booking_success.html", booking=booking)

# ---------------- PET SHOP ----------------
@app.route("/petshop")
@login_required
def pet_home():
    conn = get_db()
    products = conn.execute("SELECT * FROM pet_products").fetchall()
    conn.close()
    return render_template("pet_home.html", products=products)

@app.route("/petshop/cart")
@login_required
def pet_cart():
    return render_template("pet_cart.html")

@app.route("/petshop/checkout", methods=["GET", "POST"])
@login_required
def pet_checkout():
    if request.method == "POST":
        return redirect(url_for("pet_checkout_success"))
    return render_template("pet_checkout.html")

@app.route("/petshop/success")
@login_required
def pet_checkout_success():
    return render_template("pet_checkout_success.html")

# ---------------- DATA HUB ----------------
@app.route("/datahub", methods=["GET", "POST"])
@login_required
def datahub():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO datahub_records (title,content,created_at) VALUES (?,?,?)",
            (request.form["title"], request.form["content"], datetime.now().isoformat())
        )
        conn.commit()

    records = conn.execute("SELECT * FROM datahub_records").fetchall()
    conn.close()
    return render_template("datahub.html", records=records)

# ---------------- CONTACT ----------------
@app.route("/contact", methods=["POST"])
def contact():
    flash("Message sent successfully")
    return redirect(url_for("index") + "#contact")

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
