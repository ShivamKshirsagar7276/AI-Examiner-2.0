"""
bulk_submission_service.py  (place at backend/ root, same level as main.py)

Parallel processing — 5 sheets at a time using ThreadPoolExecutor.
For 60-70 sheets: ~14 batches × 4 min = ~56 min instead of 4.5 hours.

Flow:
  1. create_bulk_job()  → saves all files to disk, creates BulkJob row, returns job
  2. run_bulk_job()     → background task, processes 5 sheets in parallel,
                          updates BulkJob.processed after every sheet completes
  3. get_job_progress() → called by GET endpoint so frontend can poll live progress
"""

import os
import uuid
import shutil
from datetime import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import StudentSubmission, Exam, BulkJob
from ocr.azure_document_intelligence import run_document_intelligence_ocr
from vision.diagram_detector import detect_diagrams_from_pdf
from llm.llm_roll_extractor import extract_roll_number_with_llm
from llm.llm_full_student_mapper import map_student_answers_full_llm


STORAGE_DIR  = "storage/uploads"
PARALLEL_WORKERS = 5   # 5 sheets processed at the same time


# ============================================================
# STEP 1 — SAVE ALL FILES + CREATE JOB ROW
# ============================================================

def create_bulk_job(
    files: List[UploadFile],
    exam: Exam,
    db: Session
) -> BulkJob:

    os.makedirs(STORAGE_DIR, exist_ok=True)

    saved_paths    = []
    original_names = []

    for file in files:
        ext       = os.path.splitext(file.filename)[-1] or ".pdf"
        file_path = os.path.join(STORAGE_DIR, f"{uuid.uuid4()}{ext}")
        file.file.seek(0)
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        saved_paths.append(file_path)
        original_names.append(file.filename)

    initial_results = [
        {
            "filename":      name,
            "file_path":     path,
            "status":        "pending",
            "success":       None,
            "submission_id": None,
            "roll_number":   None,
            "total_marks":   None,
            "max_marks":     None,
            "percentage":    None,
            "grade":         None,
            "error":         None
        }
        for name, path in zip(original_names, saved_paths)
    ]

    job = BulkJob(
        exam_id=exam.id,
        total=len(files),
        processed=0,
        succeeded=0,
        failed=0,
        status="pending",
        results=initial_results
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


# ============================================================
# PROCESS ONE SHEET — runs inside a thread
# Each thread gets its own DB session (sessions are not thread safe)
# ============================================================

def _process_one_sheet(
    index: int,
    sheet: dict,
    exam_id: int,
    run_evaluation_fn
) -> dict:
    """
    Processes a single sheet completely:
      OCR → Diagram → Roll → Map → Save → Evaluate
    Returns a result dict with success/failure info.
    Each call opens and closes its own DB session.
    """
    db: Session = SessionLocal()

    try:
        exam      = db.query(Exam).filter(Exam.id == exam_id).first()
        file_path = sheet["file_path"]

        print(f"📄 [{index + 1}] Starting — {sheet['filename']}")

        # OCR
        ocr_output = run_document_intelligence_ocr(file_path)

        # Diagram detection
        diagram_results = detect_diagrams_from_pdf(file_path)

        # Roll number extraction
        roll_number = extract_roll_number_with_llm(ocr_output)
        if not roll_number:
            raise ValueError("Could not extract roll number from sheet")

        # Answer mapping
        mapped_answers = map_student_answers_full_llm(
            structured_questions=exam.structured_questions,
            ocr_output=ocr_output,
            diagram_results=diagram_results
        )

        # Save submission to DB
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

        # Auto evaluate
        evaluation = run_evaluation_fn(exam=exam, submission=submission, db=db)

        print(f"✅ [{index + 1}] Done — Roll: {roll_number} | Marks: {evaluation['total_marks']}/{evaluation['max_marks']}")

        return {
            "index":         index,
            "status":        "done",
            "success":       True,
            "submission_id": submission.id,
            "roll_number":   roll_number,
            "total_marks":   evaluation["total_marks"],
            "max_marks":     evaluation["max_marks"],
            "percentage":    evaluation["percentage"],
            "grade":         evaluation["grade"],
            "error":         None
        }

    except Exception as e:
        db.rollback()
        print(f"❌ [{index + 1}] Failed — {sheet['filename']} | Error: {str(e)}")
        return {
            "index":         index,
            "status":        "done",
            "success":       False,
            "submission_id": None,
            "roll_number":   None,
            "total_marks":   None,
            "max_marks":     None,
            "percentage":    None,
            "grade":         None,
            "error":         str(e)
        }

    finally:
        db.close()


# ============================================================
# STEP 2 — BACKGROUND TASK (parallel)
# ============================================================

def run_bulk_job(job_id: int, exam_id: int, run_evaluation_fn):
    """
    Processes all sheets in parallel — PARALLEL_WORKERS at a time.
    Updates BulkJob progress after every single sheet completes
    so frontend polling always shows the latest count.
    """
    db: Session = SessionLocal()

    try:
        job = db.query(BulkJob).filter(BulkJob.id == job_id).first()

        if not job:
            return

        job.status = "processing"
        db.commit()

        results = list(job.results)

        # Submit all sheets to thread pool — max PARALLEL_WORKERS running at once
        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:

            # Map future → index so we know which sheet finished
            future_to_index = {
                executor.submit(
                    _process_one_sheet,
                    index,
                    sheet,
                    exam_id,
                    run_evaluation_fn
                ): index
                for index, sheet in enumerate(results)
            }

            # as_completed fires as soon as ANY sheet finishes
            for future in as_completed(future_to_index):

                sheet_result = future.result()
                index        = sheet_result["index"]

                # Update that sheet's result
                results[index].update({
                    "status":        sheet_result["status"],
                    "success":       sheet_result["success"],
                    "submission_id": sheet_result["submission_id"],
                    "roll_number":   sheet_result["roll_number"],
                    "total_marks":   sheet_result["total_marks"],
                    "max_marks":     sheet_result["max_marks"],
                    "percentage":    sheet_result["percentage"],
                    "grade":         sheet_result["grade"],
                    "error":         sheet_result["error"]
                })

                if sheet_result["success"]:
                    job.succeeded += 1
                else:
                    job.failed += 1

                # Increment processed count immediately — frontend sees this
                job.processed += 1
                job.results    = results
                db.commit()

                print(f"📊 Progress: {job.processed}/{job.total} sheets done")

        job.status       = "done"
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        print(f"💥 Bulk job crashed: {str(e)}")
        if job:
            job.status = "failed"
            db.commit()

    finally:
        db.close()


# ============================================================
# PROGRESS QUERY — used by GET /bulk-job/{job_id}
# ============================================================

def get_job_progress(job_id: int, db: Session) -> dict | None:

    job = db.query(BulkJob).filter(BulkJob.id == job_id).first()

    if not job:
        return None

    return {
        "job_id":       job.id,
        "exam_id":      job.exam_id,
        "status":       job.status,
        "total":        job.total,
        "processed":    job.processed,
        "succeeded":    job.succeeded,
        "failed":       job.failed,
        "percent":      round((job.processed / job.total) * 100) if job.total else 0,
        "results":      job.results,
        "created_at":   job.created_at,
        "completed_at": job.completed_at
    }