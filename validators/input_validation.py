from langchain_openai import ChatOpenAI
from infer_type_ai import infer_type

def validate(func_body: str, context_code: str, full_file_code: str) -> str:
    prompt = f"""
You are an expert PHP reviewer.

Check the following function for **missing or weak input validation**.

Function:
{func_body}

Context:
{context_code}

Look for:
- Use of `$params` or `$post_data` without checks
- Accessing user input without type or null validation
- Assumptions on object properties or structure

Respond in markdown:
- **Input Validation**: <summary or 'None'>
"""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        response = llm.invoke(prompt).content.strip()
    except Exception as e:
        response = f"- **Input Validation**: ❌ AI Error: {e}"

    # infer_type_ai supplement
    try:
        type_info = infer_type(func_body, context_code, full_file_code)
        issues = []
        for var, types in type_info.items():
            if 'null' in types:
                issues.append(f"`{var}` may be null.")
            if 'unknown' in types:
                issues.append(f"`{var}` has unknown type.")
        if issues:
            response += "\n- **Type-Based Checks**:\n" + "\n".join(f"  - {i}" for i in issues)
    except Exception as e:
        response += f"\n- **Type-Based Checks**: ❌ Error: {e}"

    return response
