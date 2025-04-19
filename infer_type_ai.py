import json
import hashlib
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
load_dotenv()

# --- Cache path ---
CACHE_PATH = "infer_type_cache.json"
try:
    with open(CACHE_PATH, 'r') as f:
        _CACHE = json.load(f)
except:
    _CACHE = {}

# --- Hashing utility for deduplication ---
def _hash_content(func_body, context_code, full_code):
    key = func_body + "\n" + context_code + "\n" + full_code
    return hashlib.sha256(key.encode()).hexdigest()

# --- AI Prompt ---
prompt = PromptTemplate.from_template("""
You are a static analysis AI for PHP code.

Analyze the function and context below, and for every variable like $params['key'], $application->field, $log->x, infer the type.

Function:
{func_body}

Context:
{context_code}

Full File Code:
{full_code}

Return a JSON object like:
{ 
  "$params['task']->trigger_date": {"string": 3, "null": 1},
  "$application->tenant_id": {"int": 2, "unknown": 1}
}
Only return the JSON.
""")

llm = ChatOpenAI(model_name="gpt-4", temperature=0)
chain = LLMChain(prompt=prompt, llm=llm)

# --- Batch Utility ---
def split_into_batches(lines, batch_size):
    for i in range(0, len(lines), batch_size):
        yield "\n".join(lines[i:i + batch_size])

# --- Main Function ---
def infer_type(func_body: str, context_code: str, full_code: str, max_batch_lines=200) -> dict:
    func_body = "\n".join(func_body.splitlines()[:100])  # truncate just in case

    context_lines = context_code.splitlines()
    code_lines = full_code.splitlines()

    context_batches = list(split_into_batches(context_lines, max_batch_lines))
    code_batches = list(split_into_batches(code_lines, max_batch_lines))

    merged_result = {}

    # Run across all batch pairs
    for i, (ctx, full) in enumerate(zip(context_batches, code_batches)):
        cache_key = _hash_content(func_body, ctx, full)
        if cache_key in _CACHE:
            result = _CACHE[cache_key]
        else:
            try:
                output = chain.invoke({
                    "func_body": func_body,
                    "context_code": ctx,
                    "full_code": full
                })
                result_text = output.get("text") or output.get("output") or ""
                result = json.loads(result_text.strip())
                # _CACHE[cache_key] = result
                # with open(CACHE_PATH, 'w') as f:
                #     json.dump(_CACHE, f)
            except Exception:
                continue  # skip failed batches

        # Merge batch result into global dict
        for k, v in result.items():
            if k not in merged_result:
                merged_result[k] = v
            elif isinstance(v, dict):
                for t, c in v.items():
                    merged_result[k][t] = merged_result[k].get(t, 0) + c

    return merged_result
