import json
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import request

# Global thread pool for non-blocking DB writes
_log_executor = ThreadPoolExecutor(max_workers=2)

def _save_log_to_db(app, log_data):
    """
    Background worker function that runs inside the Flask app context.
    """
    with app.app_context():
        try:
            from database import db
            from models.tracking import ActivityLog
            
            log_entry = ActivityLog(**log_data)
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            # Fallback to standard error output if DB insert fails asynchronously
            print(f"[Logging Service Error] Could not save activity log: {e}")
            print(traceback.format_exc())

def start_async_log(app, log_data):
    """
    Dispatches the log insertion to a background thread to prevent blocking main UI request times.
    """
    _log_executor.submit(_save_log_to_db, app, log_data)

def setup_logging_middleware(app):
    """
    Hooks into Flask's after_request to automatically analyze and log specific actions based on routing.
    """
    @app.after_request
    def log_user_activity(response):
        # We only care about specific routes that indicate user 'actions'
        path = request.path
        method = request.method
        
        # Default ignore rules for static files and standard un-authenticated views
        if path.startswith("/static/") or method == "OPTIONS":
            return response
            
        action_type = None
        description = None
        
        # 1. Login/Authentication Actions
        if path == "/api/auth/login" and method == "POST":
            action_type = "LOGIN"
            description = "User authenticated successfully" if response.status_code == 200 else "Failed login attempt"
            
        # 2. Student Internship Applications
        elif path.startswith("/api/student/placements/") and path.endswith("/apply") and method == "POST":
            action_type = "APPLY_INTERNSHIP"
            opp_id = path.split("/")[4]
            description = f"Student applied for placement opportunity ID: {opp_id}"

        # 3. Company Status Updates
        elif path.startswith("/api/company/applications/") and path.endswith("/status") and method == "PUT":
            action_type = "STATUS_UPDATE"
            record_id = path.split("/")[4]
            description = f"Company updated application record ID: {record_id}"
            
        # 4. Profile Edits
        elif path == "/api/student/profile" and method in ["PUT", "POST"]:
            action_type = "UPDATE_PROFILE"
            description = "Student generated or updated their profile"
            
        # 5. ML Predictions
        elif path.startswith("/api/ml/predict") or path.startswith("/api/ml/recommend"):
            action_type = "MODEL_PREDICTION"
            description = "Machine learning model processing request"
            
        # 6. Admin Actions
        elif path.startswith("/api/admin/") and method in ["POST", "PUT", "DELETE"]:
            action_type = "ADMIN_ACTION"
            description = f"Admin modification request on {path}"
            
        # If no action matched, don't generate a log
        if not action_type:
            return response
        
        # Extract JWT user identity if present
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        user_id = None
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                user_id = int(identity)
        except:
            pass
            
        # Attempt to grab JSON payload
        payload_data = None
        if request.is_json:
            try:
                # Do not log raw passwords
                raw_json = request.get_json(silent=True)
                if raw_json:
                    clean_json = dict(raw_json)
                    if "password" in clean_json:
                        clean_json["password"] = "***"
                    payload_data = clean_json
            except:
                pass

        # Construct payload and dispatch
        log_data = {
            "user_id": user_id,
            "action_type": action_type,
            "description": description,
            "endpoint": path,
            "method": method,
            "payload": payload_data,
            "status_code": response.status_code,
            "ip_address": request.remote_addr or "127.0.0.1",
            "timestamp": datetime.utcnow()
        }
        
        start_async_log(app, log_data)
        return response
