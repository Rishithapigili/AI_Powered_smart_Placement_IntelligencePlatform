import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import db
from models.user import User
from models.student_profile import StudentProfile
from models.placement import PlacementOpportunity, PlacementRecord
from services.employability import recalculate_and_save
from utils.decorators import role_required
from utils.file_handler import validate_and_save_file
from config import Config

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


def _get_own_profile():
    """Get the StudentProfile belonging to the current JWT user."""
    user_id = int(get_jwt_identity())
    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    return profile


# ──────────────── Profile ────────────────

@student_bp.route("/profile", methods=["GET"])
@role_required("student")
def get_profile():
    """View own profile and employability score."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found. Contact admin."}), 404
    return jsonify(profile.to_dict()), 200


@student_bp.route("/profile", methods=["PUT"])
@role_required("student")
def update_profile():
    """Edit own profile — auto-recalculates employability score."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found. Contact admin."}), 404

    data = request.get_json(silent=True) or {}

    # Update allowed fields
    string_fields = ["full_name", "department", "roll_number", "career_preferences"]
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

    int_fields = ["internship_count", "programming_skills_rating", "soft_skills_rating"]
    for f in int_fields:
        if f in data:
            try:
                setattr(profile, f, int(data[f]))
            except ValueError:
                pass

    # Auto-recalculate employability score
    recalculate_and_save(profile, db)
    db.session.commit()
    return jsonify({"message": "Profile updated", "profile": profile.to_dict()}), 200


# ──────────────── File Uploads ────────────────

@student_bp.route("/upload/resume", methods=["POST"])
@role_required("student")
def upload_resume():
    """Upload resume (PDF/DOC, max 5 MB)."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    file = request.files.get("file")
    try:
        path = validate_and_save_file(file, "resume", Config.UPLOAD_FOLDER)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    profile.resume_path = path
    db.session.commit()
    return jsonify({"message": "Resume uploaded", "path": path}), 200


@student_bp.route("/upload/photo", methods=["POST"])
@role_required("student")
def upload_photo():
    """Upload photo (JPG/PNG, max 2 MB)."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    file = request.files.get("file")
    try:
        path = validate_and_save_file(file, "photo", Config.UPLOAD_FOLDER)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    profile.photo_path = path
    db.session.commit()
    return jsonify({"message": "Photo uploaded", "path": path}), 200


@student_bp.route("/upload/document", methods=["POST"])
@role_required("student")
def upload_document():
    """Upload supporting document."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    file = request.files.get("file")
    try:
        path = validate_and_save_file(file, "document", Config.UPLOAD_FOLDER)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Append to documents list
    try:
        docs = json.loads(profile.documents) if profile.documents else []
    except (json.JSONDecodeError, TypeError):
        docs = []
    docs.append(path)
    profile.documents = json.dumps(docs)
    db.session.commit()
    return jsonify({"message": "Document uploaded", "path": path, "documents": docs}), 200


# ──────────────── Placements ────────────────

@student_bp.route("/placements", methods=["GET"])
@role_required("student")
def view_placements():
    """View available placement opportunities."""
    profile = _get_own_profile()
    applied_dict = {}
    if profile:
        records = PlacementRecord.query.filter_by(student_id=profile.id).all()
        applied_dict = {r.opportunity_id: r.status for r in records}

    opps = PlacementOpportunity.query.order_by(PlacementOpportunity.created_at.desc()).all()
    results = []
    for o in opps:
        o_dict = o.to_dict()
        o_dict["applied_status"] = applied_dict.get(o.id)
        results.append(o_dict)

    return jsonify(results), 200


@student_bp.route("/placements/<int:opp_id>/apply", methods=["POST"])
@role_required("student")
def apply_placement(opp_id):
    """Apply to a placement opportunity."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    opp = PlacementOpportunity.query.get(opp_id)
    if not opp:
        return jsonify({"error": "Opportunity not found"}), 404

    # Check if already applied
    existing = PlacementRecord.query.filter_by(student_id=profile.id, opportunity_id=opp_id).first()
    if existing:
        return jsonify({"error": "Already applied to this opportunity"}), 409

    record = PlacementRecord(student_id=profile.id, opportunity_id=opp_id)
    db.session.add(record)
    db.session.commit()
    return jsonify({"message": "Application submitted", "record": record.to_dict()}), 201


@student_bp.route("/status", methods=["GET"])
@role_required("student")
def placement_status():
    """View own placement records/status."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    records = PlacementRecord.query.filter_by(student_id=profile.id).order_by(PlacementRecord.applied_at.desc()).all()
    return jsonify({
        "placement_status": profile.placement_status,
        "placement_company": profile.placement_company,
        "applications": [r.to_dict() for r in records],
    }), 200

@student_bp.route("/applications/<int:record_id>/flow", methods=["GET"])
@role_required("student")
def application_flow(record_id):
    """View the full explicit status progression of an application."""
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    record = PlacementRecord.query.get(record_id)
    if not record or record.student_id != profile.id:
        return jsonify({"error": "Application not found"}), 404
        
    current_status = record.status.lower()
    
    # Generate flow stages
    stages = [
        {"stage": "Applied", "completed": True, "active": current_status == "applied"}
    ]
    
    # Logic for shortlisted
    is_shortlisted_or_beyond = current_status in ["shortlisted", "selected", "rejected"]
    stages.append({
        "stage": "Shortlisted", 
        "completed": is_shortlisted_or_beyond, 
        "active": current_status == "shortlisted"
    })
    
    # Logic for final state
    final_stage = {
        "stage": "Decision Pending", "completed": False, "active": False
    }
    if current_status == "selected":
        final_stage = {"stage": "Selected", "completed": True, "active": True}
    elif current_status == "rejected":
        final_stage = {"stage": "Rejected", "completed": True, "active": True}
        
    stages.append(final_stage)

    return jsonify({
        "application": record.to_dict(),
        "flow": stages
    }), 200

# ──────────────── Evaluation Graphs ────────────────
import os
from flask import send_file
from utils.graph import generate_cgpa_comparison, generate_employability_graph

@student_bp.route("/evaluation/cgpa", methods=["GET"])
@role_required("student")
def get_cgpa_graph():
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    # Calculate dept average CGPA
    dept_students = StudentProfile.query.filter_by(department=profile.department, is_verified=True).all()
    if dept_students:
        dept_avg = sum(s.cgpa for s in dept_students if s.cgpa) / len(dept_students)
    else:
        dept_avg = profile.cgpa or 0

    photo_path = profile.photo_path if profile.photo_path and os.path.exists(profile.photo_path) else None
    
    output_filename = os.path.join(Config.UPLOAD_FOLDER, f"cgpa_{profile.user_id}.png")
    generate_cgpa_comparison(profile.cgpa or 0, dept_avg, photo_path, output_filename)
    
    return send_file(output_filename, mimetype='image/png')

@student_bp.route("/evaluation/employability", methods=["GET"])
@role_required("student")
def get_employability_graph():
    profile = _get_own_profile()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Calculate dept average employability
    dept_students = StudentProfile.query.filter_by(department=profile.department, is_verified=True).all()
    if dept_students:
        dept_avg = sum(s.employability_score for s in dept_students if s.employability_score) / len(dept_students)
    else:
        dept_avg = profile.employability_score or 0

    photo_path = profile.photo_path if profile.photo_path and os.path.exists(profile.photo_path) else None
    
    output_filename = os.path.join(Config.UPLOAD_FOLDER, f"emp_{profile.user_id}.png")
    generate_employability_graph(profile.employability_score or 0, dept_avg, photo_path, output_filename)
    
    return send_file(output_filename, mimetype='image/png')
