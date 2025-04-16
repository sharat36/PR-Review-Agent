# context_extractor.py
import re


def extract_related_context(func_body, full_code):
    related_context = {
        "methods": {},
        "classes": {},
        "variables": {}
    }

    # 1. Extract all functions in file
    function_pattern = re.compile(r'(public|private|protected)?\s*function\s+(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE)
    for match in function_pattern.finditer(full_code):
        start = match.start()
        name = match.group(2)
        body = extract_block(full_code, start)
        related_context['methods'][name] = body

    # 2. Extract all class definitions
    class_pattern = re.compile(r'class\s+(\w+)\s*(extends\s+\w+)?\s*\{', re.MULTILINE)
    for match in class_pattern.finditer(full_code):
        start = match.start()
        name = match.group(1)
        body = extract_block(full_code, start)
        related_context['classes'][name] = body

    # 3. Extract variable initializations
    var_pattern = re.compile(r'\$(\w+)\s*=\s*[^;]+;', re.MULTILINE)
    for match in var_pattern.finditer(full_code):
        name = match.group(1)
        related_context['variables'][name] = match.group(0)

    # 4. Scan func_body for usage
    needed_context = {
        "setDetails_body": None,
        "save_model_class": None,
        "params_initialization": None
    }

    # Detect method calls like $this->setDetails or setDetails(...)
    if match := re.search(r'(\$this->)?setDetails\s*\(', func_body):
        if 'setDetails' in related_context['methods']:
            needed_context['setDetails_body'] = related_context['methods']['setDetails']

    # Detect save() call like $log->save() and guess class by var name
    if match := re.search(r'\$(\w+)->save\(', func_body):
        var_name = match.group(1)
        class_match = re.search(rf'\${var_name}\s*=\s*new\s+(\w+)', full_code)
        if class_match:
            class_name = class_match.group(1)
            if class_name in related_context['classes']:
                needed_context['save_model_class'] = related_context['classes'][class_name]

    # Detect usage of $params['something']
    if 'params' in related_context['variables']:
        needed_context['params_initialization'] = related_context['variables']['params']

    return needed_context


def extract_block(code, start_index):
    brace_count = 0
    inside = False
    block = []
    for i in range(start_index, len(code)):
        c = code[i]
        block.append(c)
        if c == '{':
            brace_count += 1
            inside = True
        elif c == '}':
            brace_count -= 1
        if inside and brace_count == 0:
            break
    return ''.join(block).strip()
