import json, hashlib
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from dotenv import load_dotenv
load_dotenv()

CACHE_PATH = "input_validation_cache.json"
try:
    with open(CACHE_PATH, 'r') as f:
        _CACHE = json.load(f)
except:
    _CACHE = {}

def _hash_content(func_body, context_code, full_code):
    key = func_body + "\n" + context_code + "\n" + full_code
    return hashlib.sha256(key.encode()).hexdigest()

def split_into_batches(lines, batch_size=200):
    for i in range(0, len(lines), batch_size):
        yield "\n".join(lines[i:i + batch_size])

prompt = PromptTemplate.from_template("""
You are reviewing the function below for **input validation issues**.

Function:
{func_body}

Context:
{context_code}

File:
{full_code}

Look for:
- Missing type checks for parameters
- Null checks missing before accessing keys/fields
- Unexpected inputs not handled
- Trusting input data blindly

Respond with:
- **Input Validation**: <summary or "None">
""")

llm = ChatOpenAI(model_name="gpt-4", temperature=0)
chain = LLMChain(prompt=prompt, llm=llm)

def validate(func_body: str, context_code: str, full_code: str) -> str:
    func_body = "\n".join(func_body.splitlines()[:100])
    context_batches = list(split_into_batches(context_code.splitlines()))
    code_batches = list(split_into_batches(full_code.splitlines()))
    results = []

    for ctx, code in zip(context_batches, code_batches):
        cache_key = _hash_content(func_body, ctx, code)
        if cache_key in _CACHE:
            text = _CACHE[cache_key]
        else:
            try:
                result = chain.invoke({
                    "func_body": func_body,
                    "context_code": ctx,
                    "full_code": code
                })
                text = result.get("text") or result.get("output") or ""
                _CACHE[cache_key] = text
                with open(CACHE_PATH, "w") as f:
                    json.dump(_CACHE, f)
            except Exception:
                continue
        if text and "none" not in text.lower():
            results.append(text.strip())

    return "\n".join(results) if results else "None"
