import os
import base64
import json
from typing import List, Dict, Any

from pdf2image import convert_from_path
from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import ImageEnhance

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"


# --------------------------------------------------
# Image Enhancer (important for faint diagrams)
# --------------------------------------------------
def enhance_image(image):
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.8)  # increase contrast
    return image


# --------------------------------------------------
# Encode image to base64
# --------------------------------------------------
def encode_image(image) -> str:
    from io import BytesIO
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


# --------------------------------------------------
# Main Diagram Detection
# --------------------------------------------------
def detect_diagrams_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:

    # 5.1 Convert PDF → High Resolution Images
    pages = convert_from_path(
        pdf_path,
        dpi=350,
        poppler_path=POPPLER_PATH
    )

    results = []

    for page_number, page_image in enumerate(pages, start=1):

        print(f"[DIAGRAM DETECTOR] Processing page {page_number}")

        # 5.2 Enhance image
        page_image = enhance_image(page_image)

        base64_image = encode_image(page_image)

        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an academic diagram detection engine.\n"
                            "Detect whether this page contains a structured visual diagram.\n"
                            "A diagram includes circles, arrows, flow structures, "
                            "state transitions, blocks, or connected shapes.\n\n"
                            "If diagram exists:\n"
                            "- diagram_present = true\n"
                            "- diagram_type = short type (e.g., State Diagram)\n"
                            "- diagram_labels = all text inside diagram shapes\n"
                            "- description = short explanation\n\n"
                            "If no diagram exists, set diagram_present = false.\n\n"
                            "Return ONLY valid JSON in this format:\n"
                            "{"
                            "\"diagram_present\": true/false,"
                            "\"diagram_type\": \"\","
                            "\"diagram_labels\": [],"
                            "\"description\": \"\""
                            "}"
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Analyze page {page_number} of an exam answer sheet."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0
            )

            raw = response.choices[0].message.content.strip()

            parsed = json.loads(raw)

        except Exception as e:
            parsed = {
                "diagram_present": False,
                "diagram_type": "",
                "diagram_labels": [],
                "description": "",
                "error": str(e)
            }

        parsed["page"] = page_number
        results.append(parsed)

    return results