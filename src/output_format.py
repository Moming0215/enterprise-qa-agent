"""Parse a model's final JSON without accepting multiple competing answers."""

import json
import re


def parse_final(content) -> dict:
    if not isinstance(content, str):
        raise ValueError("final_content_not_text")
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("final_content_not_object")
    return value
