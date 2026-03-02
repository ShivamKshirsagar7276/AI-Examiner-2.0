from sqlalchemy.orm import Session
from core.models import Exam


def create_exam(db: Session, exam_data):
    exam = Exam(**exam_data)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def get_all_exams(db: Session):
    return db.query(Exam).all()


def get_exam_by_id(db: Session, exam_id: int):
    return db.query(Exam).filter(Exam.id == exam_id).first()


def delete_exam(db: Session, exam_id: int):
    exam = get_exam_by_id(db, exam_id)
    if exam:
        db.delete(exam)
        db.commit()
    return exam