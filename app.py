from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
import logging
import pytz

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# API URL from environment variable or default for development
API_URL = os.getenv("API_URL")

# Helper function to make authenticated API requests
def api_request(method, endpoint, data=None, token=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method.lower() == "post":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.lower() == "put":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response
    
    except requests.exceptions.ConnectionError:
        # Create a mock response for connection errors
        mock_response = requests.Response()
        mock_response.status_code = 503
        mock_response._content = b'{"detail": "Service unavailable. Could not connect to the API."}'
        return mock_response
    
    except requests.exceptions.Timeout:
        # Create a mock response for timeouts
        mock_response = requests.Response()
        mock_response.status_code = 504
        mock_response._content = b'{"detail": "Request timed out. The API is taking too long to respond."}'
        return mock_response
    
    except Exception as e:
        # Create a mock response for other exceptions
        mock_response = requests.Response()
        mock_response.status_code = 500
        mock_response._content = f'{{"detail": "An error occurred: {str(e)}"}}'.encode('utf-8')
        return mock_response


def refresh_token():
    """Attempt to refresh the access token"""
    if "refresh_token" not in session:
        return False
    
    try:
        response = requests.post(
            f"{API_URL}/token/refresh",
            data={"refresh_token": session["refresh_token"]}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            session["token"] = token_data["access_token"]
            if "refresh_token" in token_data:
                session["refresh_token"] = token_data["refresh_token"]
            return True
        
    except:
        pass
    
    return False


def api_request_with_refresh(method, endpoint, data=None, token=None, params=None):
    """Make API request with token refresh on 401"""
    response = api_request(method, endpoint, data, token, params)
    
    # If unauthorized and token refresh is successful, retry the request
    if response.status_code == 401 and refresh_token():
        return api_request(method, endpoint, data, session["token"], params)
    
    return response


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "token" not in session:
            flash("Please log in to access this page", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Role required decorator
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "token" not in session or "user_role" not in session:
                flash("Please log in to access this page", "error")
                return redirect(url_for("login"))
            
            if session["user_role"] not in roles:
                flash("You don't have permission to access this page", "error")
                return redirect(url_for("dashboard"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d %I:%M %p'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value


@app.template_filter('format_time')
def format_time(value, format='%I:%M %p'):
    if isinstance(value, str):
        try:
            time_object = datetime.strptime(value, '%H:%M:00').time()
            return time_object.strftime(format)

        except ValueError:
            pass
        
    return value


@app.template_filter('convert_timezone')
def convert_timezone(value, source_tz='UTC', target_tz='UTC', format='%Y-%m-%d %I:%M %p'):
    """Convert datetime from one timezone to another and format it"""
    if isinstance(value, str):
        try:
            # Parse the string to datetime, assuming it's in UTC if no timezone info
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return value
    
    if isinstance(value, datetime):
        # If the datetime has no timezone info, assume it's in source_tz
        if value.tzinfo is None:
            source_timezone = pytz.timezone(source_tz)
            value = source_timezone.localize(value)
        
        # Convert to target timezone
        target_timezone = pytz.timezone(target_tz)
        converted = value.astimezone(target_timezone)
        
        # Format the datetime
        return converted.strftime(format)
    
    return value


# Routes
@app.route("/")
def index():
    if "token" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
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
                return redirect(url_for("dashboard"))
        
        flash("Invalid username or password", "error")
    
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
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
            return redirect(url_for("login"))
        else:
            error_data = response.json()
            flash(f"Registration failed: {error_data.get('detail', 'Unknown error')}", "error")
    
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    try:
        # Get standups for the current user
        response = api_request_with_refresh("get", "/standups/", token=session["token"])
        
        if response.status_code == 200:
            standups = response.json()
            return render_template("dashboard.html", standups=standups)
        
        elif response.status_code == 401:
            # Token expired or invalid, redirect to login
            flash("Your session has expired. Please log in again.", "error")
            session.clear()
            return redirect(url_for("login"))
        
        else:
            # Log the error for debugging
            logger.info(f"Failed to load standups: {response.status_code} - {response.text}")
            flash("Failed to load standups. Please try again later.", "error")
            return render_template("dashboard.html", standups=[])
        
    except Exception as e:
        # Log the exception for debugging
        logger.error(f"Exception in dashboard route: {str(e)}")
        flash("An error occurred while loading standups. Please try again later.", "error")
        return render_template("dashboard.html", standups=[])


@app.route("/standups/new", methods=["GET", "POST"])
@login_required
@role_required(["admin"])
def new_standup():
    if request.method == "POST":
        # Get form data
        name = request.form.get("name")
        days = request.form.getlist("days")
        time_of_day = request.form.get("time_of_day")
        timezone = request.form.get("timezone")
        duration = request.form.get("duration")
        facilitator_id = request.form.get("facilitator_id")
        member_ids = request.form.getlist("member_ids")
        
        # Convert days to comma-separated string
        days_of_week = ",".join(days)
        
        # Create standup via API
        response = api_request_with_refresh(
            "post",
            "/standups/",
            data={
                "name": name,
                "days_of_week": days_of_week,
                "time_of_day": time_of_day,
                "timezone": timezone,
                "duration_minutes": int(duration or 0),
                "facilitator_id": int(facilitator_id or 0),
                "member_ids": [int(id) for id in member_ids]
            },
            token=session["token"]
        )
        
        if response.status_code == 200:
            flash("Standup created successfully", "success")
            return redirect(url_for("dashboard"))
        else:
            error_data = response.json()
            flash(f"Failed to create standup: {error_data.get('detail', 'Unknown error')}", "error")
    
    # Get all users for the form
    users_response = api_request_with_refresh("get", "/users/", token=session["token"])
    users = users_response.json() if users_response.status_code == 200 else []
    
    # Get all timezones
    timezones = pytz.all_timezones
    
    return render_template("new_standup.html", users=users, timezones=timezones)

@app.route("/standups/<int:standup_id>")
@login_required
def view_standup(standup_id):
    # Get standup details
    standup_response = api_request_with_refresh("get", f"/standups/{standup_id}", token=session["token"])
    
    if standup_response.status_code != 200:
        flash("Standup not found", "error")
        return redirect(url_for("dashboard"))
    
    standup = standup_response.json()
    
    # Get sessions for this standup
    sessions_response = api_request_with_refresh("get", f"/sessions/standup/{standup_id}", token=session["token"])
    sessions = sessions_response.json() if sessions_response.status_code == 200 else []
    
    return render_template("view_standup.html", standup=standup, sessions=sessions)


@app.route("/standups/<int:standup_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(["admin"])
def edit_standup(standup_id):
    # Get standup details
    standup_response = api_request_with_refresh("get", f"/standups/{standup_id}", token=session["token"])
    
    if standup_response.status_code != 200:
        flash("Standup not found", "error")
        return redirect(url_for("dashboard"))
    
    standup = standup_response.json()
    
    if request.method == "POST":
        # Get form data
        name = request.form.get("name")
        days = request.form.getlist("days")
        time_of_day = request.form.get("time_of_day")
        timezone = request.form.get("timezone")
        duration = request.form.get("duration")
        facilitator_id = request.form.get("facilitator_id")
        member_ids = request.form.getlist("member_ids")
        
        # Convert days to comma-separated string
        days_of_week = ",".join(days)
        
        # Update standup via API
        response = api_request_with_refresh(
            "put",
            f"/standups/{standup_id}",
            data={
                "name": name,
                "days_of_week": days_of_week,
                "time_of_day": time_of_day,
                "timezone": timezone,
                "duration_minutes": int(duration),
                "facilitator_id": int(facilitator_id),
                "member_ids": [int(id) for id in member_ids]
            },
            token=session["token"]
        )
        
        if response.status_code == 200:
            flash("Standup updated successfully", "success")
            return redirect(url_for("view_standup", standup_id=standup_id))
        else:
            error_data = response.json()
            flash(f"Failed to update standup: {error_data.get('detail', 'Unknown error')}", "error")
    
    # Get all users for the form
    users_response = api_request_with_refresh("get", "/users/", token=session["token"])
    users = users_response.json() if users_response.status_code == 200 else []
    
    # Get all timezones
    timezones = pytz.all_timezones
    
    # Get current standup members
    member_ids = [member["id"] for member in standup.get("members", [])]
    
    return render_template(
        "edit_standup.html", 
        standup=standup, 
        users=users, 
        timezones=timezones, 
        member_ids=member_ids
    )


@app.route("/sessions/<int:session_id>", methods=["GET", "POST"])
@login_required
def view_session(session_id):
    try:
        # Get session details
        session_response = api_request("get", f"/sessions/{session_id}", token=session["token"])
        
        if session_response.status_code != 200:
            flash("Failed to load session", "error")
            return redirect(url_for("dashboard"))
        
        standup_session = session_response.json()
        
        # Get the standup timezone
        standup_timezone = standup_session.get('standup', {}).get('timezone', 'UTC')
        
        # Get responses for this session
        responses_response = api_request("get", f"/responses/session/{session_id}", token=session["token"])
        responses = responses_response.json() if responses_response.status_code == 200 else []
        
        # Check if the current user has already submitted a response
        user_has_responded = any(r["user_id"] == session.get("user_id") for r in responses)
        
        if request.method == "POST" and not user_has_responded:
            # Submit a new response
            yesterday = request.form.get("yesterday")
            today = request.form.get("today")
            blockers = request.form.get("blockers")
            
            response = api_request(
                "post",
                "/responses/",
                data={
                    "session_id": session_id,
                    "yesterday": yesterday,
                    "today": today,
                    "blockers": blockers
                },
                token=session["token"]
            )
            
            if response.status_code == 200:
                flash("Response submitted successfully", "success")
                return redirect(url_for("view_session", session_id=session_id))
            else:
                flash("Failed to submit response", "error")
        
        return render_template(
            "view_session.html", 
            standup_session=standup_session,
            responses=responses, 
            user_has_responded=user_has_responded,
            timezone=standup_timezone
        )
    
    except Exception as e:
        logger.error(f"Exception in view_session route: {str(e)}")
        flash(f"An error occurred while loading the session", "error")
        return redirect(url_for("dashboard"))
    

@app.route("/create_session/<int:standup_id>", methods=["POST"])
@login_required
def create_session(standup_id):
    # Get standup details to check if user is facilitator
    standup_response = api_request_with_refresh("get", f"/standups/{standup_id}", token=session["token"])
    
    if standup_response.status_code != 200:
        flash("Standup not found", "error")
        return redirect(url_for("dashboard"))
    
    standup = standup_response.json()
    
    # Check if user is facilitator or admin
    if standup["facilitator_id"] != session["user_id"] and session["user_role"] != "admin":
        flash("Only the facilitator or admin can create sessions", "error")
        return redirect(url_for("view_standup", standup_id=standup_id))
    
    # Create a new session
    session_date = request.form.get("session_date")
    
    response = api_request_with_refresh(
        "post",
        "/sessions/",
        data={
            "standup_id": standup_id,
            "date": session_date
        },
        token=session["token"]
    )
    
    if response.status_code == 200:
        flash("Session created successfully", "success")
    else:
        error_data = response.json()
        flash(f"Failed to create session: {error_data.get('detail', 'Unknown error')}", "error")
    
    return redirect(url_for("view_standup", standup_id=standup_id))

if __name__ == "__main__":
    app.run(debug=True)