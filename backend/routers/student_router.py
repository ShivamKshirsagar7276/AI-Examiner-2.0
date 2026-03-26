from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime

from core.database import get_db
from core.models import Student, StudentSubmission, Exam, StudentRevaluationRequest
from core.security import hash_password, verify_password, create_access_token
from core.schemas import StudentLogin, StudentToken, StudentRequestCreate
from jose import jwt, JWTError
from config import SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/student", tags=["Student"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/student/login")


def get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload    = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id = payload.get("student_id")
        if not student_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=401, detail="Student not found")
        return student
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login", response_model=StudentToken)
def student_login(data: StudentLogin, db: Session = Depends(get_db)):
    student = db.query(Student).filter(
        Student.roll_number == data.roll_number,
        Student.division    == data.division,
        Student.class_name  == data.class_name
    ).first()

    if not student or not verify_password(data.password, student.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "student_id":  student.id,
        "roll_number": student.roll_number,
        "division":    student.division,
        "class_name":  student.class_name
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "roll_number":  student.roll_number,
        "division":     student.division,
        "class_name":   student.class_name
    }


@router.get("/dashboard")
def student_dashboard(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)
):
    submissions = db.query(StudentSubmission).join(Exam).filter(
        StudentSubmission.roll_number == student.roll_number,
        Exam.division                 == student.division,
        Exam.class_name               == student.class_name,
        Exam.result_status            == "published"
    ).all()

    results = []
    for s in submissions:
        results.append({
            "submission_id": s.id,
            "exam_id":       s.exam_id,
            "exam_title":    s.exam.title,
            "subject":       s.exam.subject,
            "total_marks":   s.total_marks,
            "max_marks":     s.max_marks,
            "percentage":    s.percentage,
            "grade":         s.grade,
            "evaluated_at":  s.evaluated_at
        })

    return {
        "roll_number": student.roll_number,
        "division":    student.division,
        "class_name":  student.class_name,
        "results":     results
    }


@router.get("/result/{submission_id}")
def view_result(
    submission_id: int,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)
):
    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id          == submission_id,
        StudentSubmission.roll_number == student.roll_number
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Result not found")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()

    if exam.result_status != "published":
        raise HTTPException(status_code=403, detail="Result not published yet")

    return {
        "submission_id": submission.id,
        "exam_title":    exam.title,
        "subject":       exam.subject,
        "total_marks":   submission.total_marks,
        "max_marks":     submission.max_marks,
        "percentage":    submission.percentage,
        "grade":         submission.grade,
        "evaluated_at":  submission.evaluated_at
    }


@router.post("/apply/{submission_id}")
def apply_request(
    submission_id: int,
    request_type: str,
    reason: str = "",
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)
):
    if request_type not in ["photocopy", "revaluation"]:
        raise HTTPException(status_code=400, detail="request_type must be 'photocopy' or 'revaluation'")

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id          == submission_id,
        StudentSubmission.roll_number == student.roll_number
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    existing = db.query(StudentRevaluationRequest).filter(
        StudentRevaluationRequest.submission_id == submission_id,
        StudentRevaluationRequest.student_id    == student.id,
        StudentRevaluationRequest.request_type  == request_type,
        StudentRevaluationRequest.status        == "pending"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"You already have a pending {request_type} request")

    new_request = StudentRevaluationRequest(
        student_id    = student.id,
        submission_id = submission_id,
        request_type  = request_type,
        reason        = reason,
        status        = "pending"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return {
        "message":      f"{request_type.capitalize()} request submitted successfully",
        "request_id":   new_request.id,
        "request_type": request_type,
        "status":       "pending"
    }


@router.get("/my-requests")
def my_requests(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)
):
    requests = db.query(StudentRevaluationRequest).filter(
        StudentRevaluationRequest.student_id == student.id
    ).all()

    return [
        {
            "request_id":     r.id,
            "submission_id":  r.submission_id,
            "request_type":   r.request_type,
            "reason":         r.reason,
            "status":         r.status,
            "faculty_remark": r.faculty_remark,
            "requested_at":   r.requested_at,
            "resolved_at":    r.resolved_at
        }
        for r in requests
    ]


@router.get("/requests/all")
def get_all_requests(db: Session = Depends(get_db)):
    requests = db.query(StudentRevaluationRequest).all()

    return [
        {
            "id":             r.id,
            "submission_id":  r.submission_id,
            "roll_number":    r.student.roll_number,
            "request_type":   r.request_type,
            "reason":         r.reason,
            "status":         r.status,
            "faculty_remark": r.faculty_remark,
            "requested_at":   r.requested_at,
            "resolved_at":    r.resolved_at
        }
        for r in requests
    ]


@router.put("/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    faculty_remark: str = "",
    db: Session = Depends(get_db)
):
    request = db.query(StudentRevaluationRequest).filter(
        StudentRevaluationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status         = "approved"
    request.faculty_remark = faculty_remark
    request.resolved_at    = datetime.utcnow()
    db.commit()

    if request.request_type == "revaluation":
        submission = db.query(StudentSubmission).filter(
            StudentSubmission.id == request.submission_id
        ).first()

        if submission:
            from routers.exam_router import run_evaluation
            run_evaluation(exam=submission.exam, submission=submission, db=db)

    return {"message": "Request approved", "request_id": request_id}


@router.put("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    faculty_remark: str = "",
    db: Session = Depends(get_db)
):
    request = db.query(StudentRevaluationRequest).filter(
        StudentRevaluationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status         = "rejected"
    request.faculty_remark = faculty_remark
    request.resolved_at    = datetime.utcnow()
    db.commit()

    return {"message": "Request rejected", "request_id": request_id}


@router.get("/photocopy/{submission_id}")
def download_photocopy(
    submission_id: int,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)
):
    request = db.query(StudentRevaluationRequest).filter(
        StudentRevaluationRequest.submission_id == submission_id,
        StudentRevaluationRequest.student_id    == student.id,
        StudentRevaluationRequest.request_type  == "photocopy",
        StudentRevaluationRequest.status        == "approved"
    ).first()

    if not request:
        raise HTTPException(status_code=403, detail="Photocopy not approved yet")

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()

    from utils.photocopy_generator import generate_photocopy_pdf
    pdf_buffer = generate_photocopy_pdf(submission, exam)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=photocopy_{submission.roll_number}.pdf"}
    )