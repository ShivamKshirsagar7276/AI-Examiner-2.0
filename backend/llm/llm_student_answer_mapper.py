import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def extract_sub_question_ids(structured_questions):
    sub_ids = []

    for section in structured_questions.get("sections", []):
        for q in section.get("questions", []):
            main_qid = q.get("question_id")

            if q.get("sub_questions"):
                for sub in q.get("sub_questions", []):
                    sub_id = sub.get("sub_id")
                    sub_ids.append(f"{main_qid}{sub_id}")
            else:
                sub_ids.append(main_qid)

    return sub_ids


def build_page_wise_text(ocr_output):
    pages = []

    for page in ocr_output:
        page_number = page["page_number"]
        page_text = ""

        for line in page["lines"]:
            page_text += line["text"] + "\n"

        pages.append({
            "page_number": page_number,
            "content": page_text.strip()
        })

    return pages


def map_student_answers_strict(structured_questions, ocr_output):

    question_ids = extract_sub_question_ids(structured_questions)

    pages_data = build_page_wise_text(ocr_output)

    prompt = {
        "task": "Strictly segment student answers by sub-question IDs.",
        "rules": [
            "Use ONLY the provided page_number values",
            "Do NOT guess page numbers",
            "Match strictly with sub-question IDs like Q1a, Q1b",
            "Do NOT merge multiple answers",
            "Return answer_text exactly as written",
            "Return correct pages where text appears",
            "Ignore header and metadata",
            "Return ONLY JSON"
        ],
        "sub_question_ids": question_ids,
        "pages": pages_data,
        "output_format_example": {
            "Q1a": {
                "answer_text": "...",
                "pages": [1]
            }
        }
    }

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are an expert academic answer segmentation engine. Return only valid JSON."
            },
            {
                "role": "user",
                "content": json.dumps(prompt)
            }
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    print("🔍 RAW STRICT SEGMENTATION OUTPUT:")
    print(raw)

    try:
        parsed = json.loads(raw)

        for qid in question_ids:
            if qid not in parsed:
                parsed[qid] = {
                    "answer_text": "",
                    "pages": []
                }

        return parsed

    except Exception as e:
        print("❌ JSON Parsing Error:", e)
        return {}