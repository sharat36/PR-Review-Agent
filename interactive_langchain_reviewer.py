# langchain_pr_reviewer.py (parallel + caching, no streaming)
import os
import re
import subprocess
import concurrent.futures
from time import sleep
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from context_extractor import extract_related_context
from param_type_analyzer import extract_function_definitions, extract_function_calls, resolve_param_types, find_odd_types
from infer_type_ai import infer_type_ai

load_dotenv()

user_input_response = None

def set_user_input(text):
    global user_input_response
    user_input_response = text

def get_changed_functions_with_bodies(base_branch, pr_branch, repo_path):
    subprocess.run(["git", "checkout", pr_branch], cwd=repo_path)
    diff_output = subprocess.run(
        ["git", "diff", f"{base_branch}...{pr_branch}", "--unified=0", "--", "*.php"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        text=True
    ).stdout

    file_changes = {}
    current_file = None
    for line in diff_output.splitlines():
        if line.startswith("diff --git"):
            match = re.search(r'b/(.*\.php)', line)
            if match:
                current_file = os.path.join(repo_path, match.group(1))
                file_changes[current_file] = set()
        elif line.startswith("@@") and current_file:
            match = re.search(r'\+(\d+)', line)
            if match:
                line_no = int(match.group(1))
                file_changes[current_file].add(line_no)

    def extract_function_body(filepath, line_numbers):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            funcs = []
            for idx in line_numbers:
                i = idx - 1
                while i >= 0:
                    if re.search(r'function\s+(\w+)\s*\(', lines[i]):
                        break
                    i -= 1

                if i < 0:
                    continue

                func_name_match = re.search(r'function\s+(\w+)\s*\(', lines[i])
                if not func_name_match:
                    continue

                func_name = func_name_match.group(1)
                body_lines = [lines[i]]
                brace_count = lines[i].count('{') - lines[i].count('}')
                j = i + 1
                while j < len(lines):
                    body_lines.append(lines[j])
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    if brace_count == 0:
                        break
                    j += 1

                funcs.append({
                    "name": func_name,
                    "file": filepath,
                    "body": ''.join(body_lines).strip()
                })
            return funcs
        except Exception:
            return []

    all_funcs = []
    seen = set()
    for file_path, changed_lines in file_changes.items():
        funcs = extract_function_body(file_path, changed_lines)
        for f in funcs:
            key = f"{f['file']}::{f['name']}"
            if key not in seen:
                seen.add(key)
                all_funcs.append(f)

    return all_funcs

def get_llm_chain():
    llm = ChatOpenAI(temperature=0.3, model_name="gpt-4")
    prompt = ChatPromptTemplate.from_template("""
You are an AI PR reviewer for a PHP codebase using the Yii framework and EMongoDB.

Function Name: {func_name}
File: {file_path}

Function Body:
{func_body}

Related Context:
{extra_context}

Odd Parameter Types:
{odd_param_types}

AI-Inferred Types:
{ai_types}

Chat History:
{chat_history}

Tasks:
1. Is this function validating input properly?
2. Are EMongoDB queries safe and performant?
3. Are there any logic or security issues?
4. If unsure, ask a clear follow-up question starting with 'QUESTION:'.
5. If confident, summarize only issues.

Return your output using the following markdown format. You must include **every** section, even if the value is 'None'. Each section must start with a bullet like `- **Section Name**:` followed by a summary or `None`:
- **Input Validation**: <summary or 'None'>
- **Tenant Safety**: <summary or 'None'>
- **Database Safety**: <summary or 'None'>
- **Logic Issues**: <summary or 'None'>
- **Security Concerns**: <summary or 'None'>

Example output:
- **Input Validation**: Function does not validate `$params['email']`.
- **Tenant Safety**: `tenant()` is called with `$application->tenant_id`, but no check for null.
- **Database Safety**: No checks for `save()` result.
- **Logic Issues**: None
- **Security Concerns**: None
- **Input Validation**: <summary or 'None'>
- **Tenant Safety**: Confirm if tenant ID is passed to tenant() calls. Trace its value and warn if null or missing.
- **Database Safety**: <summary or 'None'>
- **Logic Issues**: <summary or 'None'>
- **Security Concerns**: <summary or 'None'>
""")
    chain = prompt | llm
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return chain, memory

def review_single_function(func, callback):
    global user_input_response
    callback(f"🔍 Reviewing: {func['name']} in {func['file']}")
    callback("📦 Analyzing function body...")

    chain, memory = get_llm_chain()

    try:
        with open(func['file'], 'r', encoding='utf-8') as f:
            full_code = f.read()
    except Exception:
        full_code = ""

    extra = extract_related_context(func_body=func['body'], full_code=full_code)
    extra_context_str = "\n".join(f"{key} =>\n{value}" for key, value in extra.items() if value)

    funcs_all = extract_function_definitions(full_code)
    calls_all = extract_function_calls(full_code)
    all_param_types = resolve_param_types(funcs_all, calls_all)
    odd_params = find_odd_types(all_param_types)
    odd_param_report = "\n".join(f"{k}: {v}" for k, v in odd_params.items())

    expressions_to_check = re.findall(r'(\$\w+(\[[^\]]+\])?(->\w+)?)', func['body'])
    ai_type_results = []
    for match in expressions_to_check:
        expr = match[0].strip()
        if expr:
            callback(f"🧠 Inferring type for {expr}...")
            ai_type = infer_type_ai(expr, context_code=full_code, current_class_name=func['name'])
            ai_type_results.append(f"{expr} => {ai_type}")
    ai_type_summary = "\n".join(ai_type_results)

    inputs = {
        "func_name": func['name'],
        "file_path": func['file'],
        "func_body": func['body'],
        "extra_context": extra_context_str,
        "odd_param_types": odd_param_report,
        "ai_types": ai_type_summary,
        "chat_history": memory.load_memory_variables({})["chat_history"]
    }

    output = chain.invoke(inputs)
    print(output.content)

    if output.content.strip().lower().startswith("question:"):
        question = output.content.strip().split("QUESTION:", 1)[-1].strip()
        callback("USER_INPUT_REQUEST::" + question)
        user_input_response = None
        while user_input_response is None:
            sleep(0.5)
        memory.chat_memory.add_user_message(user_input_response)
        memory.chat_memory.add_ai_message(question)
        output = chain.invoke(inputs)
    if output.content.strip():
        callback(f"❗ AI Feedback: {output.content.strip()}")
    else:
        callback("✅ No issues detected.")

    callback("----------------------------------------")

def run_review_with_callback(repo_path, base_branch, pr_branch, callback):
    funcs = get_changed_functions_with_bodies(base_branch, pr_branch, repo_path)

    if not funcs:
        callback("❌ No changed functions found.")
        return

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(review_single_function, func, callback) for func in funcs]
        concurrent.futures.wait(futures)
