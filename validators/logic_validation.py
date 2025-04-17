from langchain_openai import ChatOpenAI
from infer_type_ai import infer_type

def validate(func_body: str, context_code: str, full_file_code: str) -> str:
    prompt = f"""
You are a PHP code logic reviewer.

Check this function for **unreachable logic, faulty conditions, or bad assumptions**.

Function:
{func_body}

Context:
{context_code}

Mention:
- Misused null coalescing
- Unchecked branches
- Logic based on unsafe assumptions

Return:
- **Logic Validation**: <summary or 'None'>
"""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        response = llm.invoke(prompt).content.strip()
    except Exception as e:
        response = f"- **Logic Validation**: ❌ AI Error: {e}"

    try:
        types = infer_type(func_body, context_code, full_file_code)
        issues = []
        for var, t in types.items():
            keys = t.keys()
            if 'object' in keys and 'string' in keys:
                issues.append(f"`{var}` used as both object and string.")
            if 'null' in keys and 'bool' in keys:
                issues.append(f"`{var}` used in boolean condition but may be null.")
        if issues:
            response += "\n- **Type-Based Checks**:\n" + "\n".join(f"  - {i}" for i in issues)
    except Exception as e:
        response += f"\n- **Type-Based Checks**: ❌ Error: {e}"

    return response
