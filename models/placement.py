import json
from datetime import datetime
from database import db


class PlacementOpportunity(db.Model):
    __tablename__ = "placement_opportunities"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), nullable=False)
    role_title = db.Column(db.String(120), nullable=False)
    package = db.Column(db.String(50), default="")  # e.g. "6 LPA"
    eligibility_criteria = db.Column(db.Text, default="")
    min_cgpa = db.Column(db.Float, default=0.0)
    required_skills = db.Column(db.Text, default="[]")  # JSON list
    deadline = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship("PlacementRecord", backref="opportunity", cascade="all, delete-orphan")

    def to_dict(self):
        try:
            skills = json.loads(self.required_skills) if self.required_skills else []
        except (json.JSONDecodeError, TypeError):
            skills = []

        return {
            "id": self.id,
            "company_name": self.company_name,
            "role_title": self.role_title,
            "package": self.package,
            "eligibility_criteria": self.eligibility_criteria,
            "min_cgpa": self.min_cgpa,
            "required_skills": skills,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PlacementRecord(db.Model):
    __tablename__ = "placement_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("placement_opportunities.id"), nullable=False)
    status = db.Column(db.String(30), default="applied")  # applied / shortlisted / selected / rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("StudentProfile", backref="placement_records")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "opportunity_id": self.opportunity_id,
            "status": self.status,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "student_name": self.student.full_name if self.student else None,
            "company_name": self.opportunity.company_name if self.opportunity else None,
            "role_title": self.opportunity.role_title if self.opportunity else None,
        }
