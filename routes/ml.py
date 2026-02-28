"""ML Prediction API routes."""
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.ml_service import (
    train_models,
    predict_placement,
    predict_salary,
    get_feature_importances,
    get_training_metrics,
    recommend_students,
)
from models.student_profile import StudentProfile
from utils.decorators import role_required

ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")


@ml_bp.route("/train", methods=["POST"])
@role_required("admin")
def train():
    """Train/retrain the ML models on the current dataset."""
    metrics = train_models()
    return jsonify({"message": "Models trained successfully", "metrics": metrics}), 200


@ml_bp.route("/predict/placement", methods=["POST"])
@jwt_required()
def predict_placement_status():
    """Predict placement status from input features."""
    data = request.get_json(silent=True) or {}

    cgpa = float(data.get("cgpa", 0))
    programming_skills = int(data.get("programming_skills_rating", 0))
    soft_skills = int(data.get("soft_skills_rating", 0))
    internship_count = int(data.get("internship_count", 0))
    certification_count = int(data.get("certification_count", 0))

    result = predict_placement(cgpa, programming_skills, soft_skills, internship_count, certification_count)
    result["input"] = {
        "cgpa": cgpa,
        "programming_skills_rating": programming_skills,
        "soft_skills_rating": soft_skills,
        "internship_count": internship_count,
        "certification_count": certification_count,
    }
    return jsonify(result), 200


@ml_bp.route("/predict/salary", methods=["POST"])
@jwt_required()
def predict_salary_package():
    """Predict salary package from input features."""
    data = request.get_json(silent=True) or {}

    cgpa = float(data.get("cgpa", 0))
    programming_skills = int(data.get("programming_skills_rating", 0))
    soft_skills = int(data.get("soft_skills_rating", 0))
    internship_count = int(data.get("internship_count", 0))
    certification_count = int(data.get("certification_count", 0))

    result = predict_salary(cgpa, programming_skills, soft_skills, internship_count, certification_count)
    result["input"] = {
        "cgpa": cgpa,
        "programming_skills_rating": programming_skills,
        "soft_skills_rating": soft_skills,
        "internship_count": internship_count,
        "certification_count": certification_count,
    }
    return jsonify(result), 200


@ml_bp.route("/predict/my-profile", methods=["GET"])
@jwt_required()
@role_required("student")
def predict_my_profile():
    """Predict placement status and salary for the logged-in student's profile."""
    user_id = int(get_jwt_identity())
    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Extract features from profile
    try:
        certs = json.loads(profile.certifications) if profile.certifications else []
    except (json.JSONDecodeError, TypeError):
        certs = []

    cgpa = profile.cgpa or 0
    programming_skills = profile.programming_skills_rating or 0
    soft_skills = profile.soft_skills_rating or 0
    internship_count = profile.internship_count or 0
    certification_count = len(certs)

    placement_result = predict_placement(cgpa, programming_skills, soft_skills, internship_count, certification_count)
    salary_result = predict_salary(cgpa, programming_skills, soft_skills, internship_count, certification_count)

    return jsonify({
        "placement_prediction": placement_result,
        "salary_prediction": salary_result,
        "profile_features": {
            "cgpa": cgpa,
            "programming_skills_rating": programming_skills,
            "soft_skills_rating": soft_skills,
            "internship_count": internship_count,
            "certification_count": certification_count,
        },
    }), 200


@ml_bp.route("/feature-importance", methods=["GET"])
@jwt_required()
def feature_importance():
    """Return feature importances from the placement classifier."""
    importances = get_feature_importances()
    return jsonify({"feature_importances": importances}), 200


@ml_bp.route("/metrics", methods=["GET"])
@jwt_required()
@role_required("admin")
def model_metrics():
    """Return training metrics for both models."""
    metrics = get_training_metrics()
    return jsonify(metrics), 200

@ml_bp.route("/recommend", methods=["POST"])
@jwt_required()
@role_required("company")
def recommend():
    """Recommend students based on required skills (TF-IDF + Cosine Similarity)."""
    data = request.get_json(silent=True) or {}
    skills_text = data.get("skills", "").strip()
    top_n = int(data.get("top_n", 5))

    if not skills_text:
        return jsonify({"error": "Please provide 'skills' text to match against."}), 400

    results = recommend_students(skills_text, top_n)
    return jsonify({"recommendations": results}), 200
