# infer_type_ai.py
import os
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def find_class_code_across_repo(class_name):
    for root, _, files in os.walk(os.getenv("REPO")):
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

def extract_class_method_context(expr, full_code, current_class_name=None):
    if current_class_name and "static::" in expr:
        expr = expr.replace("static::", f"{current_class_name}::")

    match = re.match(r'(\w+)::(\w+)', expr)
    if not match:
        return ""
    class_name, method_name = match.groups()

    code_source = full_code
    external_code = find_class_code_across_repo(class_name)
    if external_code:
        code_source = external_code + "\n" + full_code

    class_pattern = re.compile(rf'class\s+{re.escape(class_name)}\b[\s\S]+?\n\}}', re.MULTILINE)
    class_match = class_pattern.search(code_source)
    if not class_match:
        return ""
    class_body = class_match.group()

    method_pattern = re.compile(rf'function\s+{re.escape(method_name)}\s*\((.*?)\)\s*\{{[\s\S]+?\n\}}', re.MULTILINE)
    method_match = method_pattern.search(class_body)
    if method_match:
        return f"Class {class_name} with method {method_name}():\n" + method_match.group()

    return f"Class {class_name}:\n{class_body}"

def infer_type_ai(expr, context_code="", current_class_name=None):
    if '::' in expr:
        class_context = extract_class_method_context(expr, context_code, current_class_name=current_class_name)
        context_code = class_context + "\n\n" + context_code

    prompt = f"""
You are a PHP static analysis engine.

Given the following code context and expression, infer the most likely type of the expression.

Expression:
{expr}

Context:
{context_code}

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
            n=1
        )
        answer = response.choices[0].message.content.strip().lower()
        if answer == "unknown":
            print(f"⚠️ Unable to infer type for: {expr}")
            answer = input("Please enter the type manually (e.g., string, int, array, class:MyClass): ").strip().lower()
        return answer
    except Exception as e:
        print(f"[OpenAI error] Failed to infer type for: {expr} — {e}")
        return "unknown"