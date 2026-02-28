import csv
import io
import json
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from database import db
from models.student_profile import StudentProfile
from models.user import User


def _apply_filters(query, filters):
    """Apply common filters to a StudentProfile query."""
    if filters.get("department"):
        query = query.filter(StudentProfile.department.ilike(f"%{filters['department']}%"))
    if filters.get("min_cgpa"):
        query = query.filter(StudentProfile.cgpa >= float(filters["min_cgpa"]))
    if filters.get("skills"):
        for skill in filters["skills"].split(","):
            query = query.filter(StudentProfile.skills.ilike(f"%{skill.strip()}%"))
    if filters.get("placement_status"):
        query = query.filter(StudentProfile.placement_status == filters["placement_status"])
    if filters.get("verified_only") in ("true", "1", True):
        query = query.filter(StudentProfile.is_verified == True)
    return query


def generate_csv_report(filters):
    """Generate a CSV string of student profiles matching the given filters."""
    query = StudentProfile.query.join(User)
    query = _apply_filters(query, filters)
    profiles = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll Number", "Full Name", "Department", "CGPA",
        "10th %", "12th %", "Skills", "Certifications",
        "Internship Count", "Projects", "Employability Score",
        "Placement Status", "Placement Company", "Verified",
    ])

    for p in profiles:
        skills = json.loads(p.skills) if p.skills else []
        certs = json.loads(p.certifications) if p.certifications else []
        projects = json.loads(p.projects) if p.projects else []

        writer.writerow([
            p.roll_number, p.full_name, p.department, p.cgpa,
            p.tenth_percentage, p.twelfth_percentage,
            "; ".join(skills), "; ".join(certs),
            p.internship_count, "; ".join(projects),
            round(p.employability_score, 2),
            p.placement_status, p.placement_company or "",
            "Yes" if p.is_verified else "No",
        ])

    return output.getvalue()


def generate_pdf_report(filters):
    """Generate a PDF report of student profiles matching the given filters."""
    query = StudentProfile.query.join(User)
    query = _apply_filters(query, filters)
    profiles = query.all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("University Placement Report", styles["Title"]))
    elements.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    elements.append(Spacer(1, 0.25 * inch))

    # Table header
    header = ["Roll No", "Name", "Dept", "CGPA", "Skills", "Score", "Status", "Verified"]
    data = [header]

    for p in profiles:
        skills = json.loads(p.skills) if p.skills else []
        data.append([
            p.roll_number or "",
            p.full_name,
            p.department,
            str(p.cgpa),
            ", ".join(skills[:3]) + ("..." if len(skills) > 3 else ""),
            str(round(p.employability_score, 2)),
            p.placement_status,
            "Yes" if p.is_verified else "No",
        ])

    if len(data) == 1:
        elements.append(Paragraph("No students match the selected filters.", styles["Normal"]))
    else:
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
