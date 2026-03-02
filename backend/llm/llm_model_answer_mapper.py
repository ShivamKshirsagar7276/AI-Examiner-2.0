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


def map_model_answers(structured_questions, raw_text):

    prompt_data = {
        "task": "Structure the model answer according to question structure and extract marks.",
        "instructions": [
            "Match answers strictly to question IDs like Q1a, Q1b, Q2a etc.",
            "Extract the marks mentioned for each question (example: '(2 Marks)' means max_marks = 2).",
            "If marks not found, set max_marks to 0.",
            "Do NOT merge questions.",
            "Return empty answer_text if missing.",
            "Return ONLY valid JSON.",
            "Output format must include answer_text and max_marks."
        ],
        "questions": structured_questions,
        "model_answer_text": raw_text,
        "output_format_example": {
            "Q1a": {
                "answer_text": "An Operating System is...",
                "max_marks": 2
            }
        }
    }

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a strict academic model answer structurer. Extract marks and answers. Return only valid JSON."
            },
            {
                "role": "user",
                "content": json.dumps(prompt_data)
            }
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    print("🔍 MODEL ANSWER RAW LLM OUTPUT:")
    print(raw)

    try:
        parsed = json.loads(raw)

        # SAFETY NORMALIZATION
        final_output = {}

        # Extract all sub-question IDs
        sub_ids = []
        for section in structured_questions.get("sections", []):
            for q in section.get("questions", []):
                main_qid = q.get("question_id")

                if q.get("sub_questions"):
                    for sub in q.get("sub_questions", []):
                        sub_ids.append(f"{main_qid}{sub.get('sub_id')}")
                else:
                    sub_ids.append(main_qid)

        for qid in sub_ids:

            value = parsed.get(qid, {})

            if not isinstance(value, dict):
                value = {}

            final_output[qid] = {
                "answer_text": value.get("answer_text", ""),
                "max_marks": int(value.get("max_marks", 0))
            }

        return final_output

    except Exception as e:
        print("❌ Model Answer JSON Parsing Error:", e)

        # fallback empty structure
        fallback = {}
        for section in structured_questions.get("sections", []):
            for q in section.get("questions", []):
                main_qid = q.get("question_id")

                if q.get("sub_questions"):
                    for sub in q.get("sub_questions", []):
                        fallback[f"{main_qid}{sub.get('sub_id')}"] = {
                            "answer_text": "",
                            "max_marks": 0
                        }
                else:
                    fallback[main_qid] = {
                        "answer_text": "",
                        "max_marks": 0
                    }

        return fallback