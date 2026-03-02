from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


# ==================================================
# USER MODEL
# ==================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    # For future revaluation relation
    revaluation_requests = relationship("RevaluationRequest", back_populates="student")


# ==================================================
# EXAM MODEL (WITH RESULT CONTROL)
# ==================================================
class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    division = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    total_marks = Column(Integer, nullable=False)

    # 🔥 NEW RESULT CONTROL SYSTEM
    result_status = Column(String, default="draft")  # draft / published / locked
    published_at = Column(DateTime, nullable=True)

    question_paper_path = Column(String, nullable=True)
    structured_questions = Column(JSON, nullable=True)

    model_answer_path = Column(String, nullable=True)
    structured_model_answers = Column(JSON, nullable=True)

    submissions = relationship("StudentSubmission", back_populates="exam")


# ==================================================
# STUDENT SUBMISSION MODEL (FINAL PROFESSIONAL VERSION)
# ==================================================
class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(Integer, primary_key=True, index=True)

    exam_id = Column(Integer, ForeignKey("exams.id"))
    roll_number = Column(String, nullable=False)

    answer_sheet_path = Column(String, nullable=True)

    # Processing Data
    ocr_output = Column(JSON, nullable=True)    
    structured_answers = Column(JSON, nullable=True)
    mapped_answers = Column(JSON, nullable=True)
    diagram_results = Column(JSON, nullable=True)

    # ================================
    # EVALUATION SYSTEM
    # ================================
    evaluation_json = Column(JSON, nullable=True)
    total_marks = Column(Float, nullable=True)
    max_marks = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    grade = Column(String, nullable=True)

    evaluated_at = Column(DateTime, nullable=True)
    reevaluated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="submissions")

    # For future revaluation relation
    revaluation_requests = relationship("RevaluationRequest", back_populates="submission")


# ==================================================
# REVALUATION REQUEST MODEL (PHASE 2 READY)
# ==================================================
class RevaluationRequest(Base):
    __tablename__ = "revaluation_requests"

    id = Column(Integer, primary_key=True, index=True)

    submission_id = Column(Integer, ForeignKey("student_submissions.id"))
    student_id = Column(Integer, ForeignKey("users.id"))

    request_type = Column(String)  # revaluation / photocopy
    status = Column(String, default="pending")  # pending / approved / rejected

    faculty_remark = Column(String, nullable=True)

    requested_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    submission = relationship("StudentSubmission", back_populates="revaluation_requests")
    student = relationship("User", back_populates="revaluation_requests")