import os
import re
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
# STEP 1 — EXTRACT SUB QUESTION IDS
# ==========================================================
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


# ==========================================================
# STEP 2 — REGEX ANCHOR DETECTION
# ==========================================================
def detect_question_anchors(ocr_output):

    anchor_pattern = re.compile(
        r"(Q\.?\s*\d+\s*[a-eA-E]?|\d+\)|[a-eA-E]\)|\(\s*[a-eA-E]\s*\))"
    )

    blocks = []
    current_block = {
        "text": "",
        "pages": set()
    }

    for page in ocr_output:
        page_number = page.get("page") or page.get("page_number")

        for line in page["lines"]:
            text = line["text"]

            if anchor_pattern.search(text):

                # Save previous block
                if current_block["text"].strip():
                    blocks.append({
                        "text": current_block["text"],
                        "pages": list(current_block["pages"])
                    })

                # Start new block
                current_block = {
                    "text": text + "\n",
                    "pages": {page_number}
                }

            else:
                current_block["text"] += text + "\n"
                current_block["pages"].add(page_number)

    # Append last block
    if current_block["text"].strip():
        blocks.append({
            "text": current_block["text"],
            "pages": list(current_block["pages"])
        })

    return blocks


# ==========================================================
# STEP 3 — LLM BLOCK → QUESTION MATCHING
# ==========================================================
def map_student_answers_strong(structured_questions, ocr_output):

    sub_question_ids = extract_sub_question_ids(structured_questions)

    # Detect structured blocks
    answer_blocks = detect_question_anchors(ocr_output)

    prompt = {
        "task": "Map structured answer blocks to correct sub-question IDs.",
        "rules": [
            "Match each block to ONLY ONE sub-question ID",
            "Do NOT merge sub-questions",
            "Return empty string if no matching block",
            "Use pages from block",
            "Return ONLY valid JSON"
        ],
        "sub_question_ids": sub_question_ids,
        "blocks": answer_blocks,
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
                "content": "You are a strict academic answer segmentation engine. Return only valid JSON."
            },
            {
                "role": "user",
                "content": json.dumps(prompt)
            }
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    print("🔍 HYBRID RAW LLM OUTPUT:")
    print(raw)

    try:
        parsed = json.loads(raw)

        # Ensure all IDs exist
        for qid in sub_question_ids:
            if qid not in parsed:
                parsed[qid] = {
                    "answer_text": "",
                    "pages": []
                }

        return parsed

    except Exception as e:
        print("❌ Hybrid JSON Parsing Error:", e)
        return {}