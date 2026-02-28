"""Seed the database with admin + 500 students from the placement dataset."""
import os
import re
import json
import pandas as pd

from app import create_app
from database import db
from models.user import User
from models.student_profile import StudentProfile
from config import Config

# ─── Skill category → numeric rating mappings (same as ml_service) ───
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


def _extract_skill_category(text, suffix_keyword):
    """Extract skill category name from e.g. 'Python & Data Analysis Level 42'."""
    if not isinstance(text, str):
        return ""
    return re.sub(rf"\s+{suffix_keyword}\s+\d+$", "", text).strip()


def seed():
    app = create_app()
    with app.app_context():
        # Clear existing tables (except Admin)
        db.session.query(StudentProfile).delete()
        db.session.query(User).filter(User.role != 'admin').delete()
        db.session.commit()
        print("[*] Cleared existing non-admin users and student profiles.")
        # ── 1. Admin ──
        existing_admin = User.query.filter_by(username=Config.ADMIN_USERNAME).first()
        if not existing_admin:
            admin = User(
                username=Config.ADMIN_USERNAME,
                email=Config.ADMIN_EMAIL,
                role="admin",
            )
            admin.set_password(Config.ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[+] Admin user '{Config.ADMIN_USERNAME}' created.")
        else:
            print(f"[=] Admin user '{Config.ADMIN_USERNAME}' already exists.")

        # ── 2. Import students from updated dataset ──
        dataset_path = os.path.join(os.path.dirname(__file__), "utils", "updated_students_dataset_v2.csv")
        if not os.path.exists(dataset_path):
            print(f"[!] {dataset_path} not found — skipping student import.")
            return

        # File is actually xlsx despite .csv extension
        try:
            df = pd.read_excel(dataset_path)
        except Exception:
            df = pd.read_csv(dataset_path)
        print(f"[*] Loaded {len(df)} students from dataset.")

        imported = 0
        skipped = 0
        for _, row in df.iterrows():
            student_id = str(row.get("roll_number", "")).strip()
            student_name = str(row.get("student_name", "")).strip()
            
            # Formatting username: studentName_studentRollnumber
            # Removing spaces in name to make a clean username
            clean_name = student_name.replace(" ", "_")
            username = f"{clean_name}_{student_id}"

            if not student_id or not student_name:
                continue

            # Skip if user already exists
            if User.query.filter_by(username=username).first():
                skipped += 1
                continue

            # Create user account: username = studentName_studentRollnumber, password = roll_number
            user = User(
                username=username,
                email=f"{username.lower()}@student.university.edu",
                role="student",
            )
            user.set_password(student_id)
            db.session.add(user)
            db.session.commit()

            # Parse new text-based skill columns
            tech_text = str(row.get("Technical skills", ""))
            soft_text = str(row.get("Soft_skills", ""))
            tech_category = _extract_skill_category(tech_text, "Level")
            soft_category = _extract_skill_category(soft_text, "Strength")

            prog_rating = TECH_SKILL_MAP.get(tech_category, 5)
            soft_rating = SOFT_SKILL_MAP.get(soft_category, 5)
            
            # Build skills list from categories
            skills_list = []
            if tech_category:
                skills_list.append(tech_category)
            if soft_category:
                skills_list.append(soft_category)

            # Map placement_status
            raw_status = str(row.get("placement_status", "Not Placed")).strip()
            if raw_status == "Placed":
                status = "placed"
            elif raw_status == "In Process":
                status = "shortlisted"
            else:
                status = "not_placed"

            profile = StudentProfile(
                user_id=user.id,
                full_name=student_name,
                department=str(row.get("department", "")).strip(),
                roll_number=student_id,
                cgpa=float(row.get("cgpa", 0) or 0),
                programming_skills_rating=prog_rating,
                soft_skills_rating=soft_rating,
                skills=json.dumps(skills_list),
                projects=json.dumps([]),
                internship_count=int(row.get("internship_count", 0) or 0),
                certifications=json.dumps([f"Cert-{i+1}" for i in range(int(row.get("certifications", 0) or 0))]),
                career_preferences=str(row.get("preferred_role", "")),
                placement_status=status,
                is_verified=True,
            )

            # Calculate employability score
            from services.employability import calculate_employability_score
            profile.employability_score = calculate_employability_score(profile)

            db.session.add(profile)
            db.session.commit()
            imported += 1

        print(f"[+] Imported {imported} students, skipped {skipped} (already exist).")
        # ── 3. Import default companies ──
        companies = [
            {"name": "Google", "username": "CMP001", "email": "careers@google.com"},
            {"name": "Microsoft", "username": "CMP002", "email": "jobs@microsoft.com"},
            {"name": "Amazon", "username": "CMP003", "email": "recruiting@amazon.com"},
            {"name": "Meta", "username": "CMP004", "email": "hiring@meta.com"},
            {"name": "Apple", "username": "CMP005", "email": "careers@apple.com"},
        ]
        
        imported_companies = 0
        skipped_companies = 0
        
        for comp in companies:
            if User.query.filter_by(username=comp["username"]).first():
                skipped_companies += 1
                continue
                
            company_user = User(
                username=comp["username"],
                email=comp["email"],
                role="company"
            )
            company_user.set_password("ABC_" + comp["name"])  # e.g. ABC_Google
            db.session.add(company_user)
            imported_companies += 1

        db.session.commit()
        print(f"[+] Imported {imported_companies} companies, skipped {skipped_companies}.")
        print(f"[*] Done! Student login: username = studentName_rollNumber (e.g. Kiran_Singh_2210S000), password = roll_number (e.g. 2210S000)")
        print(f"[*] Company login: username = CMP001-CMP005, password = ABC_CompanyName (e.g. ABC_Google)")


if __name__ == "__main__":
    seed()

