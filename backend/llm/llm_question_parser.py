import json
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def parse_question_paper(raw_text):

    prompt = {
        "task": "Parse academic university question paper into structured JSON.",
        "instructions": [
            "Detect sections like Q1, Q2, Q3 etc.",
            "Extract total marks for each question or section.",
            "Extract sub-questions (a, b, c, etc.) if present.",
            "Extract marks for each sub-question if mentioned.",
            "If sub-question marks are NOT mentioned but total marks are given, divide total marks equally among sub-questions.",
            "Detect instructions like 'Attempt any 3', 'Solve any four', etc.",
            "If choice rule exists, add 'attempt': N inside that section.",
            "If no choice rule exists, do not add attempt field.",
            "All sub-questions MUST contain a 'marks' field.",
            "Return strictly valid JSON only. No explanation text."
        ],
        "question_paper_text": raw_text,
        "output_format_example": {
            "sections": [
                {
                    "section_name": "Q2",
                    "attempt": 3,
                    "questions": [
                        {
                            "question_id": "Q2",
                            "marks": 16,
                            "sub_questions": [
                                {
                                    "sub_id": "a",
                                    "text": "Explain OS",
                                    "marks": 4
                                },
                                {
                                    "sub_id": "b",
                                    "text": "Explain memory management",
                                    "marks": 4
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict academic question paper parser. "
                    "Return only valid JSON. No explanations. "
                    "Ensure every sub-question has marks."
                )
            },
            {
                "role": "user",
                "content": json.dumps(prompt)
            }
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    print("📘 PARSED QUESTION STRUCTURE:")
    print(raw)

    try:
        parsed = json.loads(raw)
    except Exception:
        return {}

    # ===============================
    # SAFETY CHECK (ENSURE MARKS EXIST)
    # ===============================
    for section in parsed.get("sections", []):
        for question in section.get("questions", []):

            total_marks = question.get("marks", 0)
            sub_questions = question.get("sub_questions", [])

            if sub_questions:

                # If any sub-question missing marks → distribute equally
                missing_marks = any("marks" not in sub for sub in sub_questions)

                if missing_marks and total_marks > 0:
                    equal_marks = total_marks // len(sub_questions)

                    for sub in sub_questions:
                        sub["marks"] = equal_marks

    return parsed