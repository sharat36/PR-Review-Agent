
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

please consider these changes as risk
- If a new `select()` is introduced above an existing `save()` or `saveAttributes()`.
- If we fetch a object using select and try to access any variable of that object which is not there in select
- If `EMongoCriteria` is created but **not used** in the `find()` or `findAll()` call
- If `findAll()` is called without any criteria or filtering
".
""")

llm = ChatOpenAI(model_name="gpt-4", temperature=0)
chain = LLMChain(prompt=prompt, llm=llm)

def validate(changed_lines: list[str], full_code: str) -> str:
    changed_code = "\n".join(changed_lines)
    cache_key = _hash_content(changed_code + full_code)

    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        inputs = {"full_code": full_code, "changed_code": changed_code}
        formatted_prompt = chain.prompt.format_prompt(**inputs).to_string()
        print("🧠 Prompt to DB Agent:\n", formatted_prompt)
        result = chain.invoke(inputs)

        text = result.get("text") or result.get("output") or "None"
        # _CACHE[cache_key] = text
        # with open(CACHE_PATH, "w") as f:
        #     json.dump(_CACHE, f)
        return text
    except Exception as e:
        return f"Error: {e}"
