from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from core.database import get_db
from core.models import RevaluationRequest, StudentSubmission, Exam

router = APIRouter(prefix="/revaluation", tags=["Revaluation"])


# ============================================
# STUDENT REQUEST REVALUATION
# ============================================
@router.post("/request")
def request_revaluation(
    submission_id: int,
    student_id: int,
    request_type: str,  # revaluation / photocopy
    db: Session = Depends(get_db)
):

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Prevent duplicate pending request
    existing = db.query(RevaluationRequest).filter(
        RevaluationRequest.submission_id == submission_id,
        RevaluationRequest.status == "pending"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Request already pending")

    request = RevaluationRequest(
        submission_id=submission_id,
        student_id=student_id,
        request_type=request_type,
        status="pending"
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "message": "Revaluation request submitted",
        "request_id": request.id,
        "status": request.status
    }


# ============================================
# FACULTY VIEW ALL REQUESTS
# ============================================
@router.get("/all")
def get_all_requests(db: Session = Depends(get_db)):

    requests = db.query(RevaluationRequest).all()

    return [
        {
            "id": r.id,
            "submission_id": r.submission_id,
            "student_id": r.student_id,
            "type": r.request_type,
            "status": r.status,
            "requested_at": r.requested_at
        }
        for r in requests
    ]


# ============================================
# FACULTY APPROVE REQUEST
# ============================================
@router.put("/{request_id}/approve")
def approve_request(request_id: int, db: Session = Depends(get_db)):

    request = db.query(RevaluationRequest).filter(
        RevaluationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status = "approved"
    request.resolved_at = datetime.utcnow()

    db.commit()

    return {"message": "Request approved"}


# ============================================
# FACULTY REJECT REQUEST
# ============================================
@router.put("/{request_id}/reject")
def reject_request(
    request_id: int,
    faculty_remark: str,
    db: Session = Depends(get_db)
):

    request = db.query(RevaluationRequest).filter(
        RevaluationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status = "rejected"
    request.faculty_remark = faculty_remark
    request.resolved_at = datetime.utcnow()

    db.commit()

    return {"message": "Request rejected"}