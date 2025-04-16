# langchain_pr_reviewer.py
import os
import re
from dotenv import load_dotenv
load_dotenv()

import subprocess
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from context_extractor import extract_related_context
from param_type_analyzer import extract_function_definitions, extract_function_calls, resolve_param_types, find_odd_types
from infer_type_ai import infer_type_ai


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
4. Only respond if there is an issue or risk detected. If everything looks good, return nothing.
""")
    chain = prompt | llm
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return chain, memory

def run_interactive_review():
    repo_path = '/data/live/'#input("📁 Repo path: ")
    base_branch = 'release/8.4'#input("🌿 Base branch: ")
    pr_branch = 'feature/8.4-pr-test'#input("🌿 PR branch: ")

    funcs = get_changed_functions_with_bodies(base_branch, pr_branch, repo_path)

    if not funcs:
        print("❌ No changed functions found.")
        return

    for func in funcs:
        print(f"\n🔍 Reviewing: {func['name']}\n📄 File: {func['file']}")
        print("📦 Function body preview:\n" + func["body"][:500] + "...\n")

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
        print(odd_param_report)

        expressions_to_check = re.findall(r'(\$\w+(\[[^\]]+\])?(->\w+)?)', func['body'])
        ai_type_results = []
        for match in expressions_to_check:
            expr = match[0].strip()
            if expr:
                ai_type = infer_type_ai(expr, context_code=full_code)
                ai_type_results.append(f"{expr} => {ai_type}")
        ai_type_summary = "\n".join(ai_type_results)

        while True:
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
            print(f"\n🤖 AI: {output.content}\n")

            if any(k in output.content.lower() for k in ["final suggestion", "recommendation", "review summary"]):
                break

            user_input = input("🧑 You (optional reply): ")
            if not user_input.strip():
                break
            memory.chat_memory.add_user_message(user_input)

if __name__ == "__main__":
    run_interactive_review()