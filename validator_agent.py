# validator_agent.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AVAILABLE_VALIDATORS = [
    "input_validation",
    "tenant_validation",
    "security_validation",
    "logic_validation",
    "db_validation"
]

def suggest_validators(func_body: str, context_code: str) -> list[str]:
    prompt = f"""
You are an intelligent agent assisting a static code analyzer.

Based on the function and its context, select the most relevant validation categories from the following:
- input_validation
- tenant_validation
- security_validation
- logic_validation
- db_validation

Function:
{func_body}

Context:
{context_code}

Return a comma-separated list of only the relevant validator names (e.g., input_validation, db_validation). Do not include any explanation.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=50
        )
        output = response.choices[0].message.content.strip()
        selected = [v.strip() for v in output.split(",") if v.strip() in AVAILABLE_VALIDATORS]
        return selected
    except Exception as e:
        print("❌ validator_agent error:", e)
        return AVAILABLE_VALIDATORS  # fallback to run all
