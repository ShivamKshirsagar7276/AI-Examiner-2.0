from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    email:    EmailStr
    password: str


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type:   str


class ExamCreate(BaseModel):
    title:       str
    class_name:  str
    division:    str
    subject:     str
    total_marks: int


class ExamResponse(BaseModel):
    id:            int
    title:         str
    class_name:    str
    division:      str
    subject:       str
    total_marks:   int
    result_status: str

    class Config:
        from_attributes = True


class StudentLogin(BaseModel):
    roll_number: str
    password:    str
    division:    str
    class_name:  str


class StudentToken(BaseModel):
    access_token: str
    token_type:   str
    roll_number:  str
    division:     str
    class_name:   str


class StudentRequestCreate(BaseModel):
    request_type: str
    reason:       Optional[str] = ""