import json
import hashlib
from langchain_openai import ChatOpenAI

# Simple in-memory cache to avoid duplicate calls
_cache = {}

def infer_type(func_body: str, context_code: str, full_file_code: str) -> dict:
    """
    Infer variable types and structure from PHP code using GPT-4.
    Uses function body, surrounding context, and full file code.
    """

    # Cache key for memoization
    cache_key = hashlib.md5((func_body + context_code + full_file_code).encode()).hexdigest()
    if cache_key in _cache:
        return _cache[cache_key]

    # Prompt template
    prompt = f"""
You are a PHP static analyzer.

Your job is to infer the types and structure of variables and expressions used in this function.

Function:
{func_body}

Context (other class methods, helpers):
{context_code}

Full File Code (includes declarations, helper functions, model instantiations):
{full_file_code}

Return a valid JSON object where:
- Each key is a variable or expression (e.g., `$application->tenant_id`, `$params['task']`)
- Each value is an object with possible types and their occurrence counts
- Valid types: "string", "int", "bool", "null", "array", "object", "unknown", or "class:ClassName"

Example output:

{{
  "$application": {{ "class:ApplicationModel": 2 }},
  "$application->tenant_id": {{ "string": 2 }},
  "$params['task']": {{ "class:TaskModel": 2, "null": 1 }}
}}

Respond ONLY with valid JSON — no markdown, no explanation, no code fences.
"""

    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        raw = llm.invoke(prompt).content.strip()

        # Clean up accidental markdown fences
        if raw.startswith("```"):
            raw = raw.strip("```").replace("json", "").strip()

        parsed = json.loads(raw)
        _cache[cache_key] = parsed
        return parsed

    except Exception as e:
        return {
            "error": f"infer_type_ai failed: {str(e)}",
            "raw_output": raw if 'raw' in locals() else ""
        }
