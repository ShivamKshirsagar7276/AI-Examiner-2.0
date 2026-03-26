import json
import os
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI
from sentence_transformers import SentenceTransformer

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def cosine_similarity(vec1, vec2):
    denominator = (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    if denominator == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / denominator)


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


def generate_explainable_reasoning(
    model_answer,
    student_answer,
    max_marks,
    diagram_expected,
    diagram_present,
    diagram_labels,
    semantic_score,
    coverage_score,
    quality_score,
    final_marks
):
    if not student_answer or not str(student_answer).strip():
        return {
            "components": [
                {
                    "component": "Answer",
                    "status": "✘",
                    "reasoning": "No answer was provided by the student."
                }
            ],
            "overall_feedback": "The student did not attempt this question.",
            "confidence": 0.0
        }

    if diagram_expected and diagram_present:
        labels = ", ".join(diagram_labels) if diagram_labels else "labels not detected"
        diagram_context = f"A diagram was detected with the following labels: {labels}."
    elif diagram_expected and not diagram_present:
        diagram_context = "A diagram was expected but not detected in the student's answer."
    else:
        diagram_context = "No diagram was required for this question."

    confidence = round(
        (semantic_score * 0.5 + coverage_score * 0.3 + quality_score * 0.2) * 100, 2
    )

    prompt = f"""
You are a strict but fair university examiner providing detailed evaluation feedback.

Model Answer:
{model_answer}

Student Answer:
{student_answer}

Scoring Context:
- Total marks: {max_marks}
- Marks awarded: {final_marks}
- Semantic similarity: {round(semantic_score * 100, 1)}%
- Content coverage: {round(coverage_score * 100, 1)}%
- Writing quality: {round(quality_score * 100, 1)}%
- Diagram context: {diagram_context}

Your task:
Evaluate the student answer across these 4 components and explain the grading:
1. Definition — Did the student correctly define the core concept?
2. Explanation — Was the explanation clear, complete, and relevant?
3. Example — Did the student provide a meaningful real-world example?
4. Diagram — Was a diagram present and relevant? (use diagram context above)

For each component provide:
- status: "✔" if satisfactory, "✘" if missing or incorrect
- reasoning: 1-2 sentences of specific, detailed feedback referencing the actual answer

Also provide overall_feedback: a 2-3 sentence examiner summary explaining exactly why these marks were awarded or cut.

Return ONLY this JSON format, no extra text:
{{
  "components": [
    {{
      "component": "Definition",
      "status": "✔" or "✘",
      "reasoning": "<specific detailed reasoning>"
    }},
    {{
      "component": "Explanation",
      "status": "✔" or "✘",
      "reasoning": "<specific detailed reasoning>"
    }},
    {{
      "component": "Example",
      "status": "✔" or "✘",
      "reasoning": "<specific detailed reasoning>"
    }},
    {{
      "component": "Diagram",
      "status": "✔" or "✘",
      "reasoning": "<specific detailed reasoning>"
    }}
  ],
  "overall_feedback": "<2-3 sentence examiner summary>"
}}
"""

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict but fair university examiner. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1000
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        parsed["confidence"] = confidence
        return parsed

    except Exception:
        return {
            "components": [
                {"component": "Definition", "status": "✘", "reasoning": "Reasoning generation failed."},
                {"component": "Explanation", "status": "✘", "reasoning": "Reasoning generation failed."},
                {"component": "Example", "status": "✘", "reasoning": "Reasoning generation failed."},
                {"component": "Diagram", "status": "✘", "reasoning": "Reasoning generation failed."}
            ],
            "overall_feedback": "Explainable reasoning could not be generated.",
            "confidence": confidence
        }


def evaluate_answer(
    model_answer,
    student_answer,
    max_marks,
    diagram_expected=False,
    diagram_present=False,
    diagram_labels=None,
    explain=True
):
    if diagram_labels is None:
        diagram_labels = []

    if not student_answer or not str(student_answer).strip():
        return {
            "semantic_score": 0.0,
            "coverage_score": 0.0,
            "quality_score": 0.0,
            "diagram_score": 0.0,
            "final_marks": 0.0,
            "reasoning": {
                "components": [],
                "overall_feedback": "No answer provided.",
                "confidence": 0.0
            }
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

    result = {
        "semantic_score": round(semantic_score, 3),
        "coverage_score": round(coverage_score, 3),
        "quality_score": round(quality_score, 3),
        "diagram_score": diagram_score,
        "final_marks": final_marks
    }

    if explain:
        result["reasoning"] = generate_explainable_reasoning(
            model_answer=str(model_answer),
            student_answer=str(student_answer),
            max_marks=max_marks,
            diagram_expected=diagram_expected,
            diagram_present=diagram_present,
            diagram_labels=diagram_labels,
            semantic_score=semantic_score,
            coverage_score=coverage_score,
            quality_score=quality_score,
            final_marks=final_marks
        )

    return result


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