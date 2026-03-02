import json
import os
from typing import Dict, List, Any
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def map_answers_with_llm(
    questions: Dict[str, Any],
    answer_blocks: List[Dict[str, Any]]
) -> Dict[str, List[str]]:

    prompt = {
        "role": "user",
        "content": json.dumps({
            "task": "Map answer blocks to correct question IDs.",
            "rules": [
                "Only assign a block if it clearly answers the question",
                "A block can belong to only one question",
                "Return empty list if not answered",
                "Return ONLY valid JSON"
            ],
            "questions": questions,
            "answer_blocks": answer_blocks
        })
    }

    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a strict academic evaluator. Return only JSON."
            },
            prompt
        ],
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
    except:
        parsed = {}

    final_mapping = {}
    used_blocks = set()

    for qid, block_ids in parsed.items():
        final_mapping[qid] = []

        if not isinstance(block_ids, list):
            continue

        for bid in block_ids:
            if bid not in used_blocks:
                final_mapping[qid].append(bid)
                used_blocks.add(bid)

    return final_mapping