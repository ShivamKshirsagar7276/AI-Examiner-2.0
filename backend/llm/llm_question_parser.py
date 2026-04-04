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
        "task": "Parse academic question paper into structured JSON.",
        "instructions": [
            "Detect all sections like Q1, Q2, Q3 etc.",
            "Extract total marks for each section.",
            "Extract ALL sub-questions (a, b, c, d, e, f etc.) — do NOT skip any sub-question.",
            "If instruction says 'Attempt any N' or 'Solve any N', set attempt = N (as integer) in that section.",
            "Marks per sub-question = section total marks divided by attempt count (NOT by total number of sub-questions).",
            "Example: Q2 total=20, attempt any 5 from 6 subs → each sub gets 20/5 = 4 marks.",
            "Example: Q1 total=10, attempt any 5 from 6 subs → each sub gets 10/5 = 2 marks.",
            "If no attempt instruction exists, divide total marks equally among all sub-questions.",
            "Every sub-question MUST have: sub_id, text, marks.",
            "Every section with attempt rule MUST have the attempt field as an integer.",
            "Extract question text exactly as written — do not summarize or shorten.",
            "Return strictly valid JSON only. No explanation. No markdown. No code fences."
        ],
        "question_paper_text": raw_text,
        "output_format_example": {
            "sections": [
                {
                    "section_name": "Q1",
                    "attempt": 5,
                    "questions": [
                        {
                            "question_id": "Q1",
                            "marks": 10,
                            "sub_questions": [
                                {"sub_id": "a", "text": "Define Bit Rate and Baud Rate.", "marks": 2},
                                {"sub_id": "b", "text": "Differentiate between Analog and Digital Signal.", "marks": 2},
                                {"sub_id": "c", "text": "Classify Computer Network based on geography.", "marks": 2},
                                {"sub_id": "d", "text": "State any 2 types of guided media.", "marks": 2},
                                {"sub_id": "e", "text": "Define Protocol and Bandwidth.", "marks": 2},
                                {"sub_id": "f", "text": "Draw basic communication model.", "marks": 2}
                            ]
                        }
                    ]
                },
                {
                    "section_name": "Q2",
                    "attempt": 5,
                    "questions": [
                        {
                            "question_id": "Q2",
                            "marks": 20,
                            "sub_questions": [
                                {"sub_id": "a", "text": "Define Computer Network and explain need of computer network.", "marks": 4},
                                {"sub_id": "b", "text": "Define simplex, half duplex, full duplex modes of communication.", "marks": 4},
                                {"sub_id": "c", "text": "Describe principles of packet switching techniques with neat diagram.", "marks": 4},
                                {"sub_id": "d", "text": "Compare twisted pair cable, coaxial cable and optical fibre cable.", "marks": 4},
                                {"sub_id": "e", "text": "Explain advantages of computer networks using daily life examples.", "marks": 4},
                                {"sub_id": "f", "text": "Explain satellite communication with help of neat diagram.", "marks": 4}
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
                    "Return only valid JSON. No explanations. No markdown. No code fences. "
                    "Ensure every sub-question has sub_id, marks and text fields. "
                    "Never skip sub-questions. Always use attempt count to calculate marks per sub-question."
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

    # Strip markdown code fences if LLM adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    print("📘 PARSED QUESTION STRUCTURE:")
    print(raw)

    try:
        parsed = json.loads(raw)
    except Exception:
        return {}

    # ===============================
    # AUTO-CORRECT MARKS BASED ON ATTEMPT COUNT
    # ===============================
    for section in parsed.get("sections", []):
        for question in section.get("questions", []):

            total_marks   = question.get("marks", 0)
            sub_questions = question.get("sub_questions", [])
            attempt       = section.get("attempt", len(sub_questions))

            if sub_questions and total_marks > 0 and attempt > 0:
                # Always recalculate based on attempt count not sub-question count
                marks_per_sub = total_marks // attempt
                for sub in sub_questions:
                    sub["marks"] = marks_per_sub

            # Text fallback
            for sub in sub_questions:
                if "text" not in sub or not sub["text"]:
                    sub["text"] = ""

    # ===============================
    # FINAL VALIDATION LOG
    # ===============================
    total = 0
    for section in parsed.get("sections", []):
        for question in section.get("questions", []):
            total += question.get("marks", 0)
    print(f"✅ TOTAL MARKS DETECTED: {total}")

    return parsed