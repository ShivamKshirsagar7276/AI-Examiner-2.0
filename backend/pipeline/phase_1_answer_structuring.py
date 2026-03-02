from typing import List, Dict
import re


NOISE_REGEX = re.compile(
    r"(do\s+not\s+write|seat\s+no|roll\s+no|attempt\s+any|question\s+no)",
    re.IGNORECASE
)

QUESTION_HEADER_REGEX = re.compile(r"^Q\.?\s*\d+", re.IGNORECASE)
SUBPART_REGEX = re.compile(r"^\(?[a-e]\)?\s*[.)]?", re.IGNORECASE)


def flatten_ocr_pages(ocr_pages: List[Dict]) -> List[Dict]:
    flattened = []

    for page in ocr_pages:
        for line in page["lines"]:
            text = line.get("text", "").strip()
            if text:
                flattened.append({
                    "page": page["page_number"],
                    "text": text
                })

    return flattened


def structure_answers(flattened_lines: List[Dict]) -> List[Dict]:
    blocks = []
    current = None
    block_id = 0

    for item in flattened_lines:
        text = item["text"]
        page = item["page"]

        if NOISE_REGEX.search(text):
            current = None
            continue

        if QUESTION_HEADER_REGEX.match(text):
            current = None
            continue

        if SUBPART_REGEX.match(text):
            if current:
                blocks.append(current)

            block_id += 1
            current = {
                "block_id": f"B{block_id}",
                "answer_text": text,
                "page_range": {page}
            }
            continue

        if current is None:
            block_id += 1
            current = {
                "block_id": f"B{block_id}",
                "answer_text": text,
                "page_range": {page}
            }
        else:
            current["answer_text"] += " " + text
            current["page_range"].add(page)

    if current:
        blocks.append(current)

    for b in blocks:
        b["page_range"] = sorted(list(b["page_range"]))

    return blocks


def phase_1_5_pipeline(ocr_pages: List[Dict]) -> Dict:
    flattened = flatten_ocr_pages(ocr_pages)
    answer_blocks = structure_answers(flattened)

    return {
        "total_blocks": len(answer_blocks),
        "answer_blocks": answer_blocks
    }