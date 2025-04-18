import json, hashlib
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from dotenv import load_dotenv
load_dotenv()

def _hash_content(func_body, context_code, full_code):
    key = func_body + "\n" + context_code + "\n" + full_code
    return hashlib.sha256(key.encode()).hexdigest()

def split_into_batches(lines, batch_size=200):
    for i in range(0, len(lines), batch_size):
        yield "\n".join(lines[i:i + batch_size])

prompt = PromptTemplate.from_template("""
You are reviewing the function below for **security vulnerabilities**.

Function:
{func_body}

Context:
{context_code}

File:
{full_code}

Look for:
- Trusting raw input without sanitization
- Missing authentication or permission checks
- Leaking internal data via logs or error messages
- Unsafe database or filesystem operations
- CSRF/SQL injection/XSS risks in user-supplied data

Respond with:
- **Security Validation**: <summary or "None">
""")

llm = ChatOpenAI(model_name="gpt-4", temperature=0)
chain = LLMChain(prompt=prompt, llm=llm)

def validate(func_body: str, context_code: str, full_code: str) -> str:
    func_body = "\n".join(func_body.splitlines()[:100])
    context_batches = list(split_into_batches(context_code.splitlines()))
    code_batches = list(split_into_batches(full_code.splitlines()))
    results = []

    for ctx, code in zip(context_batches, code_batches):
        try:
            result = chain.invoke({
                "func_body": func_body,
                "context_code": ctx,
                "full_code": code
            })
            text = result.get("text") or result.get("output") or ""
            
        except Exception:
            continue
        if text and "none" not in text.lower():
            results.append(text.strip())

    return "\n".join(results) if results else "None"
