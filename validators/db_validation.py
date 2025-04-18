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
You are reviewing the function below for **database safety and correctness**.

Function:
{func_body}

Context:
{context_code}

File:
{full_code}

Look for:
- Focus on improper use of `find()`, `findAll()`, `save()`, or `update()` without any filters or result checks
- ⚠️ Flag if `EMongoCriteria` is created but **not used** in the `find()` or `findAll()` call
- ⚠️ Also flag if `findAll()` is called without any criteria or filtering
- ⚠️ Also warn if `tenant()` is used but `tenant_id` is not validated
- Provide concise output like:
  - **Database Safety**: <bullet point>

Respond with:
- **Database Safety**: <summary or "None">
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
