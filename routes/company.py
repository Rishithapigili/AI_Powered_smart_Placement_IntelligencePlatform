from flask import Blueprint, request, jsonify

from models.student_profile import StudentProfile
from models.user import User
from models.placement import PlacementOpportunity
from utils.decorators import role_required
import json
from flask_jwt_extended import get_jwt_identity

company_bp = Blueprint("company", __name__, url_prefix="/api/company")


@company_bp.route("/students", methods=["GET"])
@role_required("company")
def browse_students():
    """Browse verified student profiles with optional filters."""
    query = StudentProfile.query.join(User).filter(
        StudentProfile.is_verified == True,
        User.is_active == True,
    )

    dept = request.args.get("department")
    min_cgpa = request.args.get("min_cgpa")
    skills = request.args.get("skills")

    if dept:
        query = query.filter(StudentProfile.department.ilike(f"%{dept}%"))
    if min_cgpa:
        query = query.filter(StudentProfile.cgpa >= float(min_cgpa))
    if skills:
        for skill in skills.split(","):
            query = query.filter(StudentProfile.skills.ilike(f"%{skill.strip()}%"))

    profiles = query.order_by(StudentProfile.employability_score.desc()).all()
    return jsonify([p.to_dict() for p in profiles]), 200


@company_bp.route("/students/<int:profile_id>", methods=["GET"])
@role_required("company")
def view_student(profile_id):
    """View a single verified student profile."""
    profile = StudentProfile.query.get(profile_id)
    if not profile or not profile.is_verified:
        return jsonify({"error": "Profile not found or not verified"}), 404
    return jsonify(profile.to_dict()), 200


@company_bp.route("/reports", methods=["GET"])
@role_required("company")
def view_reports():
    """Company can access consolidated student data (verified only)."""
    query = StudentProfile.query.filter(StudentProfile.is_verified == True)

    dept = request.args.get("department")
    min_cgpa = request.args.get("min_cgpa")

    if dept:
        query = query.filter(StudentProfile.department.ilike(f"%{dept}%"))
    if min_cgpa:
        query = query.filter(StudentProfile.cgpa >= float(min_cgpa))

    profiles = query.order_by(StudentProfile.employability_score.desc()).all()

    summary = {
        "total_students": len(profiles),
        "average_cgpa": round(sum(p.cgpa for p in profiles) / len(profiles), 2) if profiles else 0,
        "average_score": round(sum(p.employability_score for p in profiles) / len(profiles), 2) if profiles else 0,
        "department_breakdown": {},
        "students": [p.to_dict() for p in profiles],
    }

    for p in profiles:
        dept_name = p.department or "Unknown"
        if dept_name not in summary["department_breakdown"]:
            summary["department_breakdown"][dept_name] = 0
        summary["department_breakdown"][dept_name] += 1

    return jsonify(summary), 200

@company_bp.route("/placements", methods=["GET"])
@role_required("company")
def list_company_placements():
    """List placement opportunities created by this company."""
    user_id = int(get_jwt_identity())
    opps = PlacementOpportunity.query.filter_by(created_by=user_id).order_by(PlacementOpportunity.created_at.desc()).all()
    return jsonify([o.to_dict() for o in opps]), 200

@company_bp.route("/placements", methods=["POST"])
@role_required("company")
def create_company_placement():
    """Company creates a new placement opportunity."""
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

    user_id = int(get_jwt_identity())
    from database import db
    
    opp = PlacementOpportunity(
        company_name=company_name,
        role_title=role_title,
        package=data.get("package", ""),
        eligibility_criteria=data.get("eligibility_criteria", ""),
        min_cgpa=float(data.get("min_cgpa", 0)),
        required_skills=json.dumps(data.get("required_skills", [])),
        deadline=deadline,
        created_by=user_id,
    )
    db.session.add(opp)
    db.session.commit()
    return jsonify({"message": "Opportunity created", "opportunity": opp.to_dict()}), 201

@company_bp.route("/placements/<int:opp_id>", methods=["PUT"])
@role_required("company")
def edit_company_placement(opp_id):
    """Company edits their own placement opportunity."""
    user_id = int(get_jwt_identity())
    opp = PlacementOpportunity.query.filter_by(id=opp_id, created_by=user_id).first()
    if not opp:
        return jsonify({"error": "Opportunity not found or access denied"}), 404

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

    from database import db
    db.session.commit()
    return jsonify({"message": "Opportunity updated", "opportunity": opp.to_dict()}), 200

@company_bp.route("/placements/<int:opp_id>", methods=["DELETE"])
@role_required("company")
def delete_company_placement(opp_id):
    """Company deletes their own placement opportunity."""
    user_id = int(get_jwt_identity())
    opp = PlacementOpportunity.query.filter_by(id=opp_id, created_by=user_id).first()
    if not opp:
        return jsonify({"error": "Opportunity not found or access denied"}), 404
        
    from database import db
    db.session.delete(opp)
    db.session.commit()
    return jsonify({"message": "Opportunity deleted"}), 200

@company_bp.route("/applications/<int:record_id>/status", methods=["PUT"])
@role_required("company")
def update_application_status(record_id):
    """Company updates a student's application status with strict flow rules."""
    from models.placement import PlacementRecord
    from database import db

    user_id = int(get_jwt_identity())
    
    # Verify the application belongs to an opportunity created by this company
    record = PlacementRecord.query.get(record_id)
    if not record or record.opportunity.created_by != user_id:
        return jsonify({"error": "Application not found or access denied"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").lower()
    
    valid_statuses = ["applied", "shortlisted", "selected", "rejected"]
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

    current_status = record.status.lower()

    # Apply flow rules
    if current_status == "rejected":
        return jsonify({"error": "Cannot change status. Student has already been rejected."}), 400
    if current_status == "selected":
        return jsonify({"error": "Cannot change status. Student has already been selected."}), 400

    if new_status == "selected" and current_status != "shortlisted":
        return jsonify({"error": "Student must be shortlisted before they can be selected."}), 400

    record.status = new_status

    # Also update the student's global placement profile status if they are selected
    if new_status == "selected":
        from models.student_profile import StudentProfile
        student = StudentProfile.query.get(record.student_id)
        if student:
            student.placement_status = "placed"
            student.placement_company = record.opportunity.company_name

    db.session.commit()
    return jsonify({
        "message": f"Status updated to {new_status}", 
        "record": record.to_dict()
    }), 200
