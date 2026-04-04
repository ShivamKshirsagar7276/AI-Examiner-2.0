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


# ============================================================
# QUESTION TYPE DETECTORS
# ============================================================

def is_code_question(question_text: str) -> bool:
    if not question_text:
        return False
    code_keywords = [
        "write a program", "write program", "develop a program",
        "implement a program", "implement", "write sql", "write a sql",
        "write pl/sql", "write a pl/sql", "write query", "write a query",
        "write queries", "code to", "program to", "develop program",
        "create a program", "write java", "write python", "write c program",
        "write a function", "write function", "write a method",
        "write a class", "write class", "using jdbc", "using socket",
        "using thread", "write procedure", "write a procedure",
        "write trigger", "write a trigger", "write cursor"
    ]
    q_lower = question_text.lower()
    return any(kw in q_lower for kw in code_keywords)


def is_diagram_mandatory(question_text: str) -> bool:
    if not question_text:
        return False
    diagram_keywords = [
        "with diagram", "with neat diagram", "with neat sketch",
        "with suitable diagram", "draw", "draw er diagram",
        "draw and explain", "illustrate", "with figure",
        "with block diagram", "with flowchart", "with neat figure",
        "sketch", "show with diagram"
    ]
    q_lower = question_text.lower()
    return any(kw in q_lower for kw in diagram_keywords)


# ============================================================
# SUBJECT-AWARE SCORING WEIGHTS
# ============================================================

def get_weights(subject: str, is_code: bool, diagram_mandatory: bool) -> dict:
    if is_code:
        return dict(semantic=0.15, coverage=0.55, quality=0.25, diagram=0.05)
    if diagram_mandatory:
        return dict(semantic=0.25, coverage=0.30, quality=0.15, diagram=0.30)

    s = subject.lower()

    if any(x in s for x in ["computer networks", "network"]):
        return dict(semantic=0.35, coverage=0.40, quality=0.15, diagram=0.10)
    if any(x in s for x in ["database", "dbms"]):
        return dict(semantic=0.35, coverage=0.40, quality=0.15, diagram=0.10)
    if any(x in s for x in ["java", "object oriented", "oops", "web technology"]):
        return dict(semantic=0.30, coverage=0.45, quality=0.20, diagram=0.05)
    if any(x in s for x in ["python", "data structures", "algorithms"]):
        return dict(semantic=0.30, coverage=0.45, quality=0.20, diagram=0.05)
    if any(x in s for x in ["digital electronics", "microprocessor", "computer architecture"]):
        return dict(semantic=0.30, coverage=0.30, quality=0.10, diagram=0.30)
    if any(x in s for x in ["operating systems", "compiler", "theory of computation"]):
        return dict(semantic=0.35, coverage=0.40, quality=0.15, diagram=0.10)
    if any(x in s for x in ["machine learning", "deep learning", "artificial intelligence",
                              "data science", "natural language", "computer vision"]):
        return dict(semantic=0.40, coverage=0.35, quality=0.15, diagram=0.10)
    if any(x in s for x in ["software engineering"]):
        return dict(semantic=0.35, coverage=0.35, quality=0.15, diagram=0.15)
    if any(x in s for x in ["information security", "cloud", "internet of things", "big data"]):
        return dict(semantic=0.40, coverage=0.35, quality=0.15, diagram=0.10)

    return dict(semantic=0.40, coverage=0.35, quality=0.15, diagram=0.10)


# ============================================================
# SUBJECT-AWARE LLM COVERAGE HINT
# ============================================================

def get_subject_hint(subject: str, is_code: bool, question_text: str) -> str:
    if is_code:
        q_lower = (question_text or "").lower()
        if any(x in q_lower for x in ["sql", "pl/sql", "query", "procedure", "trigger", "cursor"]):
            return (
                "This is a SQL/PL/SQL coding question. "
                "Focus on: correct SQL syntax, right clauses used (SELECT/INSERT/UPDATE/DELETE/CREATE), "
                "correct table/column references, logic correctness. "
                "A different but correct query achieving the same result should score high. "
                "Do NOT penalize for different formatting or alias names."
            )
        if "java" in q_lower:
            return (
                "This is a Java programming question. "
                "Focus on: correct class/method structure, OOP concepts used correctly, "
                "logic correctness, and whether the program achieves the stated goal. "
                "Do NOT penalize for different variable names or minor syntax variations."
            )
        if "python" in q_lower:
            return (
                "This is a Python programming question. "
                "Focus on: correct Python syntax, logic correctness, "
                "use of appropriate built-ins or data structures. "
                "A different but correct Pythonic solution should score high."
            )
        return (
            "This is a programming question. "
            "Focus on logic correctness, syntax validity, and whether the program achieves its goal. "
            "A different but logically correct implementation should score high. "
            "Do NOT penalize for different variable names or minor style differences."
        )

    s = subject.lower()

    if any(x in s for x in ["data structures", "algorithms"]):
        return (
            "Focus on correctness of the algorithm/data structure logic, "
            "time and space complexity if mentioned, traversal steps, "
            "and dry run examples. Keyword matching is less important than conceptual correctness."
        )
    if any(x in s for x in ["theory of computation", "compiler design"]):
        return (
            "Check for correctness of formal definitions, state transitions, "
            "grammar productions, and proof steps. "
            "Give partial credit for partially correct formal constructs."
        )
    if any(x in s for x in ["digital electronics", "microprocessor", "computer architecture"]):
        return (
            "Check for correctness of logic gates, truth tables, register operations, "
            "addressing modes, and circuit descriptions. Diagram labels matter significantly."
        )
    if any(x in s for x in ["computer networks", "network"]):
        return (
            "Check for correct protocol names, OSI/TCP-IP layer functions, "
            "working mechanisms, and technical standards. "
            "Coverage of all required sub-points matters. "
            "Penalize vague answers that lack protocol/layer specifics."
        )
    if any(x in s for x in ["operating systems"]):
        return (
            "Check for correct OS concepts: scheduling algorithms, memory management, "
            "process states, deadlock conditions, synchronization mechanisms. "
            "Penalize answers missing key technical terms."
        )
    if any(x in s for x in ["database", "dbms"]):
        return (
            "Check for correct DBMS concepts: ACID properties, normalization forms, "
            "ER diagram components, transaction management, SQL syntax. "
            "Penalize answers missing key properties or steps."
        )
    if any(x in s for x in ["java", "object oriented", "oops"]):
        return (
            "Check for correct OOP concepts: inheritance, polymorphism, encapsulation, abstraction. "
            "Check for correct Java-specific features: interfaces, exceptions, threads, packages. "
            "Code examples should demonstrate the concept correctly."
        )
    if any(x in s for x in ["python"]):
        return (
            "Check for correct Python concepts: data types, control flow, OOP in Python, "
            "built-in functions, modules, data structures. "
            "Code examples should be syntactically and logically correct."
        )
    if any(x in s for x in ["machine learning", "deep learning", "artificial intelligence"]):
        return (
            "Check for correct algorithm names, mathematical intuition explained in plain language, "
            "activation functions, loss functions, training concepts. "
            "Penalize vague answers lacking technical depth."
        )
    if any(x in s for x in ["software engineering"]):
        return (
            "Check for correct model names (SDLC, Agile, Waterfall), phases, "
            "UML diagram descriptions, and real-world applicability. "
            "Penalize answers missing lifecycle phases or diagram components."
        )
    if any(x in s for x in ["information security", "cloud", "internet of things", "big data"]):
        return (
            "Check for correct terminology, security protocols, architecture components, "
            "attack types or cloud service models. "
            "Penalize generic answers lacking technical depth."
        )

    return "Evaluate based on technical accuracy, completeness of explanation, and clarity."


# ============================================================
# SUBJECT + TYPE AWARE REASONING COMPONENTS
# ============================================================

def get_reasoning_components(subject: str, is_code: bool, diagram_mandatory: bool) -> list:
    if is_code:
        s = subject.lower()
        if any(x in s for x in ["database", "dbms"]):
            return ["SQL/PL/SQL Logic", "Syntax Correctness", "Completeness", "Output / Result"]
        if "java" in s:
            return ["Logic Correctness", "Java Syntax & Structure", "OOP Concepts Used", "Output / Compilation"]
        if "python" in s or "data structures" in s:
            return ["Logic Correctness", "Python Syntax", "Edge Cases / Correctness", "Output"]
        return ["Logic Correctness", "Syntax & Structure", "Completeness", "Output / Result"]

    s = subject.lower()

    if any(x in s for x in ["computer networks", "network"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram / Architecture", "Protocol / Layer Details", "Working Mechanism"]
        return ["Concept Definition", "Working Mechanism", "Protocol / Standards", "Comparison Points"]
    if any(x in s for x in ["database", "dbms"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram Accuracy (ER/Schema)", "Properties / Rules", "Example"]
        return ["Concept Definition", "Properties / Rules", "SQL / Steps", "Example"]
    if any(x in s for x in ["java", "object oriented", "oops"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram (Class/Thread/UML)", "Working / Mechanism", "Code Example"]
        return ["Concept Definition", "OOP Principle Explained", "Working / Mechanism", "Code Example"]
    if any(x in s for x in ["python"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram / Tree / Structure", "Working / Steps", "Code / Example"]
        return ["Concept Definition", "Working / Steps", "Built-in / Library Usage", "Code / Example"]
    if any(x in s for x in ["data structures", "algorithms"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram / Tree / Graph", "Algorithm Steps", "Time & Space Complexity"]
        return ["Concept Definition", "Algorithm / Logic Steps", "Time & Space Complexity", "Example / Dry Run"]
    if any(x in s for x in ["operating systems"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram / State Chart", "Working Mechanism", "Advantages / Disadvantages"]
        return ["Concept Definition", "Working Mechanism", "Scheduling / Management Details", "Example"]
    if any(x in s for x in ["theory of computation", "compiler design"]):
        if diagram_mandatory:
            return ["Formal Definition", "Diagram (DFA/NFA/Parse Tree)", "Construction / Proof Steps", "Example (String/Grammar)"]
        return ["Formal Definition", "Construction / Proof Steps", "Example (String/Grammar)", "Correctness of Transitions"]
    if any(x in s for x in ["digital electronics", "microprocessor", "computer architecture"]):
        if diagram_mandatory:
            return ["Concept Definition", "Circuit / Block Diagram", "Truth Table / Timing", "Working Explanation"]
        return ["Concept Definition", "Circuit / Register Description", "Truth Table / Logic", "Example"]
    if any(x in s for x in ["machine learning", "deep learning", "artificial intelligence"]):
        return ["Concept Definition", "Algorithm / Model Explanation", "Mathematical Intuition", "Real-world Example"]
    if any(x in s for x in ["software engineering"]):
        if diagram_mandatory:
            return ["Concept Definition", "Diagram / Model (UML/SDLC)", "Phases / Steps", "Real-world Application"]
        return ["Concept Definition", "Phases / Steps", "Advantages / Disadvantages", "Real-world Application"]
    if any(x in s for x in ["information security", "cloud", "internet of things", "big data"]):
        return ["Concept Definition", "Technical Components", "Working / Architecture", "Example / Use Case"]

    return ["Concept Definition", "Technical Explanation", "Accuracy & Completeness", "Example / Diagram"]


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(vec1, vec2):
    denominator = (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    if denominator == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / denominator)


# ============================================================
# SEMANTIC SCORE
# ============================================================

def compute_semantic_score(model_answer, student_answer, is_code: bool) -> float:
    if not student_answer or not str(student_answer).strip():
        return 0.0
    if isinstance(model_answer, dict):
        model_answer = model_answer.get("answer_text", "")
    model_answer   = str(model_answer)
    student_answer = str(student_answer)
    try:
        model_vec   = embedding_model.encode(model_answer)
        student_vec = embedding_model.encode(student_answer)
        similarity  = cosine_similarity(model_vec, student_vec)
        return float(max(0.0, min(1.0, similarity)))
    except Exception:
        return 0.0


# ============================================================
# LLM COVERAGE + QUALITY ANALYSIS
# ============================================================

def compute_llm_analysis(
    model_answer,
    student_answer,
    subject: str = "",
    is_code: bool = False,
    question_text: str = ""
) -> tuple:
    if not student_answer or not str(student_answer).strip():
        return (0.0, 0.0)

    model_answer   = str(model_answer)
    student_answer = str(student_answer)
    subject_hint   = get_subject_hint(subject, is_code, question_text)

    prompt = {
        "task": "Compare student answer with model answer and give scores.",
        "subject": subject,
        "question_type": "code" if is_code else "theory",
        "evaluation_instructions": subject_hint,
        "scoring_rules": [
            "coverage_score (0 to 1): How many key concepts/points/steps from the model answer are covered.",
            "quality_score (0 to 1): Accuracy, correctness, and clarity of the student's explanation or code.",
            "For code questions: prioritize logic correctness over exact syntax match.",
            "For theory questions: prioritize concept accuracy and completeness.",
            "Return ONLY JSON with coverage_score and quality_score. No other text."
        ],
        "model_answer":   model_answer,
        "student_answer": student_answer
    }

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict academic evaluator. Return only JSON with coverage_score and quality_score."
                },
                {"role": "user", "content": json.dumps(prompt)}
            ],
            temperature=0.0
        )
        raw    = response.choices[0].message.content.strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        coverage = max(0.0, min(1.0, float(parsed.get("coverage_score", 0))))
        quality  = max(0.0, min(1.0, float(parsed.get("quality_score", 0))))
        return (coverage, quality)
    except Exception:
        return (0.0, 0.0)


# ============================================================
# DIAGRAM SCORE — now uses actual GPT-4V grade
# ============================================================

def compute_diagram_score(
    diagram_expected: bool,
    diagram_present: bool,
    diagram_grade: dict,
    max_marks: float,
) -> float:
    """
    OLD: binary 0 or 1
    NEW: uses actual awarded_marks from GPT-4V diagram grading
    Returns a ratio 0.0 to 1.0
    """
    if not diagram_expected or not diagram_present:
        return 0.0

    # Use actual GPT-4V grade if available
    if diagram_grade and diagram_grade.get("verdict") not in ("error", None, ""):
        awarded = float(diagram_grade.get("awarded_marks", 0.0))
        ratio   = awarded / max_marks if max_marks > 0 else 0.0
        return round(min(ratio, 1.0), 3)

    # Fallback: diagram present but no detailed grade
    return 0.5


# ============================================================
# EXPLAINABLE REASONING
# ============================================================

def generate_explainable_reasoning(
    model_answer,
    student_answer,
    max_marks,
    subject,
    question_text,
    diagram_expected,
    diagram_present,
    diagram_labels,
    diagram_grade,
    semantic_score,
    coverage_score,
    quality_score,
    final_marks,
    is_code,
    diagram_mandatory
):
    if not student_answer or not str(student_answer).strip():
        return {
            "components": [
                {"component": "Answer", "status": "✘", "reasoning": "No answer was provided by the student."}
            ],
            "overall_feedback": "The student did not attempt this question.",
            "confidence": 0.0
        }

    # Diagram context — now includes GPT-4V grade details
    if diagram_expected and diagram_present and diagram_grade:
        labels   = ", ".join(diagram_labels) if diagram_labels else "labels not detected"
        correct  = ", ".join(diagram_grade.get("correct_components", [])) or "none"
        missing  = ", ".join(diagram_grade.get("missing_components", [])) or "none"
        wrong    = ", ".join(diagram_grade.get("wrong_components", [])) or "none"
        d_marks  = diagram_grade.get("awarded_marks", 0)
        diagram_context = (
            f"Diagram detected — type: {diagram_grade.get('diagram_type', 'unknown')}. "
            f"Labels: {labels}. Correct: {correct}. Missing: {missing}. Wrong: {wrong}. "
            f"Diagram marks awarded: {d_marks}/{max_marks * 0.3:.1f}."
        )
    elif diagram_expected and diagram_present:
        labels = ", ".join(diagram_labels) if diagram_labels else "labels not detected"
        diagram_context = f"A diagram was detected with labels: {labels}."
    elif diagram_expected and not diagram_present:
        diagram_context = "A diagram was expected but not detected in the student's answer."
    else:
        diagram_context = "No diagram was required for this question."

    confidence = round(
        (semantic_score * 0.4 + coverage_score * 0.4 + quality_score * 0.2) * 100, 2
    )

    components     = get_reasoning_components(subject, is_code, diagram_mandatory)
    components_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(components)])
    components_json = ",\n    ".join([
        f'{{"component": "{c}", "status": "✔ or ✘", "reasoning": "<specific reasoning referencing student actual answer>"}}'
        for c in components
    ])

    question_type_instruction = (
        "This is a PROGRAMMING/CODE question. "
        "Focus your evaluation on logic correctness, syntax, and whether the code achieves its goal. "
        "Do NOT penalize for different variable names or minor style differences. "
        "Reference the actual code the student wrote in your reasoning."
        if is_code else
        "This is a THEORY question. "
        "Focus on concept accuracy, completeness, and clarity. "
        "Always reference what the student actually wrote — never give generic feedback."
    )

    prompt = f"""
You are a strict but fair university examiner providing detailed evaluation feedback.

Subject: {subject}
Question: {question_text}
Question Type: {"Code/Program" if is_code else "Theory/Explanation"}

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

Evaluation Instruction:
{question_type_instruction}

Your task:
Evaluate the student answer across these {len(components)} components:
{components_str}

STRICT RULES:
1. Every reasoning MUST reference what the student ACTUALLY wrote.
2. NEVER give generic feedback. Always quote specific parts of the student answer.
3. BAD: "Code logic is incorrect"
   GOOD: "Student wrote for(i=0; i<n; i++) which is correct, but the swap
          uses arr[i]=arr[j] instead of a temp variable, so swap logic is wrong"
4. overall_feedback must read like a real examiner comment on THIS student's paper.

Return ONLY this JSON format, no extra text:
{{
  "components": [
    {components_json}
  ],
  "overall_feedback": "<2-3 sentence examiner summary referencing this student's actual answer>"
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
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        raw    = response.choices[0].message.content.strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        parsed["confidence"] = confidence
        return parsed
    except Exception:
        fallback_components = [
            {"component": c, "status": "✘", "reasoning": "Reasoning generation failed."}
            for c in components
        ]
        return {
            "components":       fallback_components,
            "overall_feedback": "Explainable reasoning could not be generated.",
            "confidence":       confidence
        }


# ============================================================
# MAIN EVALUATE ANSWER — subject-aware, type-aware, diagram-aware
# ============================================================

def evaluate_answer(
    model_answer,
    student_answer,
    max_marks,
    subject          = "",
    question_text    = "",
    diagram_expected = False,
    diagram_present  = False,
    diagram_labels   = None,
    diagram_grade    = None,
    explain          = True
):
    if diagram_labels is None:
        diagram_labels = []
    if diagram_grade is None:
        diagram_grade = {}

    is_code      = is_code_question(question_text)
    diagram_mand = is_diagram_mandatory(question_text)

    if not student_answer or not str(student_answer).strip():
        return {
            "answer_type":    "code" if is_code else "theory",
            "answer_types":   ["code"] if is_code else ["theory"],
            "semantic_score": 0.0,
            "coverage_score": 0.0,
            "quality_score":  0.0,
            "diagram_score":  0.0,
            "diagram_awarded_marks": 0.0,
            "final_marks":    0.0,
            "verdict":        "Not attempted",
            "reasoning": {
                "components":       [],
                "overall_feedback": "No answer provided.",
                "confidence":       0.0
            }
        }

    semantic_score                = compute_semantic_score(model_answer, student_answer, is_code)
    coverage_score, quality_score = compute_llm_analysis(
        model_answer   = model_answer,
        student_answer = student_answer,
        subject        = subject,
        is_code        = is_code,
        question_text  = question_text
    )

    # NEW: use actual GPT-4V diagram grade ratio
    diagram_score_ratio   = compute_diagram_score(diagram_expected, diagram_present, diagram_grade, max_marks)
    diagram_awarded_marks = round(diagram_score_ratio * max_marks, 2) if diagram_expected else 0.0

    # Subject-aware weights
    w = get_weights(subject, is_code, diagram_mand)

    final_ratio = (
        semantic_score      * w["semantic"] +
        coverage_score      * w["coverage"] +
        quality_score       * w["quality"]  +
        diagram_score_ratio * w["diagram"]
    )

    final_marks = round(final_ratio * float(max_marks), 2)

    if final_ratio >= 0.80:
        verdict = "Excellent"
    elif final_ratio >= 0.60:
        verdict = "Good"
    elif final_ratio >= 0.40:
        verdict = "Average"
    elif final_ratio > 0.0:
        verdict = "Poor"
    else:
        verdict = "Not attempted"

    result = {
        "answer_type":           "code" if is_code else "theory",
        "answer_types":          ["code"] if is_code else ["theory"],
        "semantic_score":        round(semantic_score, 3),
        "coverage_score":        round(coverage_score, 3),
        "quality_score":         round(quality_score, 3),
        "diagram_score":         round(diagram_score_ratio, 3),
        "diagram_awarded_marks": diagram_awarded_marks,
        "final_marks":           final_marks,
        "verdict":               verdict,
    }

    if explain:
        result["reasoning"] = generate_explainable_reasoning(
            model_answer      = str(model_answer),
            student_answer    = str(student_answer),
            max_marks         = max_marks,
            subject           = subject,
            question_text     = question_text,
            diagram_expected  = diagram_expected,
            diagram_present   = diagram_present,
            diagram_labels    = diagram_labels,
            diagram_grade     = diagram_grade,
            semantic_score    = semantic_score,
            coverage_score    = coverage_score,
            quality_score     = quality_score,
            final_marks       = final_marks,
            is_code           = is_code,
            diagram_mandatory = diagram_mand,
        )

    return result


# ============================================================
# GRADE CALCULATOR
# ============================================================

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