"""ML Prediction Service — Random Forest models for placement prediction.

Models:
    1. Placement Status Classifier — Predicts Placed (1) vs Not Placed (0)
    2. Salary Package Regressor — Predicts estimated salary in LPA
    3. Feature Importance — Extracted from the trained classifier
"""
import json
import os
import re
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, r2_score

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml_models")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "placement_classifier.pkl")
REGRESSOR_PATH = os.path.join(MODEL_DIR, "salary_regressor.pkl")
FEATURE_NAMES = ["cgpa", "programming_skills", "soft_skills", "internship_count", "certifications"]

# ─── Skill category → numeric rating mappings ───
TECH_SKILL_MAP = {
    "Python & Data Analysis": 8,
    "Full Stack Development": 9,
    "Cloud Computing": 7,
    "Cybersecurity": 8,
    "AI & Machine Learning": 10,
    "Mobile App Development": 7,
    "DevOps Engineering": 8,
    "Database Management": 6,
    "Business Intelligence": 6,
    "Embedded Systems": 7,
}

SOFT_SKILL_MAP = {
    "Leadership & Teamwork": 9,
    "Critical Thinking": 8,
    "Effective Communication": 8,
    "Adaptability": 7,
    "Problem Solving": 9,
    "Time Management": 7,
    "Creativity": 8,
    "Decision Making": 7,
    "Emotional Intelligence": 6,
    "Collaboration": 8,
}

# ─── Singleton model holders ───
_classifier = None
_regressor = None
_training_metrics = {}


def _extract_skill_category(text, suffix_keyword):
    """Extract the skill category name from text like 'Python & Data Analysis Level 42'."""
    if not isinstance(text, str):
        return ""
    return re.sub(rf"\s+{suffix_keyword}\s+\d+$", "", text).strip()


def _load_and_prepare_data():
    """Load the placement dataset and engineer features."""
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "utils", "updated_students_dataset_v2.csv")

    # The file is actually xlsx despite .csv extension
    try:
        df = pd.read_excel(dataset_path)
    except Exception:
        df = pd.read_csv(dataset_path)

    # Parse text-based skill columns into numeric ratings
    if "Technical skills" in df.columns:
        df["tech_category"] = df["Technical skills"].apply(lambda x: _extract_skill_category(str(x), "Level"))
        df["programming_skills"] = df["tech_category"].map(TECH_SKILL_MAP).fillna(5).astype(int)
    elif "programming_skills" not in df.columns:
        df["programming_skills"] = 5

    if "Soft_skills" in df.columns:
        df["soft_category"] = df["Soft_skills"].apply(lambda x: _extract_skill_category(str(x), "Strength"))
        df["soft_skills"] = df["soft_category"].map(SOFT_SKILL_MAP).fillna(5).astype(int)
    elif "soft_skills" not in df.columns:
        df["soft_skills"] = 5

    # Convert binary target: 1 = Placed, 0 = Not Placed (In Process treated as Not Placed)
    df["placed_binary"] = (df["placement_status"] == "Placed").astype(int)

    # Synthetic salary based on features (since dataset has no salary column)
    # Base salary + bonuses from skills, CGPA, internships, certs
    np.random.seed(42)
    base = 3.0  # 3 LPA base
    df["salary_lpa"] = (
        base
        + (df["cgpa"] - 6) * 1.2               # Higher CGPA → higher salary
        + df["internship_count"] * 0.8          # Each internship adds ~0.8 LPA
        + df["programming_skills"] * 0.3        # Skills bonus
        + df["soft_skills"] * 0.2               # Soft skills bonus
        + df["certifications"] * 0.3            # Certs bonus
        + np.random.normal(0, 0.5, len(df))     # Noise
    ).clip(2.5, 25.0).round(2)

    # Placed students get a boost
    df.loc[df["placed_binary"] == 1, "salary_lpa"] *= 1.15

    return df


def train_models():
    """Train both Random Forest models on the dataset."""
    global _classifier, _regressor, _training_metrics

    os.makedirs(MODEL_DIR, exist_ok=True)
    df = _load_and_prepare_data()

    X = df[FEATURE_NAMES].values
    y_class = df["placed_binary"].values
    y_salary = df["salary_lpa"].values

    # ─── 1. Placement Classifier ───
    X_train, X_test, y_train, y_test = train_test_split(X, y_class, test_size=0.2, random_state=42, stratify=y_class)

    clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    clf_accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)
    clf_report = classification_report(y_test, y_pred, target_names=["Not Placed", "Placed"], output_dict=True)

    # ─── 2. Salary Regressor ───
    Xr_train, Xr_test, yr_train, yr_test = train_test_split(X, y_salary, test_size=0.2, random_state=42)

    reg = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    reg.fit(Xr_train, yr_train)
    yr_pred = reg.predict(Xr_test)

    reg_r2 = round(r2_score(yr_test, yr_pred) * 100, 2)

    # ─── 3. Feature Importances ───
    importances = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in clf.feature_importances_]))

    # Save models
    with open(CLASSIFIER_PATH, "wb") as f:
        pickle.dump(clf, f)
    with open(REGRESSOR_PATH, "wb") as f:
        pickle.dump(reg, f)

    _classifier = clf
    _regressor = reg
    _training_metrics = {
        "classifier_accuracy": clf_accuracy,
        "classifier_report": {
            "not_placed": {k: round(v, 3) for k, v in clf_report["Not Placed"].items() if k != "support"},
            "placed": {k: round(v, 3) for k, v in clf_report["Placed"].items() if k != "support"},
        },
        "regressor_r2_score": reg_r2,
        "feature_importances": importances,
        "training_samples": len(df),
    }

    return _training_metrics


def _ensure_models_loaded():
    """Load models from disk if not already in memory."""
    global _classifier, _regressor
    if _classifier is None:
        if os.path.exists(CLASSIFIER_PATH):
            with open(CLASSIFIER_PATH, "rb") as f:
                _classifier = pickle.load(f)
        else:
            train_models()
    if _regressor is None:
        if os.path.exists(REGRESSOR_PATH):
            with open(REGRESSOR_PATH, "rb") as f:
                _regressor = pickle.load(f)
        else:
            train_models()


def predict_placement(cgpa, programming_skills, soft_skills, internship_count, certifications):
    """Predict placement status. Returns dict with prediction and probability."""
    _ensure_models_loaded()
    features = np.array([[cgpa, programming_skills, soft_skills, internship_count, certifications]])
    prediction = int(_classifier.predict(features)[0])
    probabilities = _classifier.predict_proba(features)[0]

    return {
        "prediction": prediction,
        "status": "Placed" if prediction == 1 else "Not Placed",
        "confidence": round(float(max(probabilities)) * 100, 2),
        "probability_placed": round(float(probabilities[1]) * 100, 2),
        "probability_not_placed": round(float(probabilities[0]) * 100, 2),
    }


def predict_salary(cgpa, programming_skills, soft_skills, internship_count, certifications):
    """Predict salary package in LPA."""
    _ensure_models_loaded()
    features = np.array([[cgpa, programming_skills, soft_skills, internship_count, certifications]])
    salary = float(_regressor.predict(features)[0])

    return {
        "predicted_salary_lpa": round(salary, 2),
        "salary_range": {
            "min": round(max(salary - 1.0, 2.5), 2),
            "max": round(salary + 1.0, 2),
        },
    }


def get_feature_importances():
    """Return feature importances from the placement classifier."""
    _ensure_models_loaded()
    importances = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in _classifier.feature_importances_]))
    # Sort by importance descending
    sorted_imp = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
    return sorted_imp


def get_training_metrics():
    """Return cached training metrics."""
    if not _training_metrics:
        train_models()
    return _training_metrics

def recommend_students(job_skills_text, top_n=5):
    """
    Recommend students based on job skills using TF-IDF and Cosine Similarity.
    This fetches all verified students, combines their skills, and returns top matches.
    """
    from models.student_profile import StudentProfile
    
    # Get all verified students
    students = StudentProfile.query.filter_by(is_verified=True).all()
    if not students:
        return []

    # Prepare corpus: combine student skills and projects
    student_docs = []
    student_map = []
    for s in students:
        try:
            skills = " ".join(json.loads(s.skills) if s.skills else [])
        except:
            skills = ""
        try:
            projects = " ".join(json.loads(s.projects) if s.projects else [])
        except:
            projects = ""
            
        doc = f"{skills} {projects}".strip()
        student_docs.append(doc)
        student_map.append(s)

    # Add the query to the corpus
    docs = [job_skills_text] + student_docs

    # Vectorize
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(docs)

    # Compute cosine similarity between query (index 0) and all students (index 1 to end)
    sim_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    # Get top matching indices
    top_indices = sim_scores.argsort()[::-1][:top_n]

    results = []
    for idx in top_indices:
        score = float(sim_scores[idx])
        if score > 0:  # Only return matches with some similarity
            student = student_map[idx]
            match_pct = round(score * 100, 1)
            results.append({
                "id": student.id,
                "full_name": student.full_name,
                "department": student.department,
                "cgpa": student.cgpa,
                "skills": json.loads(student.skills) if student.skills else [],
                "employability_score": student.employability_score,
                "placement_status": student.placement_status,
                "match_percentage": match_pct
            })

    return results
