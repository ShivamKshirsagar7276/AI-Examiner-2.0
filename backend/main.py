from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from core.database import Base, engine
from core import models
from routers.auth_router import router as auth_router
from routers.exam_router import router as exam_router
from routers.result_router import router as result_router
from routers.revaluation_router import router as revaluation_router
from routers.dashboard_router import router as dashboard_router
from routers.public_router import router as public_router
from routers.student_router import router as student_router
from routers.faculty_router import router as faculty_router
from core.dependencies import get_current_user
from core.models import User

app = FastAPI(
    title="AI Examiner 2.0",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(exam_router)
app.include_router(result_router)
app.include_router(revaluation_router)
app.include_router(dashboard_router)
app.include_router(public_router)
app.include_router(student_router)
app.include_router(faculty_router)

@app.get("/health")
def health_check():
    return {"status": "running"}

@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "id":    current_user.id,
        "email": current_user.email
    }