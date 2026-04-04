import os
import base64
import json
from io import BytesIO
from typing import List, Dict, Any

import cv2
import numpy as np
from pdf2image import convert_from_path
from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import Image, ImageEnhance

load_dotenv()

POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"

text_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

vision_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_VISION_KEY", os.getenv("AZURE_OPENAI_KEY")),
    azure_endpoint=os.getenv("AZURE_OPENAI_VISION_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT")),
    api_version="2024-02-15-preview"
)
VISION_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT")


def enhance_image(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = ImageEnhance.Sharpness(image).enhance(1.5)
    return image


def encode_image(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return base64.b64encode(buffer.getvalue()).decode()


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))


# --------------------------------------------------
# Reject ruled notebook horizontal lines
# --------------------------------------------------
def _is_ruled_lines_region(region_img: np.ndarray) -> bool:
    gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    edges = cv2.Canny(gray, 30, 100)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=40, minLineLength=int(w * 0.55), maxLineGap=10
    )
    if lines is None:
        return False
    horizontal_count = sum(
        1 for line in lines if abs(line[0][3] - line[0][1]) < 6
    )
    return horizontal_count >= 4 and horizontal_count / len(lines) > 0.65


# --------------------------------------------------
# Reject small header boxes (Page No / Date)
# --------------------------------------------------
def _is_header_box(region_img: np.ndarray, page_h: int, region_y: int) -> bool:
    h, w = region_img.shape[:2]
    return (h < page_h * 0.12) and (w < page_h * 0.35) and (region_y < page_h * 0.15)


# --------------------------------------------------
# Reject vertical margin lines
# --------------------------------------------------
def _is_margin_line(region_img: np.ndarray, page_w: int, region_x: int) -> bool:
    h, w = region_img.shape[:2]
    return (w < page_w * 0.04) and (h > page_w * 0.3) and (region_x < page_w * 0.12)


# --------------------------------------------------
# Check if contour is a closed shape
# --------------------------------------------------
def _is_closed_shape(contour) -> bool:
    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0:
        return False
    area = cv2.contourArea(contour)
    circularity = 4 * np.pi * area / (perimeter * perimeter)
    return circularity > 0.3


# --------------------------------------------------
# Core diagram region validator
# --------------------------------------------------
def _is_diagram_region(
    region_img: np.ndarray,
    page_h: int = 0,
    page_w: int = 0,
    region_y: int = 0,
    region_x: int = 0,
) -> bool:
    gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    if _is_ruled_lines_region(region_img):
        return False

    if page_h > 0 and _is_header_box(region_img, page_h, region_y):
        return False

    if page_w > 0 and _is_margin_line(region_img, page_w, region_x):
        return False

    if h < 60 or w < 60:
        return False

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    ink_ratio = np.count_nonzero(binary) / binary.size
    if ink_ratio < 0.018 or ink_ratio > 0.85:
        return False

    edges = cv2.Canny(gray, 50, 150)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=25, minLineLength=18, maxLineGap=8
    )

    if lines is not None:
        non_horizontal = sum(
            1 for line in lines
            if abs(line[0][3] - line[0][1]) / (abs(line[0][2] - line[0][0]) + 1e-5) > 0.15
        )
        if non_horizontal >= 3:
            return True

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    closed_shapes = [
        c for c in contours
        if cv2.contourArea(c) > 150 and _is_closed_shape(c)
    ]
    if len(closed_shapes) >= 2:
        return True

    return False


# --------------------------------------------------
# Remove overlapping regions
# --------------------------------------------------
def _deduplicate_regions(
    regions: List[Dict[str, Any]],
    overlap_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    if not regions:
        return []
    regions = sorted(regions, key=lambda r: r["area"], reverse=True)
    kept = []
    for region in regions:
        overlap = False
        for k in kept:
            ix1 = max(region["x1"], k["x1"])
            iy1 = max(region["y1"], k["y1"])
            ix2 = min(region["x2"], k["x2"])
            iy2 = min(region["y2"], k["y2"])
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                smaller = min(region["area"], k["area"])
                if inter / smaller > overlap_threshold:
                    overlap = True
                    break
        if not overlap:
            kept.append(region)
    return kept


# --------------------------------------------------
# STAGE 1: Extract diagram regions using OpenCV
# --------------------------------------------------
def extract_diagram_regions(pil_image: Image.Image) -> List[Dict[str, Any]]:
    img = pil_to_cv2(pil_image)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    page_h, page_w = img.shape[:2]

    denoised = cv2.fastNlMeansDenoising(gray, h=12)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 30))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)

    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
    dilated = cv2.dilate(closed, kernel_dilate, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    page_area = page_h * page_w
    min_area = page_area * 0.012
    max_area = page_area * 0.90
    padding = 15

    candidates = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h

        if area < min_area or area > max_area:
            continue

        aspect = w / h if h > 0 else 0
        if aspect > 18 or aspect < 0.05:
            continue

        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(page_w, x + w + padding)
        y2 = min(page_h, y + h + padding)

        region_img = img[y1:y2, x1:x2]

        if not _is_diagram_region(
            region_img,
            page_h=page_h,
            page_w=page_w,
            region_y=y1,
            region_x=x1,
        ):
            continue

        candidates.append({
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
            "area": area,
            "pil_image": cv2_to_pil(region_img),
        })

    return _deduplicate_regions(candidates)


# --------------------------------------------------
# STAGE 2: Classify diagram using GPT-4V (vision)
# --------------------------------------------------
def classify_diagram_region(
    region_image: Image.Image,
    page_number: int,
    subject_hint: str = "",
) -> Dict[str, Any]:
    enhanced = enhance_image(region_image)
    b64 = encode_image(enhanced)
    subject_context = f"This is from a {subject_hint} exam paper." if subject_hint else ""

    system_prompt = (
        "You are an expert academic diagram classifier.\n"
        "You receive a cropped image of a single diagram from a handwritten student answer paper.\n"
        f"{subject_context}\n\n"
        "Identify the diagram type from this list:\n"
        "circuit_diagram, flowchart, dfd, uml_class, uml_sequence, uml_usecase, "
        "er_diagram, binary_tree, graph, dfa, nfa, state_diagram, gantt_chart, "
        "truth_table, k_map, physics_sketch, ray_diagram, force_diagram, "
        "free_hand_sketch, other, no_diagram\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        "  \"diagram_type\": \"<type from list above>\",\n"
        "  \"type_confidence\": <0.0 to 1.0>,\n"
        "  \"diagram_labels\": [\"<all visible text labels>\"],\n"
        "  \"diagram_components\": [\"<structural components found>\"],\n"
        "  \"description\": \"<one sentence describing the diagram>\"\n"
        "}"
    )

    try:
        response = vision_client.chat.completions.create(
            model=VISION_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Classify this diagram from page {page_number}."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except Exception as e:
        return {
            "diagram_type": "unknown",
            "type_confidence": 0.0,
            "diagram_labels": [],
            "diagram_components": [],
            "description": "",
            "error": str(e)
        }


# --------------------------------------------------
# STAGE 3: Grade diagram using GPT-4V (vision)
# --------------------------------------------------
def grade_diagram_region(
    region_image: Image.Image,
    classified: Dict[str, Any],
    question_text: str,
    model_answer_description: str,
    max_marks: float,
    subject: str,
    subject_persona: str,
) -> Dict[str, Any]:

    if classified.get("diagram_type") == "no_diagram":
        return {
            "awarded_marks": 0.0,
            "confidence": 1.0,
            "verdict": "blank",
            "correct_components": [],
            "missing_components": ["No diagram drawn"],
            "wrong_components": [],
            "label_feedback": "Student did not draw any diagram.",
            "structure_feedback": "No diagram found.",
            "overall_reasoning": "No diagram drawn. Zero marks awarded.",
            "needs_human_review": False,
        }

    enhanced = enhance_image(region_image)
    b64 = encode_image(enhanced)

    diagram_type = classified.get("diagram_type", "unknown")
    detected_labels = classified.get("diagram_labels", [])
    detected_components = classified.get("diagram_components", [])
    description = classified.get("description", "")

    type_instructions = {
        "circuit_diagram": "Check: correct gates (AND/OR/NOT/NAND/NOR/XOR), proper wire connections, correct output logic, all inputs/outputs labeled.",
        "flowchart": "Check: correct start/end symbols (ovals), process boxes (rectangles), decision diamonds, arrows showing correct flow, all steps present.",
        "dfd": "Check: correct process circles, data stores (parallel lines), external entities (rectangles), data flow arrows with labels.",
        "uml_class": "Check: class name, attributes section, methods section, correct relationships, multiplicity.",
        "uml_sequence": "Check: actor/object lifelines, correct message arrows, sequence order, activation boxes.",
        "uml_usecase": "Check: system boundary, actors (stick figures), use case ovals, association lines.",
        "er_diagram": "Check: entity rectangles, relationship diamonds, attribute ovals, primary keys underlined, correct cardinality.",
        "binary_tree": "Check: correct node values, correct parent-child links, BST property if applicable, proper left/right placement.",
        "graph": "Check: correct nodes and edges, edge weights if weighted, directed/undirected correctly shown, all vertices labeled.",
        "dfa": "Check: all states as circles, start state arrow, accepting states as double circles, all transitions labeled with input symbols.",
        "nfa": "Check: all states, epsilon transitions if present, accepting states, correct transition labels.",
        "state_diagram": "Check: all states present, correct transitions with conditions, initial and final states marked correctly.",
        "gantt_chart": "Check: all processes listed on Y axis, correct time slots on X axis, no overlapping bars, correct order.",
        "truth_table": "Check: correct number of input columns, all input combinations present, correct output values in each row.",
        "k_map": "Check: correct grid size, correct cell values, correct groupings, correct simplified expression.",
        "physics_sketch": "Check: correct diagram type drawn, proper directional arrows, all components labeled with correct names and units.",
    }

    grading_instructions = type_instructions.get(
        diagram_type,
        "Check all visible components, labels, connections, and overall correctness."
    )

    prompt = f"""
{subject_persona}

You are grading a student's hand-drawn {diagram_type} from a scanned {subject} exam answer paper.
The student's actual diagram image is attached — look at it carefully before writing anything.

QUESTION:
{question_text}

MODEL ANSWER DESCRIPTION:
{model_answer_description}

GRADING CRITERIA FOR {diagram_type.upper()}:
{grading_instructions}

Maximum marks for this diagram: {max_marks}

STRICT RULES:
1. Every point in correct_components, missing_components, wrong_components MUST reference what the student ACTUALLY drew.
2. label_feedback must name the ACTUAL labels visible in the student's diagram specifically.
3. overall_reasoning must be specific to THIS student's diagram — never generic.
4. Do NOT copy from model answer — evaluate what the student DREW.

Return ONLY valid JSON:
{{
  "awarded_marks": <float 0 to {max_marks}>,
  "confidence": <float 0.0 to 1.0>,
  "verdict": "<correct | partially_correct | incorrect | blank>",
  "correct_components": ["<specific correct things student drew>"],
  "missing_components": ["<specific things missing>"],
  "wrong_components": ["<specific mistakes with what student drew vs what it should be>"],
  "label_feedback": "<specific label-by-label feedback>",
  "structure_feedback": "<specific structural feedback>",
  "overall_reasoning": "<teacher-style comment specific to THIS student's diagram>",
  "needs_human_review": <true if confidence below 0.65>
}}
""".strip()

    try:
        response = vision_client.chat.completions.create(
            model=VISION_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a strict but fair {subject} professor grading handwritten diagrams. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        awarded = max(0.0, min(float(data.get("awarded_marks", 0)), max_marks))
        data["awarded_marks"] = round(awarded, 2)
        confidence = float(data.get("confidence", 0.5))
        data["needs_human_review"] = data.get("needs_human_review", confidence < 0.65)
        return data

    except Exception as e:
        return {
            "awarded_marks": 0.0,
            "confidence": 0.0,
            "verdict": "error",
            "correct_components": [],
            "missing_components": [],
            "wrong_components": [],
            "label_feedback": "",
            "structure_feedback": "",
            "overall_reasoning": f"Grading failed: {str(e)}",
            "needs_human_review": True,
        }


# --------------------------------------------------
# MAIN FUNCTION — backward compatible
# --------------------------------------------------
def detect_diagrams_from_pdf(
    pdf_path: str,
    subject: str = "",
    subject_persona: str = "You are a strict but fair university professor.",
    question_text: str = "",
    model_answer_description: str = "",
    max_marks: float = 0.0,
) -> List[Dict[str, Any]]:

    pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    results = []

    for page_number, page_image in enumerate(pages, start=1):
        print(f"[DIAGRAM DETECTOR] Processing page {page_number}/{len(pages)}")

        regions = extract_diagram_regions(page_image)

        if not regions:
            print(f"  → No diagram regions found on page {page_number}")
            results.append({
                "page": page_number,
                "diagram_present": False,
                "diagram_type": "",
                "diagram_labels": [],
                "diagram_components": [],
                "description": "",
                "regions_found": 0,
                "grade": None,
            })
            continue

        print(f"  → {len(regions)} region(s) found on page {page_number}")

        classified_regions = []
        for i, region in enumerate(regions):
            print(f"  → Classifying region {i + 1}/{len(regions)}")
            classified = classify_diagram_region(
                region_image=region["pil_image"],
                page_number=page_number,
                subject_hint=subject,
            )
            classified["region_index"] = i
            classified["region_coords"] = {
                "x1": region["x1"], "y1": region["y1"],
                "x2": region["x2"], "y2": region["y2"],
            }
            classified_regions.append((region, classified))

        valid = [
            (r, c) for r, c in classified_regions
            if c.get("diagram_type") not in ("no_diagram", "unknown")
        ]

        if not valid:
            best_region, best_classified = classified_regions[0]
        else:
            best_region, best_classified = max(
                valid, key=lambda x: x[1].get("type_confidence", 0)
            )

        grade_result = None
        if max_marks > 0 and question_text:
            print(f"  → Grading diagram on page {page_number}")
            grade_result = grade_diagram_region(
                region_image=best_region["pil_image"],
                classified=best_classified,
                question_text=question_text,
                model_answer_description=model_answer_description,
                max_marks=max_marks,
                subject=subject,
                subject_persona=subject_persona,
            )

        results.append({
            "page": page_number,
            "diagram_present": best_classified.get("diagram_type") not in ("no_diagram", "unknown"),
            "diagram_type": best_classified.get("diagram_type", ""),
            "type_confidence": best_classified.get("type_confidence", 0.0),
            "diagram_labels": best_classified.get("diagram_labels", []),
            "diagram_components": best_classified.get("diagram_components", []),
            "description": best_classified.get("description", ""),
            "regions_found": len(regions),
            "all_regions": [c for _, c in classified_regions],
            "grade": grade_result,
        })

    return results