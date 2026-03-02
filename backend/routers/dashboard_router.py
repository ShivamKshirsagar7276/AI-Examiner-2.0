from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import get_db
from core.models import Exam, StudentSubmission

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):

    # ===== EXAM COUNTS =====
    total_exams = db.query(Exam).count()

    draft_exams = db.query(Exam).filter(
        Exam.result_status == "draft"
    ).count()

    published_exams = db.query(Exam).filter(
        Exam.result_status == "published"
    ).count()

    locked_exams = db.query(Exam).filter(
        Exam.result_status == "locked"
    ).count()

    # ===== SUBMISSION COUNTS =====
    total_submissions = db.query(StudentSubmission).count()

    evaluated_submissions = db.query(StudentSubmission).filter(
        StudentSubmission.total_marks != None
    ).count()

    # ===== OVERALL AVERAGE =====
    overall_avg = db.query(
        func.avg(StudentSubmission.percentage)
    ).scalar() or 0

    # ===== GRADE DISTRIBUTION =====
    grades = db.query(
        StudentSubmission.grade,
        func.count(StudentSubmission.id)
    ).group_by(StudentSubmission.grade).all()

    grade_distribution = {
        grade: count for grade, count in grades if grade
    }

    # ===== RECENT SUBMISSIONS (Last 5 Evaluated) =====
    recent = db.query(StudentSubmission).filter(
        StudentSubmission.total_marks != None
    ).order_by(
        StudentSubmission.evaluated_at.desc()
    ).limit(5).all()

    recent_submissions = [
        {
            "roll": s.roll_number,
            "exam": s.exam.title if s.exam else "N/A",
            "marks": s.total_marks
        }
        for s in recent
    ]

    return {
        "total_exams": total_exams,
        "draft_exams": draft_exams,
        "published_exams": published_exams,
        "locked_exams": locked_exams,
        "total_submissions": total_submissions,
        "evaluated_submissions": evaluated_submissions,
        "overall_average": round(overall_avg, 2),
        "grade_distribution": grade_distribution,
        "recent_submissions": recent_submissions
    }