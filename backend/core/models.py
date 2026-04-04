from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    revaluation_requests = relationship("RevaluationRequest", back_populates="student")


class Exam(Base):
    __tablename__ = "exams"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String, nullable=False)
    class_name  = Column(String, nullable=False)
    division    = Column(String, nullable=False)
    subject     = Column(String, nullable=False)
    total_marks = Column(Integer, nullable=False)

    result_status = Column(String, default="draft")
    published_at  = Column(DateTime, nullable=True)

    question_paper_path      = Column(String, nullable=True)
    structured_questions     = Column(JSON, nullable=True)
    model_answer_path        = Column(String, nullable=True)
    structured_model_answers = Column(JSON, nullable=True)

    submissions = relationship("StudentSubmission", back_populates="exam")
    bulk_jobs   = relationship("BulkJob", back_populates="exam")


class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id          = Column(Integer, primary_key=True, index=True)
    exam_id     = Column(Integer, ForeignKey("exams.id"))
    roll_number = Column(String, nullable=False)

    answer_sheet_path  = Column(String, nullable=True)
    ocr_output         = Column(JSON, nullable=True)
    structured_answers = Column(JSON, nullable=True)
    mapped_answers     = Column(JSON, nullable=True)
    diagram_results    = Column(JSON, nullable=True)

    evaluation_json = Column(JSON, nullable=True)
    total_marks     = Column(Float, nullable=True)
    max_marks       = Column(Float, nullable=True)
    percentage      = Column(Float, nullable=True)
    grade           = Column(String, nullable=True)

    evaluated_at   = Column(DateTime, nullable=True)
    reevaluated_at = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    exam                 = relationship("Exam", back_populates="submissions")
    revaluation_requests = relationship("RevaluationRequest", back_populates="submission")


class RevaluationRequest(Base):
    __tablename__ = "revaluation_requests"

    id             = Column(Integer, primary_key=True, index=True)
    submission_id  = Column(Integer, ForeignKey("student_submissions.id"))
    student_id     = Column(Integer, ForeignKey("users.id"))
    request_type   = Column(String)
    status         = Column(String, default="pending")
    faculty_remark = Column(String, nullable=True)
    requested_at   = Column(DateTime, default=datetime.utcnow)
    resolved_at    = Column(DateTime, nullable=True)

    submission = relationship("StudentSubmission", back_populates="revaluation_requests")
    student    = relationship("User", back_populates="revaluation_requests")


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id           = Column(Integer, primary_key=True, index=True)
    exam_id      = Column(Integer, ForeignKey("exams.id"), nullable=False)
    total        = Column(Integer, default=0)
    processed    = Column(Integer, default=0)
    succeeded    = Column(Integer, default=0)
    failed       = Column(Integer, default=0)
    status       = Column(String, default="pending")
    results      = Column(JSON, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    exam = relationship("Exam", back_populates="bulk_jobs")


class Student(Base):
    __tablename__ = "students"

    id          = Column(Integer, primary_key=True, index=True)
    roll_number = Column(String, nullable=False)
    division    = Column(String, nullable=False)
    class_name  = Column(String, nullable=False)
    password    = Column(String, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("roll_number", "division", "class_name", name="uq_student_roll_div_class"),
    )

    student_revaluation_requests = relationship("StudentRevaluationRequest", back_populates="student")


class StudentRevaluationRequest(Base):
    __tablename__ = "student_revaluation_requests"

    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey("students.id"))
    submission_id  = Column(Integer, ForeignKey("student_submissions.id"))
    request_type   = Column(String, nullable=False)
    reason         = Column(String, nullable=True)
    status         = Column(String, default="pending")
    faculty_remark = Column(String, nullable=True)
    requested_at   = Column(DateTime, default=datetime.utcnow)
    resolved_at    = Column(DateTime, nullable=True)

    # ← NEW: stores marks before revaluation for comparison
    old_marks      = Column(Float, nullable=True)
    old_percentage = Column(Float, nullable=True)
    old_grade      = Column(String, nullable=True)
    old_eval_json  = Column(JSON, nullable=True)

    student    = relationship("Student", back_populates="student_revaluation_requests")
    submission = relationship("StudentSubmission")