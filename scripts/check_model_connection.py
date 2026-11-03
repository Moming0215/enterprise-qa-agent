"""Check model availability without printing credentials or response bodies."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()
try:
    response = ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        timeout=12,
        max_retries=0,
    ).invoke("Return OK")
    print("model_available", bool(response.content))
except Exception as exc:
    print("model_unavailable", type(exc).__name__, getattr(exc, "status_code", None),
          getattr(exc, "code", None))
