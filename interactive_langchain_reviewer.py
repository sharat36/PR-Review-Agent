import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

from context_extractor import extract_related_context
from validator_agent import suggest_validators
from validators import (
    input_validation,
    tenant_validation,
    security_validation,
    logic_validation,
    db_validation,
)
from infer_type_ai import infer_type
from review_prompt import review_prompt

from dotenv import load_dotenv
load_dotenv()

user_input_response = None

def set_user_input(answer: str):
    global user_input_response
    user_input_response = answer


def get_changed_functions(repo_path, base_branch, pr_branch):
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
                file_changes[current_file].add(int(match.group(1)))

    def extract_function_body(filepath, line_numbers):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            funcs = []
            for idx in line_numbers:
                i = idx - 1
                while i >= 0 and not re.search(r'function\s+\w+\s*\(', lines[i]):
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
                    "body": ''.join(body_lines).strip(),
                    "full_file_code": ''.join(lines)
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



def review_single_function(func, full_code, callback):
    func_key = f"{func['file'].strip()}::{func['name'].strip()}"
    print(f"🔍 Reviewing function: {func_key}")
    callback(f"🔍 Reviewing: {func['name']} in {func['file']}")

    start_time = time.time()

    try:
        suggested = suggest_validators(func['body'], full_code)
        print(f"✅ Suggested: {suggested} for {func_key} completed in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"❌ Validator agent failed: {e}")
        callback(f"❌ Validator agent failed: {e}")
        suggested = []

    if not suggested:
        callback("ℹ️ No validators suggested.")
        return

    callback(f"STREAM::{func_key}::Selected validators: {', '.join(suggested)}")
    
    start_time1 = time.time()
    context_code = extract_related_context(func['body'], func['full_file_code'], func['file'])
    type_info = infer_type(func['body'], context_code, func['full_file_code'])
    print(f"✅ Type inference complete for {func_key}. completed in {time.time() - start_time1:.2f}s")

    type_summary = "\n".join(
        f"- {var}: {', '.join(f'{t} ({c})' for t, c in types.items())}" if isinstance(types, dict) else f"- {var}: {types}"
        for var, types in type_info.items()
    )

    validator_map = {
        "input_validation": input_validation.validate,
        "tenant_validation": tenant_validation.validate,
        "security_validation": security_validation.validate,
        "logic_validation": logic_validation.validate,
        "db_validation": db_validation.validate,
    }

    results = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(validator_map[name], func['body'], context_code, func['full_file_code']): name
            for name in suggested if name in validator_map
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                start = time()
                result = future.result(timeout=20)
                duration = time() - start
                if result and result.strip().lower() != "none":
                    results.append(result)
                    print(f"✅ {name} validator passed for {func_key} in {duration:.2f}s.")
                else:
                    print(f"ℹ️ {name} validator returned 'none' for {func_key} in {duration:.2f}s.")
            except Exception as e:
                results.append(f"- **{name}**: ❌ Error: {str(e)}")

    combined = "\n".join(results) + "\n\nInferred Types:\n" + type_summary

    changed_lines = func.get("changed_lines", [])
    func_lines = func['body'].splitlines()
    changed_code = [
        func_lines[ln - 1].strip()
        for ln in changed_lines
        if 0 < ln <= len(func_lines)
    ]

    memory = ConversationBufferMemory(memory_key="chat_history", input_key="func_body")
    llm = ChatOpenAI(model_name="gpt-4", temperature=0)
    chain = LLMChain(prompt=review_prompt, llm=llm, memory=memory)

    try:
        output = chain.invoke({
            "func_body": func['body'],
            "combined": combined,
            "chat_history": "",
            "changed_lines": "\n".join(changed_code)
        })
    except Exception as e:
        callback(f"❌ AI Review failed: {str(e)}")
        return

    response_text = output.get("text") or output.get("output") or ""
    question_line = next((line for line in response_text.splitlines() if line.lower().startswith("question:")), None)

    if not question_line:
        safe_response = response_text.strip().replace("\n", "\\n")
        callback(f"STREAM::{func_key}::{safe_response}✅ Done")
        return

    callback(f"USER_INPUT_REQUEST::{func_key}::{question_line.split(':', 1)[-1].strip()}")
    user_input_response = None
    while user_input_response is None:
        time.sleep(0.5)

    memory.chat_memory.add_user_message(user_input_response)
    memory.chat_memory.add_ai_message(question_line)

    final_output = chain.invoke({
        "func_body": func['body'],
        "combined": combined,
        "chat_history": memory.buffer,
        "changed_lines": "\n".join(changed_code)
    })

    final_response = final_output.get("text") or final_output.get("output") or ""
    safe_final = final_response.strip().replace("\n", "\\n")
    callback(f"STREAM::{func_key}::{safe_final}✅ Done")
    print(f"✅ Total review for {func_key} completed in {time.time() - start_time:.2f}s")

def run_review_with_callback(repo_path, base_branch, pr_branch, callback):
    callback(f"📦 Repo: {repo_path}")
    start_time = time.time()
    changed = get_changed_functions(repo_path, base_branch, pr_branch)
    print(f"✅ fetched changed functions completed in {time.time() - start_time:.2f}s")

    if not changed:
        callback("✅ No changed functions found.")
        return

    callback(f"🔎 {len(changed)} changed function(s) found.")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(review_single_function, func, func['full_file_code'], callback)
            for func in changed
        ]
        for future in as_completed(futures):
            future.result()
