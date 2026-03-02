from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import Exam, StudentSubmission
from datetime import datetime

# PDF
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image
)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4

import os

router = APIRouter(prefix="/public", tags=["Public"])


# ==========================================================
# 1️⃣ GET PUBLISHED EXAMS
# ==========================================================
@router.get("/exams")
def get_published_exams(db: Session = Depends(get_db)):

    exams = db.query(Exam).filter(
        Exam.result_status.in_(["published", "locked"])
    ).all()

    return [
        {
            "id": exam.id,
            "title": exam.title,
            "class_name": exam.class_name,
            "division": exam.division,
            "subject": exam.subject
        }
        for exam in exams
    ]


# ==========================================================
# 2️⃣ GET STUDENT RESULT
# ==========================================================
@router.get("/result/{exam_id}/{roll_number}")
def get_student_result(exam_id: int, roll_number: str, db: Session = Depends(get_db)):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.result_status not in ["published", "locked"]:
        raise HTTPException(status_code=403, detail="Result not published yet")

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id,
        StudentSubmission.roll_number == roll_number
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Result not found")

    if submission.total_marks is None:
        raise HTTPException(status_code=400, detail="Result not evaluated yet")

    return {
        "exam_title": exam.title,
        "roll_number": submission.roll_number,
        "total_marks": submission.total_marks,
        "max_marks": submission.max_marks,
        "percentage": submission.percentage,
        "grade": submission.grade,
        "question_wise": submission.evaluation_json
    }


# ==========================================================
# 3️⃣ DOWNLOAD MARKSHEET (FIXED PROFESSIONAL VERSION)
# ==========================================================
@router.get("/marksheet/{exam_id}/{roll_number}")
def download_marksheet(exam_id: int, roll_number: str, db: Session = Depends(get_db)):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.result_status not in ["published", "locked"]:
        raise HTTPException(status_code=403, detail="Result not published")

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id,
        StudentSubmission.roll_number == roll_number
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Result not found")

    if submission.total_marks is None:
        raise HTTPException(status_code=400, detail="Result not evaluated yet")

    os.makedirs("generated_marksheets", exist_ok=True)
    file_path = f"generated_marksheets/marksheet_{exam_id}_{roll_number}.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    elements = []

    # ==============================
    # STYLES (FIXED SPACING)
    # ==============================

    college_style = ParagraphStyle(
        name="CollegeStyle",
        fontSize=20,
        alignment=1,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        name="SubtitleStyle",
        fontSize=12,
        alignment=1,
        textColor=colors.grey,
        spaceAfter=14
    )

    normal_style = ParagraphStyle(
        name="NormalStyle",
        fontSize=11,
        spaceAfter=6
    )

    footer_style = ParagraphStyle(
        name="FooterStyle",
        fontSize=9,
        alignment=1,
        textColor=colors.grey
    )

    # ==============================
    # LOGO (PROPERLY SPACED)
    # ==============================

    logo_path = "storage/assets/slazzer-preview-8rnsa.png"

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.2 * inch, height=1.2 * inch)
        logo.hAlign = "CENTER"
        elements.append(logo)
        elements.append(Spacer(1, 0.25 * inch))

    # ==============================
    # COLLEGE NAME (NO OVERLAP)
    # ==============================

    elements.append(Paragraph("<b>Zeal Polytechnic</b>", college_style))
    elements.append(Paragraph("Official Examination Marksheet", subtitle_style))

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 0.4 * inch))

    # ==============================
    # STUDENT INFO TABLE
    # ==============================

    info_data = [
        ["Exam", exam.title],
        ["Class", exam.class_name],
        ["Subject", exam.subject],
        ["Roll Number", submission.roll_number],
        ["Generated Date", datetime.utcnow().strftime("%d-%m-%Y")]
    ]

    info_table = Table(info_data, colWidths=[2 * inch, 3.5 * inch])

    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.6 * inch))

    # ==============================
    # MARKS TABLE
    # ==============================

    marks_data = [["Question", "Obtained", "Max Marks"]]

    for qid, details in submission.evaluation_json.items():
        if not details.get("ignored_due_to_best_of", False):
            marks_data.append([
                qid,
                str(round(details.get("final_marks", 0), 2)),
                str(details.get("max_marks", 0))
            ])

    marks_data.append(["", "", ""])
    marks_data.append(["TOTAL", str(submission.total_marks), str(submission.max_marks)])

    marks_table = Table(marks_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])

    marks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (-3, -1), (-1, -1), colors.whitesmoke),
    ]))

    elements.append(marks_table)
    elements.append(Spacer(1, 0.6 * inch))

    # ==============================
    # SUMMARY
    # ==============================

    summary_data = [
        ["Percentage", f"{submission.percentage}%"],
        ["Grade", submission.grade]
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])

    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 1 * inch))

    # ==============================
    # SIGNATURE
    # ==============================

    elements.append(Paragraph("______________________________", normal_style))
    elements.append(Paragraph("Authorized Signature", normal_style))
    elements.append(Spacer(1, 0.5 * inch))

    # ==============================
    # FOOTER
    # ==============================

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(
        "This marksheet is digitally generated by AI Examiner System.",
        footer_style
    ))

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"marksheet_{roll_number}.pdf"
    )