from flask import Flask, render_template, redirect, url_for, session, request, send_from_directory, abort
from dotenv import load_dotenv
import os
from routes.auth_routes import auth_bp
from routes.review_routes import review_bp
from routes.api_dashboard import api_bp  
from routes.place_routes import place_bp  
from routes.trends_routes import trends_bp
from routes.event_routes import event_bp
from routes.photo_proxy import photo_bp


load_dotenv()

app = Flask(__name__)
app.secret_key = "tourzen_secret_key"

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(review_bp)
app.register_blueprint(api_bp)
app.register_blueprint(place_bp)
app.register_blueprint(trends_bp)
app.register_blueprint(event_bp)
app.register_blueprint(photo_bp)


# Home route
@app.route("/home")
def home_page():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))
    return render_template("home.html", username=session["user"])

# About Page
@app.route("/about")
def about_page():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))
    return render_template("about.html", username=session["user"])

# Trends Page
@app.route("/trends")
def trends_page():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))
    return render_template("trends.html", username=session["user"])

# Redirect first page to home AFTER login
@app.route("/")
def home():
    session.clear()
    return redirect(url_for("auth_bp.login"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))
    return render_template("dashboard.html", username=session["user"])

@app.route("/proxy_image")
def proxy_image():
    filename = request.args.get("file")
    if not filename:
        abort(404)
    return send_from_directory("local_icons", filename)


if __name__ == "__main__":
    app.run(debug=True)
