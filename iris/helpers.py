from flask import flash, redirect, session, url_for
from functools import wraps
import os
import requests

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
