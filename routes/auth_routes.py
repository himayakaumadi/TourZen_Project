import re
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from firebase_config import firebase_db as db

auth_bp = Blueprint('auth_bp', __name__)

def valid_password(password):
    if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[@$!%*?&^#]", password):
        return "Password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters."
    return None

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match!", username=username, email=email)

        pw_error = valid_password(password)
        if pw_error:
            return render_template("signup.html", error=pw_error, username=username, email=email)

        users = db.reference("users").get() or {}
        for uid, udata in users.items():
            if udata["username"] == username or udata["email"] == email:
                return render_template("signup.html", error="User already exists!", username=username, email=email)

        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        db.reference("users").push({"username": username, "email": email, "password": hashed_pw})
        return redirect(url_for("auth_bp.login"))

    return render_template("signup.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = db.reference("users").get() or {}
        for uid, udata in users.items():
            if udata["username"] == username and check_password_hash(udata["password"], password):
                session["user"] = username
                return redirect(url_for("home_page"))

        return render_template("login.html", error="Invalid username or password!")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("auth_bp.login"))
