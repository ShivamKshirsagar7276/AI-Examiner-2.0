from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import shutil
import uuid

from core.database import get_db
from core import schemas
from core.models import StudentSubmission, Exam
from repositories import exam_repository

# Question Paper + Model Answer
from utils.pdf_text_extractor import extract_text_from_pdf
from llm.llm_question_parser import parse_question_paper
from llm.llm_model_answer_mapper import map_model_answers

# Student Processing
from ocr.azure_document_intelligence import run_document_intelligence_ocr
from vision.diagram_detector import detect_diagrams_from_pdf
from llm.llm_roll_extractor import extract_roll_number_with_llm
from llm.llm_full_student_mapper import map_student_answers_full_llm

# Evaluator
from llm.llm_evaluator import evaluate_answer, calculate_grade


router = APIRouter(prefix="/exams", tags=["Exams"])

print("🔥 FINAL EXAM_ROUTER WITH RESULT CONTROL + FULL EVALUATION LOADED 🔥")


# ============================================================
# HELPER: EXTRACT MARKS PER QUESTION
# ============================================================
def get_question_marks(structured_questions):

    marks_map = {}

    if not structured_questions:
        return marks_map

    for section in structured_questions.get("sections", []):

        for question in section.get("questions", []):

            main_qid = question.get("question_id")

            if question.get("sub_questions"):

                for sub in question.get("sub_questions"):

                    full_qid = f"{main_qid}{sub.get('sub_id')}"
                    marks_map[full_qid] = sub.get("marks", 0)

            else:

                marks_map[main_qid] = question.get("marks", 0)

    return marks_map


# ============================================================
# CREATE EXAM
# ============================================================
@router.post("/", response_model=schemas.ExamResponse)
def create_exam(
    exam: schemas.ExamCreate,
    db: Session = Depends(get_db)
):
    return exam_repository.create_exam(db, exam.dict())


# ============================================================
# LIST EXAMS
# ============================================================
@router.get("/", response_model=List[schemas.ExamResponse])
def list_exams(
    db: Session = Depends(get_db)
):
    return exam_repository.get_all_exams(db)


# ============================================================
# GET EXAM
# ============================================================
@router.get("/{exam_id}", response_model=schemas.ExamResponse)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db)
):

    exam = exam_repository.get_exam_by_id(db, exam_id)

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    return exam


# ============================================================
# DELETE EXAM
# ============================================================
@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db)
):

    exam = exam_repository.delete_exam(db, exam_id)

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    return {"message": "Exam deleted successfully"}


# ============================================================
# PUBLISH RESULT
# ============================================================
@router.put("/{exam_id}/publish-result")
def publish_result(
    exam_id: int,
    db: Session = Depends(get_db)
):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    if exam.result_status == "locked":
        raise HTTPException(
            status_code=400,
            detail="Result already locked"
        )

    exam.result_status = "published"
    exam.published_at = datetime.utcnow()

    db.commit()
    db.refresh(exam)

    return {
        "message": "Result published successfully",
        "status": exam.result_status
    }


# ============================================================
# LOCK RESULT
# ============================================================
@router.put("/{exam_id}/lock-result")
def lock_result(
    exam_id: int,
    db: Session = Depends(get_db)
):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Exam not found"
        )

    if exam.result_status != "published":
        raise HTTPException(
            status_code=400,
            detail="Publish result first"
        )

    exam.result_status = "locked"

    db.commit()
    db.refresh(exam)

    return {
        "message": "Result locked successfully",
        "status": exam.result_status
    }


# ============================================================
# UPLOAD QUESTION PAPER
# ============================================================
@router.post("/{exam_id}/question-paper")
def upload_question_paper(
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    exam = exam_repository.get_exam_by_id(db, exam_id)

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    storage_dir = "storage/question_papers"
    os.makedirs(storage_dir, exist_ok=True)

    file_path = os.path.join(storage_dir, f"exam_{exam_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    raw_text = extract_text_from_pdf(file_path)

    structured_questions = parse_question_paper(raw_text)

    exam.question_paper_path = file_path
    exam.structured_questions = structured_questions

    db.commit()
    db.refresh(exam)

    return {
        "message": "Question paper uploaded and parsed successfully",
        "structured_questions": structured_questions
    }


# ============================================================
# UPLOAD MODEL ANSWER
# ============================================================
@router.post("/{exam_id}/model-answer")
def upload_model_answer(
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    exam = exam_repository.get_exam_by_id(db, exam_id)

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    storage_dir = "storage/model_answers"
    os.makedirs(storage_dir, exist_ok=True)

    file_path = os.path.join(storage_dir, f"model_answer_{exam_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    raw_text = extract_text_from_pdf(file_path)

    structured_model_answers = map_model_answers(
        structured_questions=exam.structured_questions,
        raw_text=raw_text
    )

    exam.model_answer_path = file_path
    exam.structured_model_answers = structured_model_answers

    db.commit()
    db.refresh(exam)

    return {
        "message": "Model answer uploaded successfully",
        "structured_model_answers": structured_model_answers
    }


# ============================================================
# SUBMIT ANSWER SHEET
# ============================================================
@router.post("/{exam_id}/submit-answer-sheet")
def submit_answer_sheet(
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    exam = exam_repository.get_exam_by_id(db, exam_id)

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    storage_dir = "storage/uploads"
    os.makedirs(storage_dir, exist_ok=True)

    file_path = os.path.join(storage_dir, f"{uuid.uuid4()}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # OCR
    ocr_output = run_document_intelligence_ocr(file_path)

    # Diagram Detection
    diagram_results = detect_diagrams_from_pdf(file_path)

    # Roll Extraction
    roll_number = extract_roll_number_with_llm(ocr_output)

    # Answer Mapping
    mapped_answers = map_student_answers_full_llm(
        structured_questions=exam.structured_questions,
        ocr_output=ocr_output,
        diagram_results=diagram_results
    )

    submission = StudentSubmission(
        exam_id=exam_id,
        roll_number=roll_number,
        answer_sheet_path=file_path,
        ocr_output=ocr_output,
        mapped_answers=mapped_answers,
        diagram_results=diagram_results
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "message": "Submission processed successfully",
        "submission_id": submission.id,
        "roll_number": roll_number
    }


# ============================================================
# EVALUATE SUBMISSION
# ============================================================
@router.post("/{exam_id}/evaluate/{submission_id}")
def evaluate_submission(
    exam_id: int,
    submission_id: int,
    db: Session = Depends(get_db)
):

    exam = exam_repository.get_exam_by_id(db, exam_id)

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.result_status == "locked":
        raise HTTPException(
            status_code=400,
            detail="Result is locked. Evaluation not allowed."
        )

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id == submission_id,
        StudentSubmission.exam_id == exam_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    model_answers = exam.structured_model_answers or {}
    student_answers = submission.mapped_answers or {}
    marks_map = get_question_marks(exam.structured_questions)

    question_wise_results = {}

    grand_total = 0
    grand_max_total = 0

    for section in exam.structured_questions.get("sections", []):

        attempt_limit = section.get("attempt")
        section_scores = []

        for question in section.get("questions", []):

            main_qid = question.get("question_id")

            for sub in question.get("sub_questions", []):

                qid = f"{main_qid}{sub.get('sub_id')}"

                model_answer = model_answers.get(qid, "")
                student_data = student_answers.get(qid, {})

                student_text = student_data.get("answer_text", "")
                diagram_present = student_data.get("diagram_present", False)

                max_marks = marks_map.get(qid, 0)

                evaluation = evaluate_answer(
                    model_answer=model_answer,
                    student_answer=student_text,
                    max_marks=max_marks,
                    diagram_expected=False,
                    diagram_present=diagram_present
                )

                question_wise_results[qid] = {
                    "max_marks": max_marks,
                    **evaluation
                }

                section_scores.append({
                    "qid": qid,
                    "marks": evaluation["final_marks"],
                    "max_marks": max_marks
                })

        # Best Of Logic
        if attempt_limit:

            section_scores.sort(
                key=lambda x: x["marks"],
                reverse=True
            )

            selected = section_scores[:attempt_limit]
            selected_qids = [q["qid"] for q in selected]

        else:

            selected = section_scores
            selected_qids = [q["qid"] for q in section_scores]

        for q in section_scores:

            question_wise_results[q["qid"]]["ignored_due_to_best_of"] = (
                q["qid"] not in selected_qids
            )

        for q in selected:

            grand_total += q["marks"]
            grand_max_total += q["max_marks"]

    percentage = round(
        (grand_total / grand_max_total) * 100, 2
    ) if grand_max_total > 0 else 0

    grade = calculate_grade(percentage)

    submission.evaluation_json = question_wise_results
    submission.total_marks = round(grand_total, 2)
    submission.max_marks = grand_max_total
    submission.percentage = percentage
    submission.grade = grade

    if submission.evaluated_at:
        submission.reevaluated_at = datetime.utcnow()
    else:
        submission.evaluated_at = datetime.utcnow()

    db.commit()
    db.refresh(submission)

    return {
        "submission_id": submission.id,
        "total_obtained_marks": submission.total_marks,
        "total_max_marks": submission.max_marks,
        "percentage": submission.percentage,
        "grade": submission.grade,
        "question_wise": question_wise_results
    }

# ============================================================
# GET DETAILED SUBMISSION (FOR MARK PAGE)
# ============================================================
@router.get("/{exam_id}/submission/{submission_id}")
def get_submission_detail(
    exam_id: int,
    submission_id: int,
    db: Session = Depends(get_db)
):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Allow only if result is published or locked
    if exam.result_status == "draft":
        raise HTTPException(
            status_code=400,
            detail="Result not published yet"
        )

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id == submission_id,
        StudentSubmission.exam_id == exam_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submission_id": submission.id,
        "roll_number": submission.roll_number,
        "total_marks": submission.total_marks,
        "max_marks": submission.max_marks,
        "percentage": submission.percentage,
        "grade": submission.grade,
        "question_wise": submission.evaluation_json or {},
        "result_status": exam.result_status
    }

# ============================================================
# LIST SUBMISSIONS
# ============================================================
@router.get("/{exam_id}/submissions")
def list_submissions(
    exam_id: int,
    db: Session = Depends(get_db)
):

    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id
    ).all()

    return [
        {
            "submission_id": s.id,
            "roll_number": s.roll_number,
            "total_marks": s.total_marks,
            "percentage": s.percentage,
            "grade": s.grade
        }
        for s in submissions
    ]