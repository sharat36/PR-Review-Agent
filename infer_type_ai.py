# infer_type_ai.py (stream-ready with caching)
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
REPO_PATH = "/data"

_type_cache = {}
_class_summary_cache = {}

def find_class_code_across_repo(class_name, repo_path=REPO_PATH):
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".php"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if f'class {class_name}' in content:
                            return content
                except:
                    continue
    return ""

def summarize_php_code(code):
    if code in _class_summary_cache:
        return _class_summary_cache[code]

    prompt = f"""
You are a PHP summarizer.

Summarize this class code by extracting:
- Class name and parent
- All public/protected properties
- All method signatures

Only output a clean summary, no explanation.

Code:
{code}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=500
        )
        result = response.choices[0].message.content.strip()
        _class_summary_cache[code] = result
        return result
    except Exception as e:
        return f"# summarization_error: {e}"

def extract_class_method_context(expr, full_code, current_class_name=None):
    if current_class_name and "static::" in expr:
        expr = expr.replace("static::", f"{current_class_name}::")

    match = re.match(r'(\w+)::(\w+)', expr)
    if not match:
        return ""
    class_name, method_name = match.groups()

    external_code = find_class_code_across_repo(class_name)
    if external_code:
        return summarize_php_code(external_code) + "\n\n" + full_code

    return full_code

def fetch_variable_class(expr, context_code):
    var_match = re.match(r'\$(\w+)->', expr)
    if not var_match:
        return ""
    var_name = var_match.group(1)
    assignment_pattern = re.compile(rf'\${var_name}\s*=\s*([\w:]+)::model\(\)->[\w]+\(.*?\);')
    match = assignment_pattern.search(context_code)
    if match:
        class_name = match.group(1)
        raw_class_code = find_class_code_across_repo(class_name)
        if raw_class_code:
            return summarize_php_code(raw_class_code)
    return ""

def infer_type_ai(expr, context_code="", current_class_name=None):
    if expr in _type_cache:
        return _type_cache[expr]

    class_context = ""
    if '::' in expr:
        class_context += extract_class_method_context(expr, context_code, current_class_name=current_class_name)

    if '->' in expr:
        class_context += fetch_variable_class(expr, context_code)

    full_context = class_context + "\n\n" + context_code

    prompt = f"""
You are a PHP static analysis engine.

Given the following code context and expression, infer the most likely type of the expression.

Expression:
{expr}

Context:
{full_context}

Respond with only one of the following:
- int
- string
- float
- bool
- array
- object
- class:<ClassName>
- null
- unknown
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a static analysis engine for PHP code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=10,
            stream=False
        )
        answer = response.choices[0].message.content.strip().lower()
        if answer == "unknown":
            answer = f"manual_type_needed_for:{expr}"
        _type_cache[expr] = answer
        return answer
    except Exception as e:
        return f"error_in_type_inference:{expr} — {e}"
