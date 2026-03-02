from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import StudentSubmission, Exam

router = APIRouter(prefix="/results", tags=["Public Results"])


@router.get("/{exam_id}/{roll_number}")
def get_public_result(exam_id: int, roll_number: str, db: Session = Depends(get_db)):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.result_status != "published":
        raise HTTPException(status_code=403, detail="Result not published yet")

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id,
        StudentSubmission.roll_number == roll_number
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Result not found")

    return {
        "roll_number": submission.roll_number,
        "total_marks": submission.total_marks,
        "percentage": submission.percentage,
        "grade": submission.grade
    }