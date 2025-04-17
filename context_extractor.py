import re
import os

def extract_related_context(func_body: str, full_code: str) -> str:
    context = ""

    # Extract model class from usage like static::model()
    model_match = re.search(r'(\w+)::model\(\)', func_body)
    model_class = model_match.group(1) if model_match else None

    # If a model is detected, extract its class code
    if model_class:
        context += get_class_code(model_class, full_code)

        # If model extends a parent class, include parent's methods like tenant()
        parent_class = get_parent_class(model_class, full_code)
        if parent_class:
            context += get_method_code(parent_class, "tenant", full_code)
            context += get_method_code(parent_class, "save", full_code)

        # Also extract tenant() and save() if overridden in model itself
        context += get_method_code(model_class, "tenant", full_code)
        context += get_method_code(model_class, "save", full_code)

    return context


def get_class_code(class_name: str, code: str) -> str:
    """
    Extract full class definition (excluding method bodies) for summary context.
    """
    pattern = rf'class\s+{re.escape(class_name)}\b.*?\{{.*?^\}}'
    match = re.search(pattern, code, re.DOTALL | re.MULTILINE)
    if match:
        return f"\n// Class: {class_name}\n" + match.group(0) + "\n"
    return ""


def get_method_code(class_name: str, method_name: str, code: str) -> str:
    """
    Extract a method from the class body (roughly) using brace matching.
    """
    pattern = rf'class\s+{re.escape(class_name)}.*?\{{(.*?)^\}}'
    class_match = re.search(pattern, code, re.DOTALL | re.MULTILINE)
    if not class_match:
        return ""

    class_body = class_match.group(1)
    method_pattern = rf'function\s+{re.escape(method_name)}\s*\(.*?\)\s*\{{'
    start = re.search(method_pattern, class_body)
    if not start:
        return ""

    idx = start.start()
    brace_count = 0
    method_lines = []
    in_method = False

    for line in class_body[idx:].splitlines():
        if '{' in line:
            brace_count += line.count('{')
            in_method = True
        if '}' in line:
            brace_count -= line.count('}')
        method_lines.append(line)
        if in_method and brace_count == 0:
            break

    return f"\n// {class_name}::{method_name}()\n" + "\n".join(method_lines) + "\n"


def get_parent_class(class_name: str, code: str) -> str:
    """
    Get parent class from definition like: class Foo extends Bar
    """
    pattern = rf'class\s+{re.escape(class_name)}\s+extends\s+(\w+)'
    match = re.search(pattern, code)
    return match.group(1) if match else None
