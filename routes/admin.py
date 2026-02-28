import json
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import db
from models.user import User
from models.student_profile import StudentProfile
from models.placement import PlacementOpportunity, PlacementRecord
from services.employability import recalculate_and_save
from services.report_service import generate_csv_report, generate_pdf_report
from utils.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ──────────────── User Management ────────────────

@admin_bp.route("/users", methods=["POST"])
@role_required("admin")
def create_user():
    """Create a new student or company account."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "student")

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    if role not in ("student", "company"):
        return jsonify({"error": "Role must be 'student' or 'company'"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 409

    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    # Auto-create empty student profile
    if role == "student":
        profile = StudentProfile(user_id=user.id, full_name=data.get("full_name", username))
        db.session.add(profile)

    db.session.commit()
    return jsonify({"message": "User created", "user": user.to_dict()}), 201


@admin_bp.route("/users", methods=["GET"])
@role_required("admin")
def list_users():
    """List all users, optionally filtered by role."""
    role_filter = request.args.get("role")
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    users = query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@role_required("admin")
def edit_user(user_id):
    """Edit a user (username, email, role, is_active)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]
    if "role" in data and data["role"] in ("admin", "student", "company"):
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "password" in data and data["password"]:
        user.set_password(data["password"])

    db.session.commit()
    return jsonify({"message": "User updated", "user": user.to_dict()}), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@role_required("admin")
def delete_user(user_id):
    """Deactivate a user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.is_active = False
    db.session.commit()
    return jsonify({"message": "User deactivated"}), 200


# ──────────────── Student Management ────────────────

@admin_bp.route("/students", methods=["GET"])
@role_required("admin")
def list_students():
    """List student profiles with filters."""
    query = StudentProfile.query.join(User)
    dept = request.args.get("department")
    min_cgpa = request.args.get("min_cgpa")
    skills = request.args.get("skills")
    status = request.args.get("placement_status")
    verified = request.args.get("verified")

    if dept:
        query = query.filter(StudentProfile.department.ilike(f"%{dept}%"))
    if min_cgpa:
        query = query.filter(StudentProfile.cgpa >= float(min_cgpa))
    if skills:
        for skill in skills.split(","):
            query = query.filter(StudentProfile.skills.ilike(f"%{skill.strip()}%"))
    if status:
        query = query.filter(StudentProfile.placement_status == status)
    if verified in ("true", "1"):
        query = query.filter(StudentProfile.is_verified == True)

    profiles = query.order_by(StudentProfile.full_name).all()
    return jsonify([p.to_dict() for p in profiles]), 200


@admin_bp.route("/students/<int:profile_id>", methods=["GET"])
@role_required("admin")
def get_student(profile_id):
    """View a specific student profile."""
    profile = StudentProfile.query.get(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile.to_dict()), 200


@admin_bp.route("/students/<int:profile_id>", methods=["PUT"])
@role_required("admin")
def edit_student(profile_id):
    """Admin edits a student profile."""
    profile = StudentProfile.query.get(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    data = request.get_json(silent=True) or {}
    _update_profile_fields(profile, data)

    recalculate_and_save(profile, db)
    db.session.commit()
    return jsonify({"message": "Profile updated", "profile": profile.to_dict()}), 200


@admin_bp.route("/students/<int:profile_id>/verify", methods=["PUT"])
@role_required("admin")
def verify_student(profile_id):
    """Toggle verification status of a student profile."""
    profile = StudentProfile.query.get(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    profile.is_verified = not profile.is_verified
    db.session.commit()
    return jsonify({"message": f"Profile {'verified' if profile.is_verified else 'unverified'}", "is_verified": profile.is_verified}), 200


# ──────────────── Reports ────────────────

@admin_bp.route("/reports", methods=["GET"])
@role_required("admin")
def get_csv_report():
    """Generate CSV report of students."""
    filters = {
        "department": request.args.get("department"),
        "min_cgpa": request.args.get("min_cgpa"),
        "skills": request.args.get("skills"),
        "placement_status": request.args.get("placement_status"),
        "verified_only": request.args.get("verified_only"),
    }
    csv_data = generate_csv_report(filters)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_report.csv"},
    )


@admin_bp.route("/reports/pdf", methods=["GET"])
@role_required("admin")
def get_pdf_report():
    """Generate PDF report of students."""
    filters = {
        "department": request.args.get("department"),
        "min_cgpa": request.args.get("min_cgpa"),
        "skills": request.args.get("skills"),
        "placement_status": request.args.get("placement_status"),
        "verified_only": request.args.get("verified_only"),
    }
    pdf_data = generate_pdf_report(filters)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=student_report.pdf"},
    )


# ──────────────── Placement Opportunities ────────────────

@admin_bp.route("/placements", methods=["GET"])
@role_required("admin")
def list_placements():
    """List all placement opportunities."""
    opps = PlacementOpportunity.query.order_by(PlacementOpportunity.created_at.desc()).all()
    return jsonify([o.to_dict() for o in opps]), 200


@admin_bp.route("/placements", methods=["POST"])
@role_required("admin")
def create_placement():
    """Create a new placement opportunity."""
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "").strip()
    role_title = data.get("role_title", "").strip()

    if not company_name or not role_title:
        return jsonify({"error": "company_name and role_title are required"}), 400

    from datetime import datetime
    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.fromisoformat(data["deadline"])
        except ValueError:
            pass

    opp = PlacementOpportunity(
        company_name=company_name,
        role_title=role_title,
        package=data.get("package", ""),
        eligibility_criteria=data.get("eligibility_criteria", ""),
        min_cgpa=float(data.get("min_cgpa", 0)),
        required_skills=json.dumps(data.get("required_skills", [])),
        deadline=deadline,
        created_by=int(get_jwt_identity()),
    )
    db.session.add(opp)
    db.session.commit()
    return jsonify({"message": "Opportunity created", "opportunity": opp.to_dict()}), 201


@admin_bp.route("/placements/<int:opp_id>", methods=["PUT"])
@role_required("admin")
def edit_placement(opp_id):
    """Edit a placement opportunity."""
    opp = PlacementOpportunity.query.get(opp_id)
    if not opp:
        return jsonify({"error": "Opportunity not found"}), 404

    data = request.get_json(silent=True) or {}
    if "company_name" in data:
        opp.company_name = data["company_name"]
    if "role_title" in data:
        opp.role_title = data["role_title"]
    if "package" in data:
        opp.package = data["package"]
    if "eligibility_criteria" in data:
        opp.eligibility_criteria = data["eligibility_criteria"]
    if "min_cgpa" in data:
        opp.min_cgpa = float(data["min_cgpa"])
    if "required_skills" in data:
        opp.required_skills = json.dumps(data["required_skills"])
    if "deadline" in data:
        from datetime import datetime
        try:
            opp.deadline = datetime.fromisoformat(data["deadline"]) if data["deadline"] else None
        except ValueError:
            pass

    db.session.commit()
    return jsonify({"message": "Opportunity updated", "opportunity": opp.to_dict()}), 200


@admin_bp.route("/placements/<int:opp_id>", methods=["DELETE"])
@role_required("admin")
def delete_placement(opp_id):
    """Delete a placement opportunity."""
    opp = PlacementOpportunity.query.get(opp_id)
    if not opp:
        return jsonify({"error": "Opportunity not found"}), 404
    db.session.delete(opp)
    db.session.commit()
    return jsonify({"message": "Opportunity deleted"}), 200


@admin_bp.route("/placements/status", methods=["GET"])
@role_required("admin")
def placement_status():
    """Track all placement records."""
    records = PlacementRecord.query.order_by(PlacementRecord.applied_at.desc()).all()
    return jsonify([r.to_dict() for r in records]), 200


# ──────────────── Bulk Recalculate ────────────────

@admin_bp.route("/recalculate-scores", methods=["POST"])
@role_required("admin")
def recalculate_all_scores():
    """Recalculate employability scores for all students."""
    profiles = StudentProfile.query.all()
    count = 0
    for p in profiles:
        recalculate_and_save(p, db)
        count += 1
    db.session.commit()
    return jsonify({"message": f"Recalculated scores for {count} students"}), 200


# ──────────────── Utility ────────────────

def _update_profile_fields(profile, data):
    """Update profile fields from a dict (shared by admin & student routes)."""
    string_fields = ["full_name", "department", "roll_number", "career_preferences",
                     "placement_status", "placement_company"]
    for f in string_fields:
        if f in data:
            setattr(profile, f, data[f])

    float_fields = ["cgpa", "tenth_percentage", "twelfth_percentage"]
    for f in float_fields:
        if f in data:
            setattr(profile, f, float(data[f]))

    json_fields = ["skills", "certifications", "projects", "internships"]
    for f in json_fields:
        if f in data:
            setattr(profile, f, json.dumps(data[f]) if isinstance(data[f], list) else data[f])

    if "internship_count" in data:
        profile.internship_count = int(data["internship_count"])
