from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import shutil
import uuid

from core.database import get_db
from core import schemas
from core.models import StudentSubmission, Exam, Student
from repositories import exam_repository

from utils.pdf_text_extractor import extract_text_from_pdf
from llm.llm_question_parser import parse_question_paper
from llm.llm_model_answer_mapper import map_model_answers

from ocr.azure_document_intelligence import run_document_intelligence_ocr
from vision.diagram_detector import detect_diagrams_from_pdf
from llm.llm_roll_extractor import extract_roll_number_with_llm
from llm.llm_full_student_mapper import map_student_answers_full_llm

from llm.llm_evaluator import evaluate_answer, calculate_grade

from bulk_submission_service import create_bulk_job, run_bulk_job, get_job_progress


router = APIRouter(prefix="/exams", tags=["Exams"])

print("🔥 EXAM_ROUTER — SUBJECT-AWARE + TYPE-AWARE + DIAGRAM-AWARE GRADING LOADED 🔥")


# ============================================================
# HELPER: SAFELY EXTRACT MODEL ANSWER TEXT
# structured_model_answers stores dicts like:
#   { "Q1a": { "answer_text": "...", "max_marks": 2 } }
# This helper safely extracts the plain string in all cases.
# ============================================================
def _extract_model_answer_text(model_answers: dict, qid: str) -> str:
    raw = model_answers.get(qid, "")
    if isinstance(raw, dict):
        return raw.get("answer_text", "")
    return raw or ""


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
# HELPER: EXTRACT QUESTION TEXT PER QID
# ============================================================
def get_question_texts(structured_questions) -> dict:
    text_map = {}
    if not structured_questions:
        return text_map
    for section in structured_questions.get("sections", []):
        for question in section.get("questions", []):
            main_qid = question.get("question_id")
            if question.get("sub_questions"):
                for sub in question.get("sub_questions"):
                    full_qid = f"{main_qid}{sub.get('sub_id')}"
                    text_map[full_qid] = sub.get("text", "")
            else:
                text_map[main_qid] = question.get("text", "")
    return text_map


# ============================================================
# HELPER: CHECK IF QUESTION NEEDS A DIAGRAM
# ============================================================
def _question_needs_diagram(question_text: str, model_answer: str = "") -> bool:
    diagram_keywords = [
        "draw", "diagram", "sketch", "figure", "illustrate",
        "neat diagram", "with diagram", "show", "circuit",
        "flowchart", "uml", "dfa", "nfa", "state diagram",
        "er diagram", "graph", "tree", "waveform", "block diagram",
        "architecture", "layout"
    ]
    combined = (question_text + " " + model_answer).lower()
    return any(kw in combined for kw in diagram_keywords)


# ============================================================
# HELPER: CHECK IF MODEL ANSWER EXPECTS A DIAGRAM
# ============================================================
def _model_expects_diagram(model_answer: str) -> bool:
    return _question_needs_diagram("", model_answer)


# ============================================================
# RUN DIAGRAM DETECTION PER QUESTION
# Detects diagrams from PDF and maps them to each question
# that requires a diagram, with proper question context
# ============================================================
def run_per_question_diagram_detection(
    pdf_path: str,
    subject: str,
    structured_questions: dict,
    structured_model_answers: dict,
    marks_map: dict,
    question_texts: dict,
) -> dict:
    """
    Returns a dict: { qid -> diagram_result }
    Only runs detection for questions that need a diagram.
    Runs detection once per PDF page, then maps results to questions.
    """

    # Step 1 — Find which questions need diagrams
    diagram_questions = {}
    for qid, question_text in question_texts.items():
        # FIX: use helper to always get a plain string
        model_answer = _extract_model_answer_text(structured_model_answers, qid)
        if _question_needs_diagram(question_text, model_answer):
            diagram_questions[qid] = {
                "question_text": question_text,
                "model_answer":  model_answer,
                "max_marks":     marks_map.get(qid, 0),
            }

    if not diagram_questions:
        print("ℹ️ No diagram questions found — skipping diagram detection")
        return {}

    print(f"🖼️ Diagram detection needed for: {list(diagram_questions.keys())}")

    # Step 2 — Run detection once on full PDF (page-level results)
    first_qid = list(diagram_questions.keys())[0]
    first_q   = diagram_questions[first_qid]

    all_page_results = detect_diagrams_from_pdf(
        pdf_path                 = pdf_path,
        subject                  = subject,
        question_text            = first_q["question_text"],
        model_answer_description = first_q["model_answer"],
        max_marks                = first_q["max_marks"],
    )

    # Step 3 — Map page results to questions
    pages_with_diagrams = [
        r for r in all_page_results
        if r.get("diagram_present")
    ]

    print(f"✅ Pages with diagrams detected: {[r['page'] for r in pages_with_diagrams]}")

    qid_list    = list(diagram_questions.keys())
    qid_results = {}

    for i, qid in enumerate(qid_list):
        if i < len(pages_with_diagrams):
            page_result = pages_with_diagrams[i]

            grade = page_result.get("grade")
            if not grade or i > 0:
                from vision.diagram_detector import (
                    extract_diagram_regions,
                    classify_diagram_region,
                    grade_diagram_region
                )
                from pdf2image import convert_from_path

                POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"

                try:
                    pages = convert_from_path(
                        pdf_path,
                        dpi          = 300,
                        poppler_path = POPPLER_PATH,
                        first_page   = page_result["page"],
                        last_page    = page_result["page"]
                    )
                    if pages:
                        regions = extract_diagram_regions(pages[0])
                        if regions:
                            best_region = regions[0]
                            classified  = classify_diagram_region(
                                region_image = best_region["pil_image"],
                                page_number  = page_result["page"],
                                subject_hint = subject,
                            )
                            q_info = diagram_questions[qid]
                            grade  = grade_diagram_region(
                                region_image             = best_region["pil_image"],
                                classified               = classified,
                                question_text            = q_info["question_text"],
                                model_answer_description = q_info["model_answer"],
                                max_marks                = q_info["max_marks"],
                                subject                  = subject,
                                subject_persona          = f"You are a strict but fair {subject} professor.",
                            )
                            print(f"  ✅ Re-graded diagram for {qid}: {grade.get('awarded_marks')}/{q_info['max_marks']}")
                except Exception as e:
                    print(f"  ⚠️ Re-grading failed for {qid}: {e}")
                    grade = page_result.get("grade")

            qid_results[qid] = {
                "diagram_present":    True,
                "diagram_type":       page_result.get("diagram_type", ""),
                "diagram_labels":     page_result.get("diagram_labels", []),
                "diagram_components": page_result.get("diagram_components", []),
                "page":               page_result.get("page"),
                "grade":              grade,
            }
        else:
            print(f"  ⚠️ No diagram found for {qid}")
            qid_results[qid] = {
                "diagram_present": False,
                "diagram_type":    "",
                "diagram_labels":  [],
                "grade":           None,
            }

    return qid_results


# ============================================================
# HELPER: AUTO CREATE STUDENT ACCOUNT
# ============================================================
def auto_create_student(exam, roll_number, db):
    from core.security import hash_password

    existing = db.query(Student).filter(
        Student.roll_number == roll_number,
        Student.division    == exam.division,
        Student.class_name  == exam.class_name
    ).first()

    if not existing:
        student = Student(
            roll_number = roll_number,
            division    = exam.division,
            class_name  = exam.class_name,
            password    = hash_password(roll_number)
        )
        db.add(student)
        db.commit()
        print(f"✅ Student auto-created: {roll_number} | {exam.division} | {exam.class_name}")
    else:
        print(f"ℹ Student exists: {roll_number} | {exam.division} | {exam.class_name}")


# ============================================================
# HELPER: EVALUATE ONE SUB-QUESTION
# ============================================================
def _evaluate_sub(
    qid, model_answer, student_data, max_marks,
    subject, question_text, explain_mode,
    diagram_qid_results=None
):
    student_text    = student_data.get("answer_text", "")
    diagram_present = student_data.get("diagram_present", False)
    diagram_labels  = student_data.get("diagram_labels", [])
    diagram_grade   = student_data.get("diagram_grade") or {}
    diagram_type    = student_data.get("diagram_type", "")

    if diagram_qid_results and qid in diagram_qid_results:
        q_diagram       = diagram_qid_results[qid]
        diagram_present = q_diagram.get("diagram_present", diagram_present)
        diagram_labels  = q_diagram.get("diagram_labels", diagram_labels)
        diagram_type    = q_diagram.get("diagram_type", diagram_type)
        diagram_grade   = q_diagram.get("grade") or diagram_grade
        print(f"  🖼️ {qid} — Using per-question diagram result: present={diagram_present}, grade={diagram_grade.get('awarded_marks') if diagram_grade else None}")

    diagram_expected = (
        diagram_present or
        _model_expects_diagram(model_answer) or
        _question_needs_diagram(question_text)
    )

    evaluation = evaluate_answer(
        model_answer     = model_answer,
        student_answer   = student_text,
        max_marks        = max_marks,
        subject          = subject,
        question_text    = question_text,
        diagram_expected = diagram_expected,
        diagram_present  = diagram_present,
        diagram_labels   = diagram_labels,
        diagram_grade    = diagram_grade,
        explain          = explain_mode,
    )

    return {
        "result_entry": {
            "max_marks":              max_marks,
            "answer_type":            evaluation.get("answer_type", "theory"),
            "answer_types":           evaluation.get("answer_types", ["theory"]),
            "semantic_score":         evaluation.get("semantic_score"),
            "coverage_score":         evaluation.get("coverage_score"),
            "quality_score":          evaluation.get("quality_score"),
            "answer_type_score":      evaluation.get("answer_type_score"),
            "diagram_score":          evaluation.get("diagram_score"),
            "diagram_awarded_marks":  evaluation.get("diagram_awarded_marks", 0),
            "diagram_type":           diagram_type,
            "final_marks":            evaluation.get("final_marks"),
            "verdict":                evaluation.get("verdict", ""),
            "reasoning":              evaluation.get("reasoning", {}),
            "ignored_due_to_best_of": False,
        },
        "score_entry": {
            "qid":       qid,
            "marks":     evaluation["final_marks"],
            "max_marks": max_marks,
        }
    }


# ============================================================
# HELPER: APPLY BEST-OF SELECTION
# ============================================================
def _apply_best_of(scores, attempt_limit, results):
    if not attempt_limit:
        selected_qids = [q["qid"] for q in scores]
        selected      = scores
    else:
        sorted_scores = sorted(scores, key=lambda x: x["marks"], reverse=True)
        selected      = sorted_scores[:attempt_limit]
        selected_qids = [q["qid"] for q in selected]

    for q in scores:
        results[q["qid"]]["ignored_due_to_best_of"] = (
            q["qid"] not in selected_qids
        )

    return selected


# ============================================================
# CORE EVALUATION — subject-aware, type-aware, diagram-aware
# ============================================================
def run_evaluation(exam, submission, db, explain_mode=False):

    model_answers   = exam.structured_model_answers or {}
    student_answers = submission.mapped_answers or {}
    marks_map       = get_question_marks(exam.structured_questions)
    question_texts  = get_question_texts(exam.structured_questions)

    subject = exam.subject or ""

    # Run per-question diagram detection if answer sheet exists
    diagram_qid_results = {}
    if submission.answer_sheet_path and os.path.exists(submission.answer_sheet_path):
        try:
            diagram_qid_results = run_per_question_diagram_detection(
                pdf_path                 = submission.answer_sheet_path,
                subject                  = subject,
                structured_questions     = exam.structured_questions,
                structured_model_answers = model_answers,
                marks_map                = marks_map,
                question_texts           = question_texts,
            )
            print(f"✅ Per-question diagram detection done: {list(diagram_qid_results.keys())}")
        except Exception as e:
            print(f"⚠️ Per-question diagram detection failed: {e}")

    question_wise_results = {}
    grand_total           = 0
    grand_max_total       = 0

    for section in exam.structured_questions.get("sections", []):

        section_attempt = section.get("attempt")
        section_scores  = []

        for question in section.get("questions", []):
            main_qid = question.get("question_id")

            question_attempt = question.get("attempt")
            question_scores  = []

            for sub in question.get("sub_questions", []):
                qid           = f"{main_qid}{sub.get('sub_id')}"
                # FIX: use helper to always get a plain string
                model_answer  = _extract_model_answer_text(model_answers, qid)
                student_data  = student_answers.get(qid, {})
                max_marks     = marks_map.get(qid, 0)
                question_text = question_texts.get(qid, "")

                evaluated = _evaluate_sub(
                    qid                 = qid,
                    model_answer        = model_answer,
                    student_data        = student_data,
                    max_marks           = max_marks,
                    subject             = subject,
                    question_text       = question_text,
                    explain_mode        = explain_mode,
                    diagram_qid_results = diagram_qid_results,
                )

                question_wise_results[qid] = evaluated["result_entry"]
                question_scores.append(evaluated["score_entry"])
                section_scores.append(evaluated["score_entry"])

            if question_attempt and not section_attempt:
                selected = _apply_best_of(
                    question_scores, question_attempt, question_wise_results
                )
                for q in selected:
                    grand_total     += q["marks"]
                    grand_max_total += q["max_marks"]

            elif not question_attempt and not section_attempt:
                for q in question_scores:
                    question_wise_results[q["qid"]]["ignored_due_to_best_of"] = False
                    grand_total     += q["marks"]
                    grand_max_total += q["max_marks"]

        if section_attempt:
            selected = _apply_best_of(
                section_scores, section_attempt, question_wise_results
            )
            for q in selected:
                grand_total     += q["marks"]
                grand_max_total += q["max_marks"]

    percentage = round((grand_total / grand_max_total) * 100, 2) if grand_max_total > 0 else 0
    grade      = calculate_grade(percentage)

    submission.evaluation_json = question_wise_results
    submission.total_marks     = round(grand_total, 2)
    submission.max_marks       = grand_max_total
    submission.percentage      = percentage
    submission.grade           = grade

    if submission.evaluated_at:
        submission.reevaluated_at = datetime.utcnow()
    else:
        submission.evaluated_at = datetime.utcnow()

    db.commit()
    db.refresh(submission)

    auto_create_student(exam, submission.roll_number, db)

    return {
        "total_marks":   submission.total_marks,
        "max_marks":     submission.max_marks,
        "percentage":    submission.percentage,
        "grade":         submission.grade,
        "question_wise": question_wise_results,
    }


# ============================================================
# CREATE EXAM
# ============================================================
@router.post("/", response_model=schemas.ExamResponse)
def create_exam(exam: schemas.ExamCreate, db: Session = Depends(get_db)):
    return exam_repository.create_exam(db, exam.dict())


# ============================================================
# LIST EXAMS
# ============================================================
@router.get("/", response_model=List[schemas.ExamResponse])
def list_exams(db: Session = Depends(get_db)):
    return exam_repository.get_all_exams(db)


# ============================================================
# GET EXAM
# ============================================================
@router.get("/{exam_id}", response_model=schemas.ExamResponse)
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = exam_repository.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


# ============================================================
# DELETE EXAM
# ============================================================
@router.delete("/{exam_id}")
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = exam_repository.delete_exam(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return {"message": "Exam deleted successfully"}


# ============================================================
# PUBLISH RESULT
# ============================================================
@router.put("/{exam_id}/publish-result")
def publish_result(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.result_status == "locked":
        raise HTTPException(status_code=400, detail="Result already locked")
    exam.result_status = "published"
    exam.published_at  = datetime.utcnow()
    db.commit()
    db.refresh(exam)
    return {"message": "Result published successfully", "status": exam.result_status}


# ============================================================
# LOCK RESULT
# ============================================================
@router.put("/{exam_id}/lock-result")
def lock_result(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.result_status != "published":
        raise HTTPException(status_code=400, detail="Publish result first")
    exam.result_status = "locked"
    db.commit()
    db.refresh(exam)
    return {"message": "Result locked successfully", "status": exam.result_status}


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
    raw_text             = extract_text_from_pdf(file_path)
    structured_questions = parse_question_paper(raw_text)
    exam.question_paper_path  = file_path
    exam.structured_questions = structured_questions
    db.commit()
    db.refresh(exam)
    return {
        "message":              "Question paper uploaded and parsed successfully",
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
    raw_text                 = extract_text_from_pdf(file_path)
    structured_model_answers = map_model_answers(
        structured_questions = exam.structured_questions,
        raw_text             = raw_text
    )
    exam.model_answer_path        = file_path
    exam.structured_model_answers = structured_model_answers
    db.commit()
    db.refresh(exam)
    return {
        "message":                  "Model answer uploaded successfully",
        "structured_model_answers": structured_model_answers
    }


# ============================================================
# SUBMIT SINGLE ANSWER SHEET
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

    ocr_output = run_document_intelligence_ocr(file_path)

    diagram_results = detect_diagrams_from_pdf(
        pdf_path = file_path,
        subject  = exam.subject or "",
    )

    roll_number    = extract_roll_number_with_llm(ocr_output)
    mapped_answers = map_student_answers_full_llm(
        structured_questions = exam.structured_questions,
        ocr_output           = ocr_output,
        diagram_results      = diagram_results
    )

    submission = StudentSubmission(
        exam_id           = exam_id,
        roll_number       = roll_number,
        answer_sheet_path = file_path,
        ocr_output        = ocr_output,
        mapped_answers    = mapped_answers,
        diagram_results   = diagram_results
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {
        "message":       "Submission processed successfully",
        "submission_id": submission.id,
        "roll_number":   roll_number
    }


# ============================================================
# BULK SUBMIT + AUTO EVALUATE
# ============================================================
@router.post(
    "/{exam_id}/bulk-submit-sheets",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type":        "array",
                                "items":       {"type": "string", "format": "binary"},
                                "description": "Select multiple answer sheet PDFs"
                            }
                        },
                        "required": ["files"]
                    }
                }
            },
            "required": True
        }
    }
)
def bulk_submit_and_evaluate(
    exam_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    exam = exam_repository.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if not exam.structured_questions:
        raise HTTPException(status_code=400, detail="Upload question paper first")
    if not exam.structured_model_answers:
        raise HTTPException(status_code=400, detail="Upload model answer first")

    job = create_bulk_job(files=files, exam=exam, db=db)

    background_tasks.add_task(
        run_bulk_job,
        job_id            = job.id,
        exam_id           = exam_id,
        run_evaluation_fn = run_evaluation
    )

    return {
        "message":  f"Bulk job started for {job.total} sheets (5 in parallel)",
        "job_id":   job.id,
        "total":    job.total,
        "poll_url": f"/exams/{exam_id}/bulk-job/{job.id}"
    }


# ============================================================
# GET BULK JOB PROGRESS
# ============================================================
@router.get("/{exam_id}/bulk-job/{job_id}")
def get_bulk_job_status(
    exam_id: int,
    job_id: int,
    db: Session = Depends(get_db)
):
    progress = get_job_progress(job_id=job_id, db=db)
    if not progress:
        raise HTTPException(status_code=404, detail="Bulk job not found")
    if progress["exam_id"] != exam_id:
        raise HTTPException(status_code=403, detail="Job does not belong to this exam")
    return progress


# ============================================================
# EVALUATE SINGLE SUBMISSION
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
        raise HTTPException(status_code=400, detail="Result is locked. Evaluation not allowed.")
    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id      == submission_id,
        StudentSubmission.exam_id == exam_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    evaluation = run_evaluation(
        exam         = exam,
        submission   = submission,
        db           = db,
        explain_mode = True
    )

    return {
        "submission_id":        submission.id,
        "total_obtained_marks": evaluation["total_marks"],
        "total_max_marks":      evaluation["max_marks"],
        "percentage":           evaluation["percentage"],
        "grade":                evaluation["grade"],
        "question_wise":        evaluation["question_wise"]
    }


# ============================================================
# GENERATE REASONING ON DEMAND
# ============================================================
@router.post("/{exam_id}/submission/{submission_id}/generate-reasoning")
def generate_reasoning_on_demand(
    exam_id: int,
    submission_id: int,
    db: Session = Depends(get_db)
):
    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id      == submission_id,
        StudentSubmission.exam_id == exam_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not submission.evaluation_json:
        raise HTTPException(status_code=404, detail="Evaluate the submission first")

    exam           = db.query(Exam).filter(Exam.id == exam_id).first()
    model_answers  = exam.structured_model_answers or {}
    subject        = exam.subject or ""
    question_texts = get_question_texts(exam.structured_questions)
    eval_data      = submission.evaluation_json
    updated        = {}

    for qid, data in eval_data.items():
        existing_reasoning = data.get("reasoning", {})

        if existing_reasoning.get("components"):
            updated[qid] = data
            continue

        student_data    = (submission.mapped_answers or {}).get(qid, {})
        # FIX: use helper to always get a plain string
        model_answer    = _extract_model_answer_text(model_answers, qid)
        student_text    = student_data.get("answer_text", "")
        diagram_present = student_data.get("diagram_present", False)
        diagram_labels  = student_data.get("diagram_labels", [])
        diagram_grade   = student_data.get("diagram_grade") or {}
        max_marks       = data.get("max_marks", 0)
        question_text   = question_texts.get(qid, "")

        diagram_expected = (
            diagram_present or
            _model_expects_diagram(model_answer) or
            _question_needs_diagram(question_text)
        )

        evaluation = evaluate_answer(
            model_answer     = model_answer,
            student_answer   = student_text,
            max_marks        = max_marks,
            subject          = subject,
            question_text    = question_text,
            diagram_expected = diagram_expected,
            diagram_present  = diagram_present,
            diagram_labels   = diagram_labels,
            diagram_grade    = diagram_grade,
            explain          = True,
        )

        updated[qid] = {
            **data,
            "answer_type":  evaluation.get("answer_type", data.get("answer_type", "theory")),
            "answer_types": evaluation.get("answer_types", data.get("answer_types", ["theory"])),
            "reasoning":    evaluation.get("reasoning", {}),
        }

    submission.evaluation_json = updated
    db.commit()

    return {"message": "Reasoning generated successfully"}


# ============================================================
# GET DETAILED SUBMISSION
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
    if exam.result_status == "draft":
        raise HTTPException(status_code=400, detail="Result not published yet")
    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id      == submission_id,
        StudentSubmission.exam_id == exam_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "submission_id": submission.id,
        "roll_number":   submission.roll_number,
        "total_marks":   submission.total_marks,
        "max_marks":     submission.max_marks,
        "percentage":    submission.percentage,
        "grade":         submission.grade,
        "question_wise": submission.evaluation_json or {},
        "result_status": exam.result_status
    }


# ============================================================
# GET AI REASONING
# ============================================================
@router.get("/{exam_id}/submission/{submission_id}/reasoning")
def get_ai_reasoning(
    exam_id: int,
    submission_id: int,
    db: Session = Depends(get_db)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    submission = db.query(StudentSubmission).filter(
        StudentSubmission.id      == submission_id,
        StudentSubmission.exam_id == exam_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not submission.evaluation_json:
        raise HTTPException(status_code=404, detail="Evaluation not done yet")

    evaluation          = submission.evaluation_json
    questions_reasoning = []

    for qid, data in evaluation.items():
        reasoning = data.get("reasoning", {})
        questions_reasoning.append({
            "question_id":            qid,
            "max_marks":              data.get("max_marks", 0),
            "final_marks":            data.get("final_marks", 0),
            "marks_cut":              round(data.get("max_marks", 0) - data.get("final_marks", 0), 2),
            "answer_type":            data.get("answer_type", "theory"),
            "answer_types":           data.get("answer_types", ["theory"]),
            "semantic_score":         data.get("semantic_score", 0),
            "coverage_score":         data.get("coverage_score", 0),
            "quality_score":          data.get("quality_score", 0),
            "answer_type_score":      data.get("answer_type_score", 0),
            "diagram_score":          data.get("diagram_score", 0),
            "diagram_awarded_marks":  data.get("diagram_awarded_marks", 0),
            "diagram_type":           data.get("diagram_type", ""),
            "verdict":                data.get("verdict", ""),
            "confidence":             reasoning.get("confidence", 0),
            "components":             reasoning.get("components", []),
            "overall_feedback":       reasoning.get("overall_feedback", ""),
            "ignored_due_to_best_of": data.get("ignored_due_to_best_of", False)
        })

    return {
        "submission_id": submission.id,
        "roll_number":   submission.roll_number,
        "subject":       exam.subject,
        "total_marks":   submission.total_marks,
        "max_marks":     submission.max_marks,
        "marks_cut":     round((submission.max_marks or 0) - (submission.total_marks or 0), 2),
        "percentage":    submission.percentage,
        "grade":         submission.grade,
        "evaluated_at":  submission.evaluated_at,
        "questions":     questions_reasoning
    }


# ============================================================
# LIST SUBMISSIONS
# ============================================================
@router.get("/{exam_id}/submissions")
def list_submissions(exam_id: int, db: Session = Depends(get_db)):
    submissions = db.query(StudentSubmission).filter(
        StudentSubmission.exam_id == exam_id
    ).all()
    return [
        {
            "submission_id": s.id,
            "roll_number":   s.roll_number,
            "total_marks":   s.total_marks,
            "percentage":    s.percentage,
            "grade":         s.grade
        }
        for s in submissions
    ]