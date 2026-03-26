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
        "percentage":  submission.percentage,
        "grade":       submission.grade
    }


# ============================================================
# NEW — FACULTY AI REASONING ENDPOINT
# ============================================================
@router.get("/faculty/{submission_id}/reasoning")
def get_faculty_reasoning(submission_id: int, db: Session = Depends(get_db)):
    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not submission.evaluation_json:
        raise HTTPException(status_code=404, detail="Evaluation not done yet for this submission")

    evaluation = submission.evaluation_json
    questions_reasoning = []

    for qid, data in evaluation.items():
        reasoning = data.get("reasoning", {})
        questions_reasoning.append({
            "question_id":            qid,
            "max_marks":              data.get("max_marks", 0),
            "final_marks":            data.get("final_marks", 0),
            "marks_cut":              round(data.get("max_marks", 0) - data.get("final_marks", 0), 2),
            "semantic_score":         data.get("semantic_score", 0),
            "coverage_score":         data.get("coverage_score", 0),
            "quality_score":          data.get("quality_score", 0),
            "diagram_score":          data.get("diagram_score", 0),
            "confidence":             reasoning.get("confidence", 0),
            "components":             reasoning.get("components", []),
            "overall_feedback":       reasoning.get("overall_feedback", ""),
            "ignored_due_to_best_of": data.get("ignored_due_to_best_of", False)
        })

    return {
        "submission_id": submission.id,
        "roll_number":   submission.roll_number,
        "total_marks":   submission.total_marks,
        "max_marks":     submission.max_marks,
        "marks_cut":     round((submission.max_marks or 0) - (submission.total_marks or 0), 2),
        "percentage":    submission.percentage,
        "grade":         submission.grade,
        "evaluated_at":  submission.evaluated_at,
        "questions":     questions_reasoning
    }