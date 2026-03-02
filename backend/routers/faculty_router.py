from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth_utils import require_faculty
from core.models import RevaluationRequest

router = APIRouter(
    prefix="/faculty",
    tags=["Faculty"]
)


# ==============================
# Faculty Dashboard
# ==============================
@router.get("/dashboard")
def faculty_dashboard(
    db: Session = Depends(get_db),
    faculty=Depends(require_faculty)
):

    pending_requests = db.query(RevaluationRequest).filter(
        RevaluationRequest.status == "pending"
    ).all()

    return {
        "message": f"Welcome {faculty.username}",
        "pending_requests": len(pending_requests)
    }