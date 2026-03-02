from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth_utils import require_student
from core.models import StudentSubmission, Exam

router = APIRouter(
    prefix="/student",
    tags=["Student"]
)


# ==============================
# Student Dashboard
# ==============================
@router.get("/dashboard")
def student_dashboard(
    db: Session = Depends(get_db),
    student=Depends(require_student)
):

    submissions = db.query(StudentSubmission).all()

    return {
        "message": f"Welcome {student.username}",
        "total_submissions": len(submissions)
    }


# ==============================
# View Result (Only if Published)
# ==============================
@router.get("/result/{submission_id}")
def view_result(
    submission_id: int,
    db: Session = Depends(get_db),
    student=Depends(require_student)
):

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id == submission_id
    ).first()

    if not submission:
        return {"error": "Submission not found"}

    exam = db.query(Exam).filter(
        Exam.id == submission.exam_id
    ).first()

    if exam.result_status != "published":
        return {"message": "Result not published yet"}

    return {
        "total_marks": submission.total_marks,
        "percentage": submission.percentage,
        "grade": submission.grade
    }