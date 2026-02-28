from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def role_required(*roles):
    """Decorator that restricts access to users with the specified role(s).

    Usage:
        @role_required("admin")
        @role_required("admin", "student")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "")
            if user_role not in roles:
                return jsonify({"error": "Forbidden – insufficient privileges"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
