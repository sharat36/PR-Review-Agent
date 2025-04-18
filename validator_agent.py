import json
import hashlib
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from dotenv import load_dotenv
load_dotenv()


# --- Utility to hash each input combination ---
def _hash_content(func_body, full_code, review_level):
    key = func_body + "\n" + full_code + "\n" + review_level
    return hashlib.sha256(key.encode()).hexdigest()

# --- Batch Utility ---
def split_into_batches(lines, batch_size):
    for i in range(0, len(lines), batch_size):
        yield "\n".join(lines[i:i + batch_size])

# --- Main Function ---
def suggest_validators(func_body: str, full_code: str, review_level: str = "standard") -> list:
    func_body = "\n".join(func_body.splitlines()[:100])  # safe trim

    code_lines = full_code.splitlines()
    code_batches = list(split_into_batches(code_lines, 200))

    all_validators = set()

    prompt = PromptTemplate.from_template("""
You are an expert code reviewer for a PHP/Yii/MongoDB codebase.

Based on the provided function and review level, select the most appropriate validators to apply.

Function:
{func_body}

Review Level: {review_level}

Context:
{full_code}

Choose from:
- input_validation
- tenant_validation
- logic_validation
- db_validation
- security_validation

Return only a comma-separated list of validators. No explanation.
""")

    llm = ChatOpenAI(model_name="gpt-4", temperature=0)
    chain = LLMChain(prompt=prompt, llm=llm)

    for batch in code_batches:
        try:
            result = chain.invoke({
                "func_body": func_body,
                "review_level": review_level,
                "full_code": batch
            })
            raw = result.get("text") or result.get("output") or ""
        except Exception:
            continue

        for v in raw.split(","):
            v = v.strip()
            if v:
                all_validators.add(v)

    return list(all_validators)
