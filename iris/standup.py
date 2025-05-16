from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .helpers import api_request_with_refresh, login_required, role_required
from iris import logger
import pytz

bp = Blueprint('standup', __name__, url_prefix='/standup')


@bp.route("/dashboard")
@login_required
def dashboard():
    try:
        # Get standups for the current user
        response = api_request_with_refresh("get", "/standups/", token=session["token"])
        
        if response.status_code == 200:
            standups = response.json()
            return render_template("standup/dashboard.html", standups=standups)
        
        elif response.status_code == 401:
            # Token expired or invalid, redirect to login
            flash("Your session has expired. Please log in again.", "error")
            session.clear()
            return redirect(url_for("standup.login"))
        
        else:
            # Log the error for debugging
            logger.info(f"Failed to load standups: {response.status_code} - {response.text}")
            flash("Failed to load standups. Please try again later.", "error")
            return render_template("standup/dashboard.html", standups=[])
        
    except Exception as e:
        # Log the exception for debugging
        logger.error(f"Exception in dashboard route: {str(e)}")
        flash("An error occurred while loading standups. Please try again later.", "error")
        return render_template("standup/dashboard.html", standups=[])


@bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required(["admin"])
def create():
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
            return redirect(url_for("standup.dashboard"))
        else:
            error_data = response.json()
            flash(f"Failed to create standup: {error_data.get('detail', 'Unknown error')}", "error")
    
    # Get all users for the form
    users_response = api_request_with_refresh("get", "/users/", token=session["token"])
    users = users_response.json() if users_response.status_code == 200 else []
    
    # Get all timezones
    timezones = pytz.all_timezones
    
    return render_template("standup/new_standup.html", users=users, timezones=timezones)


@bp.route("/<int:standup_id>")
@login_required
def view(standup_id):
    # Get standup details
    standup_response = api_request_with_refresh("get", f"/standups/{standup_id}", token=session["token"])
    
    if standup_response.status_code != 200:
        flash("Standup not found", "error")
        return redirect(url_for("standup.dashboard"))
    
    standup = standup_response.json()
    
    # Get sessions for this standup
    sessions_response = api_request_with_refresh("get", f"/sessions/standup/{standup_id}", token=session["token"])
    sessions = sessions_response.json() if sessions_response.status_code == 200 else []
    
    return render_template("standup/view_standup.html", standup=standup, sessions=sessions)


@bp.route("/<int:standup_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(["admin"])
def edit(standup_id):
    # Get standup details
    standup_response = api_request_with_refresh("get", f"/standups/{standup_id}", token=session["token"])
    
    if standup_response.status_code != 200:
        flash("Standup not found", "error")
        return redirect(url_for("standup.dashboard"))
    
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
            return redirect(url_for("standup.view_standup", standup_id=standup_id))
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
        "standup/edit_standup.html", 
        standup=standup, 
        users=users, 
        timezones=timezones, 
        member_ids=member_ids
    )


@bp.route("/sessions/<int:session_id>", methods=["GET", "POST"])
@login_required
def view_session(session_id):
    try:
        # Get session details
        session_response = api_request_with_refresh("get", f"/sessions/{session_id}", token=session["token"])
        
        if session_response.status_code != 200:
            flash("Failed to load session", "error")
            return redirect(url_for("standup.dashboard"))
        
        standup_session = session_response.json()
        
        # Get the standup timezone
        standup_timezone = standup_session.get('standup', {}).get('timezone', 'UTC')
        
        # Get responses for this session
        responses_response = api_request_with_refresh("get", f"/responses/session/{session_id}", token=session["token"])
        responses = responses_response.json() if responses_response.status_code == 200 else []
        
        # Check if the current user has already submitted a response
        user_has_responded = any(r["user_id"] == session.get("user_id") for r in responses)
        
        if request.method == "POST" and not user_has_responded:
            # Submit a new response
            yesterday = request.form.get("yesterday")
            today = request.form.get("today")
            blockers = request.form.get("blockers")
            
            response = api_request_with_refresh(
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
                return redirect(url_for("standup.view_session", session_id=session_id))
            else:
                flash("Failed to submit response", "error")
        
        return render_template(
            "standup/view_session.html", 
            standup_session=standup_session,
            responses=responses, 
            user_has_responded=user_has_responded,
            timezone=standup_timezone
        )
    
    except Exception as e:
        logger.error(f"Exception in view_session route: {str(e)}")
        flash(f"An error occurred while loading the session", "error")
        return redirect(url_for("standup.dashboard"))
    

@bp.route("/create_session/<int:standup_id>", methods=["POST"])
@login_required
def create_session(standup_id):
    # Get standup details to check if user is facilitator
    standup_response = api_request_with_refresh("get", f"/standups/{standup_id}", token=session["token"])
    
    if standup_response.status_code != 200:
        flash("Standup not found", "error")
        return redirect(url_for("standup.dashboard"))
    
    standup = standup_response.json()
    
    # Check if user is facilitator or admin
    if standup["facilitator_id"] != session["user_id"] and session["user_role"] != "admin":
        flash("Only the facilitator or admin can create sessions", "error")
        return redirect(url_for("standup.view_standup", standup_id=standup_id))
    
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
    
    return redirect(url_for("standup.view_standup", standup_id=standup_id))
