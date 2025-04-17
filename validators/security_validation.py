from langchain_openai import ChatOpenAI
from infer_type_ai import infer_type

def validate(func_body: str, context_code: str, full_file_code: str) -> str:
    prompt = f"""
You are reviewing PHP/Yii code for **security risks**.

Function:
{func_body}

Context:
{context_code}

Flag:
- Use of raw `$params`, `$_POST` in queries or responses
- Logging/printing sensitive data
- Exposure via debug_backtrace or stack traces

Respond as:
- **Security Validation**: <summary or 'None'>
"""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        response = llm.invoke(prompt).content.strip()
    except Exception as e:
        response = f"- **Security Validation**: ❌ AI Error: {e}"

    try:
        types = infer_type(func_body, context_code, full_file_code)
        alerts = []
        for var, t in types.items():
            if 'string' in t and 'unknown' in t:
                alerts.append(f"`{var}` could contain unsafe user input.")
        if 'debug_backtrace' in func_body or 'print_r' in func_body:
            alerts.append("Sensitive debug function used.")
        if alerts:
            response += "\n- **Type-Based Checks**:\n" + "\n".join(f"  - {a}" for a in alerts)
    except Exception as e:
        response += f"\n- **Type-Based Checks**: ❌ Error: {e}"

    return response
