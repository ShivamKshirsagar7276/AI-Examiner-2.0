import json
import os
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI
from sentence_transformers import SentenceTransformer

load_dotenv()

# ==============================
# Azure Chat Client (LLM Only)
# ==============================
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# ==============================
# Local Free Embedding Model
# ==============================
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ==========================================================
# 1️⃣ SAFE COSINE SIMILARITY
# ==========================================================
def cosine_similarity(vec1, vec2):
    denominator = (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    if denominator == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / denominator)


# ==========================================================
# 2️⃣ SAFE SEMANTIC SCORE
# ==========================================================
def compute_semantic_score(model_answer, student_answer):

    if not student_answer or not str(student_answer).strip():
        return 0.0

    if isinstance(model_answer, dict):
        model_answer = model_answer.get("answer_text", "")

    model_answer = str(model_answer)
    student_answer = str(student_answer)

    try:
        model_vec = embedding_model.encode(model_answer)
        student_vec = embedding_model.encode(student_answer)
        similarity = cosine_similarity(model_vec, student_vec)
        return float(max(0.0, min(1.0, similarity)))
    except Exception:
        return 0.0


# ==========================================================
# 3️⃣ LLM COVERAGE + QUALITY
# ==========================================================
def compute_llm_analysis(model_answer, student_answer):

    if not student_answer or not str(student_answer).strip():
        return (0.0, 0.0)

    model_answer = str(model_answer)
    student_answer = str(student_answer)

    prompt = {
        "task": "Compare student answer with model answer.",
        "instructions": [
            "Give coverage_score between 0 and 1.",
            "Give quality_score between 0 and 1.",
            "Return only JSON."
        ],
        "model_answer": model_answer,
        "student_answer": student_answer
    }

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict academic evaluator. Return only JSON."
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt)
                }
            ],
            temperature=0.0
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)

        coverage = float(parsed.get("coverage_score", 0))
        quality = float(parsed.get("quality_score", 0))

        coverage = max(0.0, min(1.0, coverage))
        quality = max(0.0, min(1.0, quality))

        return (coverage, quality)

    except Exception:
        return (0.0, 0.0)


# ==========================================================
# 4️⃣ FACULTY-LIKE SCORING
# ==========================================================
def evaluate_answer(
    model_answer,
    student_answer,
    max_marks,
    diagram_expected=False,
    diagram_present=False
):

    if not student_answer or not str(student_answer).strip():
        return {
            "semantic_score": 0.0,
            "coverage_score": 0.0,
            "quality_score": 0.0,
            "diagram_score": 0.0,
            "final_marks": 0.0
        }

    semantic_score = compute_semantic_score(model_answer, student_answer)
    coverage_score, quality_score = compute_llm_analysis(model_answer, student_answer)

    diagram_score = 1.0 if (diagram_expected and diagram_present) else 0.0

    final_ratio = (
        semantic_score * 0.5 +
        coverage_score * 0.3 +
        quality_score * 0.1 +
        diagram_score * 0.1
    )

    final_marks = round(final_ratio * float(max_marks), 2)

    return {
        "semantic_score": round(semantic_score, 3),
        "coverage_score": round(coverage_score, 3),
        "quality_score": round(quality_score, 3),
        "diagram_score": diagram_score,
        "final_marks": final_marks
    }


# ==========================================================
# 5️⃣ GRADE SYSTEM
# ==========================================================
def calculate_grade(percentage: float) -> str:

    if percentage >= 80:
        return "First Class with Distinction"
    elif percentage >= 75:
        return "Distinction"
    elif percentage >= 60:
        return "First Class"
    elif percentage >= 50:
        return "Second Class"
    elif percentage >= 40:
        return "Pass"
    else:
        return "Fail"