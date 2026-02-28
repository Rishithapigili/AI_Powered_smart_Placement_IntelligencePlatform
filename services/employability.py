import json


def calculate_employability_score(profile):
    """Calculate employability score (0-100) from a StudentProfile instance.

    Weights:
        CGPA           → 30%
        Internships    → 25%
        Certifications → 25%
        Projects       → 20%
    """
    # CGPA component (0-30)
    cgpa = profile.cgpa or 0
    cgpa_score = (min(cgpa, 10) / 10) * 30

    # Internship component (0-25), caps at 3
    internship_count = profile.internship_count or 0
    internship_score = min(internship_count / 3, 1.0) * 25

    # Certifications component (0-25), caps at 5
    try:
        certs = json.loads(profile.certifications) if profile.certifications else []
    except (json.JSONDecodeError, TypeError):
        certs = []
    cert_score = min(len(certs) / 5, 1.0) * 25

    # Projects component (0-20), caps at 4
    try:
        projects = json.loads(profile.projects) if profile.projects else []
    except (json.JSONDecodeError, TypeError):
        projects = []
    project_score = min(len(projects) / 4, 1.0) * 20

    total = cgpa_score + internship_score + cert_score + project_score
    return round(total, 2)


def recalculate_and_save(profile, db):
    """Recalculate the employability score and persist it."""
    profile.employability_score = calculate_employability_score(profile)
    db.session.add(profile)
