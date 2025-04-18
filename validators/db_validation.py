
import json, hashlib
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

load_dotenv()

CACHE_PATH = "db_validation_cache.json"
try:
    with open(CACHE_PATH, 'r') as f:
        _CACHE = json.load(f)
except:
    _CACHE = {}

def _hash_content(code):
    return hashlib.sha256(code.encode()).hexdigest()

prompt = PromptTemplate.from_template("""
You are a PHP reviewer for MongoDB/Yii-based applications.

Changed Lines:
{changed_code}

Full File:
{full_code}

Focus only on the changed lines.

If a new `select()` is introduced above an existing `save()` or `saveAttributes()`, does this change create a risk of partial document overwrite?

Respond only if there's a risk. Otherwise say "None".
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
        _CACHE[cache_key] = text
        with open(CACHE_PATH, "w") as f:
            json.dump(_CACHE, f)
        return text
    except Exception as e:
        return f"Error: {e}"
