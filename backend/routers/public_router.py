from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import Exam, StudentSubmission
from datetime import datetime
import os

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
# 3️⃣ DOWNLOAD MARKSHEET (FINAL PROFESSIONAL VERSION)
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
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elements = []

    # ==============================
    # HEADER (LOGO + COLLEGE + TITLE)
    # ==============================

    logo_path = "storage/assets/slazzer-preview-8rnsa.png"

    header_text_style = ParagraphStyle(
        name="HeaderText",
        fontSize=16,
        leading=18
    )

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=0.9 * inch, height=0.9 * inch)

        text_part = Paragraph(
            "<b>Zeal Polytechnic</b><br/>"
            "<font size=11 color='grey'>Official Examination Marksheet</font>",
            header_text_style
        )

        header_table = Table(
            [[logo, text_part]],
            colWidths=[1 * inch, 4.8 * inch]
        )

        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        elements.append(header_table)

    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 15))

    # ==============================
    # STUDENT INFO TABLE
    # ==============================

    info_data = [
        ["Exam", exam.title, "Class", exam.class_name],
        ["Subject", exam.subject, "Roll No", submission.roll_number],
        ["Generated Date", datetime.utcnow().strftime("%d-%m-%Y"), "", ""]
    ]

    info_table = Table(info_data, colWidths=[90, 170, 90, 110])

    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 18))

    # ==============================
    # MARKS TABLE
    # ==============================

    marks_data = [["Question", "Obtained", "Max Marks"]]

    for qid, details in submission.evaluation_json.items():
        if not details.get("ignored_due_to_best_of", False):
            marks_data.append([
                qid,
                round(details.get("final_marks", 0), 2),
                details.get("max_marks", 0)
            ])

    marks_data.append([
        "TOTAL",
        round(submission.total_marks, 2),
        submission.max_marks
    ])

    marks_table = Table(marks_data, colWidths=[200, 80, 80])

    marks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    elements.append(marks_table)
    elements.append(Spacer(1, 18))

    # ==============================
    # SUMMARY TABLE
    # ==============================

    summary_data = [
        ["Percentage", f"{round(submission.percentage, 2)}%"],
        ["Grade", submission.grade]
    ]

    summary_table = Table(summary_data, colWidths=[120, 220])

    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    # ==============================
    # SIGNATURE
    # ==============================

    elements.append(
        Paragraph("<para alignment='right'><b>Authorized Signature</b></para>",
        ParagraphStyle(name="SigStyle", fontSize=10))
    )

    elements.append(Spacer(1, 10))

    # ==============================
    # FOOTER
    # ==============================

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 5))
    elements.append(
        Paragraph(
            "Digitally generated by AI Examiner System.",
            ParagraphStyle(name="FooterStyle", fontSize=8, textColor=colors.grey)
        )
    )

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"marksheet_{roll_number}.pdf"
    )