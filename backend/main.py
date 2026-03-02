from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from core.database import Base, engine
from core import models
from routers.auth_router import router as auth_router
from routers.exam_router import router as exam_router
from routers.result_router import router as result_router
from routers.revaluation_router import router as revaluation_router
from core.dependencies import get_current_user
from core.models import User
from routers.dashboard_router import router as dashboard_router
from routers.public_router import router as public_router


# ----------------------------
# Create App
# ----------------------------
app = FastAPI(title="AI Examiner 2.0")


# ----------------------------
# CORS Configuration (VERY IMPORTANT)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite frontend
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Create All Tables
# ----------------------------
Base.metadata.create_all(bind=engine)


# ----------------------------
# Include Routers
# ----------------------------
app.include_router(auth_router)
app.include_router(exam_router)
app.include_router(result_router)
app.include_router(revaluation_router)
app.include_router(dashboard_router)
app.include_router(public_router)

# ----------------------------
# Protected Test Route
# ----------------------------
@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email
    }