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


# ==========================================================
# PURE LLM STUDENT ANSWER MAPPER
# ==========================================================
def map_student_answers_full_llm(
    structured_questions,
    ocr_output,
    diagram_results
):

    # --------------------------------------------
    # STEP 1 — Convert OCR into page-wise text
    # --------------------------------------------
    pages_data = []

    for page in ocr_output:
        page_number = page.get("page") or page.get("page_number") or 0

        page_text = ""
        for line in page.get("lines", []):
            page_text += line.get("text", "") + "\n"

        pages_data.append({
            "page": page_number,
            "text": page_text.strip()
        })

    # --------------------------------------------
    # STEP 2 — Build Prompt
    # --------------------------------------------
    prompt = {
        "task": "Segment student answers strictly by sub-question IDs and attach diagrams correctly.",
        "instructions": [
            "Match answers strictly to sub-question IDs like Q1a, Q1b, Q2a, etc.",
            "Do NOT merge multiple sub-questions.",
            "Use page numbers where answer appears.",
            "Attach diagram ONLY if the diagram visually belongs to that answer section.",
            "Do NOT attach one diagram to multiple questions unless clearly repeated.",
            "If no answer found, return empty answer_text and empty pages.",
            "Return ONLY valid JSON in required format."
        ],
        "structured_questions": structured_questions,
        "student_pages": pages_data,
        "detected_diagrams": diagram_results,
        "output_format_example": {
            "Q1a": {
                "answer_text": "...",
                "pages": [1],
                "diagram_present": False,
                "diagram_label": "",
                "diagram_labels": []
            }
        }
    }

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are an expert academic answer segmentation and evaluation engine. Return only valid JSON."
            },
            {
                "role": "user",
                "content": json.dumps(prompt)
            }
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    print("🔍 PURE LLM RAW OUTPUT:")
    print(raw)

    try:
        parsed = json.loads(raw)

        # --------------------------------------------
        # SAFETY NORMALIZATION
        # --------------------------------------------
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
                "pages": value.get("pages", []) if isinstance(value.get("pages"), list) else [],
                "diagram_present": bool(value.get("diagram_present", False)),
                "diagram_label": value.get("diagram_label", ""),
                "diagram_labels": value.get("diagram_labels", []) if isinstance(value.get("diagram_labels"), list) else []
            }

        return final_output

    except Exception as e:
        print("❌ Pure LLM JSON Parsing Error:", e)

        # Safe fallback
        fallback = {}
        for section in structured_questions.get("sections", []):
            for q in section.get("questions", []):
                main_qid = q.get("question_id")

                if q.get("sub_questions"):
                    for sub in q.get("sub_questions", []):
                        fallback[f"{main_qid}{sub.get('sub_id')}"] = {
                            "answer_text": "",
                            "pages": [],
                            "diagram_present": False,
                            "diagram_label": "",
                            "diagram_labels": []
                        }
                else:
                    fallback[main_qid] = {
                        "answer_text": "",
                        "pages": [],
                        "diagram_present": False,
                        "diagram_label": "",
                        "diagram_labels": []
                    }

        return fallback