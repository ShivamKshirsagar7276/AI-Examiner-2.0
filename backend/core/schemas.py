from pydantic import BaseModel, EmailStr
from typing import List


# ---------------------------
# USER SCHEMAS
# ---------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# ---------------------------
# EXAM SCHEMAS
# ---------------------------

class ExamCreate(BaseModel):
    title: str
    class_name: str
    division: str
    subject: str
    total_marks: int


class ExamResponse(BaseModel):
    id: int
    title: str
    class_name: str
    division: str
    subject: str
    total_marks: int
    result_status: str

    class Config:
        from_attributes = True