
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

def _hash_content(code):
    return hashlib.sha256(code.encode()).hexdigest()

prompt = PromptTemplate.from_template("""
You are reviewing changed lines in a PHP function for input validation issues.

Changed Lines:
{changed_code}

Full File:
{full_code}

Focus only on the changed lines.

please consider these changes as risk
- Parameters used without null/type checks
- Direct access to array keys/fields without validation
- Check when statically accessing any variable or function if that class name is correct and case sensitive

Only return issues caused by these changes. Respond with "None" if no new risks.
""")

llm = ChatOpenAI(model_name="gpt-4", temperature=0)
chain = LLMChain(prompt=prompt, llm=llm)

def validate(changed_lines: list[str], full_code: str) -> str:
    changed_code = "\n".join(changed_lines)
    cache_key = _hash_content(changed_code + full_code)

    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        result = chain.invoke({
            "changed_code": changed_code,
            "full_code": full_code
        })
        text = result.get("text") or result.get("output") or "None"
        # _CACHE[cache_key] = text
        # with open(CACHE_PATH, "w") as f:
        #     json.dump(_CACHE, f)
        return text
    except Exception as e:
        return f"Error: {e}"
