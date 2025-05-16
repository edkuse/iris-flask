from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .helpers import API_URL, api_request_with_refresh
import requests

bp = Blueprint('main', __name__, url_prefix='/')


@bp.route("/")
def index():
    if "token" in session:
        return redirect(url_for("standup.dashboard"))
    return render_template("index.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Authenticate with the API
        response = requests.post(
            f"{API_URL}/token",
            data={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            session["token"] = token_data["access_token"]
            if "refresh_token" in token_data:
                session["refresh_token"] = token_data["refresh_token"]
            
            # Get user info
            user_response = api_request_with_refresh("get", "/users/me/", token=session["token"])
            if user_response.status_code == 200:
                user_data = user_response.json()
                session["user_id"] = user_data["id"]
                session["username"] = user_data["username"]
                session["user_role"] = user_data["role"]
                
                flash(f"Welcome back, {user_data['username']}!", "success")
                return redirect(url_for("standup.dashboard"))
        
        flash("Invalid username or password", "error")
    
    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html")
        
        # Register with the API
        response = api_request_with_refresh(
            "post",
            "/users/",
            data={
                "email": email,
                "username": username,
                "password": password,
                "role": "developer"  # Default role for new users
            }
        )
        
        if response.status_code == 200:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("main.login"))
        else:
            error_data = response.json()
            flash(f"Registration failed: {error_data.get('detail', 'Unknown error')}", "error")
    
    return render_template("register.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("main.index"))
