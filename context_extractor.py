import re
import os

def extract_related_context(func_body: str, full_code: str, file_path: str = None) -> str:
    context = ""

    # Extract model class used inside the function

    for model_class in extract_model_classes(func_body, file_path):
        context += get_class_code(model_class, full_code)
        context += get_method_code(model_class, "tenant", full_code)
        context += get_method_code(model_class, "save", full_code)
        parent = get_parent_class(model_class, full_code)
        if parent:
            context += get_method_code(parent, "tenant", full_code)
            context += get_method_code(parent, "save", full_code)

    return context


def get_class_code(class_name: str, code: str) -> str:
    pattern = rf'class\s+{re.escape(class_name)}\b.*?\{{.*?^\}}'
    match = re.search(pattern, code, re.DOTALL | re.MULTILINE)
    if match:
        return f"\n// Class: {class_name}\n" + match.group(0) + "\n"
    return ""


def get_method_code(class_name: str, method_name: str, code: str) -> str:
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
    pattern = rf'class\s+{re.escape(class_name)}\s+extends\s+(\w+)'
    match = re.search(pattern, code)
    return match.group(1) if match else None


def extract_model_classes(func_body: str, fallback_file_path: str = None) -> list[str]:
    matches = re.findall(r'(\w+)::model\(\)', func_body)
    model_classes = set()

    for match in matches:
        if match == "static" and fallback_file_path:
            filename = os.path.basename(fallback_file_path)
            if filename.lower().endswith('.php'):
                model_classes.add(filename[:-4])
        elif match != "static":
            model_classes.add(match)

    return list(model_classes)
