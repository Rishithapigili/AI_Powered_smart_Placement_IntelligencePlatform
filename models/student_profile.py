import json
from datetime import datetime
from database import db


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # Personal & Academic
    full_name = db.Column(db.String(120), nullable=False, default="")
    department = db.Column(db.String(80), default="")
    roll_number = db.Column(db.String(30), unique=True, nullable=True)
    cgpa = db.Column(db.Float, default=0.0)
    tenth_percentage = db.Column(db.Float, default=0.0)
    twelfth_percentage = db.Column(db.Float, default=0.0)

    # Skills & Experience (stored as JSON strings / integers)
    programming_skills_rating = db.Column(db.Integer, default=0)
    soft_skills_rating = db.Column(db.Integer, default=0)
    skills = db.Column(db.Text, default="[]")
    certifications = db.Column(db.Text, default="[]")
    projects = db.Column(db.Text, default="[]")
    internships = db.Column(db.Text, default="[]")
    internship_count = db.Column(db.Integer, default=0)

    # Preferences
    career_preferences = db.Column(db.Text, default="")

    # Uploads
    resume_path = db.Column(db.String(256), nullable=True)
    photo_path = db.Column(db.String(256), nullable=True)
    documents = db.Column(db.Text, default="[]")  # JSON list of doc paths

    # Status
    is_verified = db.Column(db.Boolean, default=False)
    placement_status = db.Column(db.String(30), default="not_placed")  # not_placed / shortlisted / placed
    placement_company = db.Column(db.String(120), nullable=True)
    employability_score = db.Column(db.Float, default=0.0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---------- helpers ----------

    def _parse_json(self, field_value):
        try:
            return json.loads(field_value) if field_value else []
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "department": self.department,
            "roll_number": self.roll_number,
            "cgpa": self.cgpa,
            "tenth_percentage": self.tenth_percentage,
            "twelfth_percentage": self.twelfth_percentage,
            "programming_skills_rating": self.programming_skills_rating,
            "soft_skills_rating": self.soft_skills_rating,
            "skills": self._parse_json(self.skills),
            "certifications": self._parse_json(self.certifications),
            "projects": self._parse_json(self.projects),
            "internships": self._parse_json(self.internships),
            "internship_count": self.internship_count,
            "career_preferences": self.career_preferences,
            "resume_path": self.resume_path,
            "photo_path": self.photo_path,
            "documents": self._parse_json(self.documents),
            "is_verified": self.is_verified,
            "placement_status": self.placement_status,
            "placement_company": self.placement_company,
            "employability_score": round(self.employability_score, 2) if self.employability_score else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
