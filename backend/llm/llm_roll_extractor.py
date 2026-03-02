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


def extract_roll_number_with_llm(ocr_output):

    # Only use first page
    first_page_text = ""
    first_page = ocr_output[0]

    for line in first_page["lines"]:
        first_page_text += line["text"] + "\n"

    prompt = {
        "task": "Extract student roll number.",
        "rules": [
            "Return only digits.",
            "Ignore labels like Roll No, Seat No.",
            "If multiple numbers exist, choose number near 'Roll'.",
            "If not found return UNKNOWN.",
            "Return JSON format: { roll_number: '' }"
        ],
        "text": first_page_text
    }

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "You extract only roll number digits from exam header. Return JSON only."
            },
            {
                "role": "user",
                "content": json.dumps(prompt)
            }
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
        roll = parsed.get("roll_number", "UNKNOWN")

        # Safety: ensure digits only
        roll = "".join(filter(str.isdigit, roll))

        return roll if roll else "UNKNOWN"

    except:
        return "UNKNOWN"