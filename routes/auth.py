from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt

from database import db
from models.user import User
from models.tracking import StudentLoginLog, CompanyTable, AdminTable

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Verified company IDs — companies must provide one of these to register
VERIFIED_COMPANY_IDS = [
    "CMP001", "CMP002", "CMP003", "CMP004", "CMP005",
    "CMP006", "CMP007", "CMP008", "CMP009", "CMP010",
    "CMP011", "CMP012", "CMP013", "CMP014", "CMP015",
    "CMP016", "CMP017", "CMP018", "CMP019", "CMP020",
]


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return a JWT."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403

    # Explicit tracker for student logins as requested
    if user.role == "student":
        login_log = StudentLoginLog(user_id=user.id, username=user.username)
        db.session.add(login_log)
        db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    return jsonify({"access_token": token, "role": user.role, "username": user.username}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return current user info from the JWT."""
    claims = get_jwt()
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


@auth_bp.route("/register/company", methods=["POST"])
def register_company():
    """Register a new company account. Requires a verified company ID."""
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id", "").strip().upper()
    company_name = data.get("company_name", "").strip()
    password = data.get("password", "")

    if not company_id or not company_name or not password:
        return jsonify({"error": "company_id, company_name, and password are required"}), 400

    # Verify company ID
    if company_id not in VERIFIED_COMPANY_IDS:
        return jsonify({"error": "Invalid or unverified Company ID. Contact the placement office."}), 403

    # Check if company_id already used
    if User.query.filter_by(email=f"{company_id.lower()}@company.placement.edu").first():
        return jsonify({"error": "This Company ID has already been registered"}), 409

    # Check if username (company_name) taken
    if User.query.filter_by(username=company_name).first():
        return jsonify({"error": "Company name already taken as username"}), 409

    user = User(
        username=company_name,
        email=f"{company_id.lower()}@company.placement.edu",
        role="company",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush() # flush to get user.id before committing next table

    company_entry = CompanyTable(user_id=user.id, company_name=company_name, company_id=company_id)
    db.session.add(company_entry)
    
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    return jsonify({
        "message": "Company registered successfully",
        "access_token": token,
        "role": user.role,
        "username": user.username,
    }), 201


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout_failsafe():
    """Fail-safe logout route."""
    return jsonify({"message": "Logged out"}), 200

@auth_bp.route("/company-ids", methods=["GET"])
def get_company_ids():
    """Return list of valid company IDs (public endpoint for UI validation hints)."""
    return jsonify({"company_ids": VERIFIED_COMPANY_IDS}), 200
