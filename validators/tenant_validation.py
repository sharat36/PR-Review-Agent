from langchain_openai import ChatOpenAI
from infer_type_ai import infer_type

def validate(func_body: str, context_code: str, full_file_code: str) -> str:
    prompt = f"""
You're reviewing a multi-tenant Yii/MongoDB app.

Function:
{func_body}

Context:
{context_code}

Check:
- `tenant()` calls without a tenant ID
- Use of `$application->tenant_id` or `$params['tenant_id']`
- Risk of unscoped data access

Format:
- **Tenant Validation**: <summary or 'None'>
"""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        response = llm.invoke(prompt).content.strip()
    except Exception as e:
        response = f"- **Tenant Validation**: ❌ AI Error: {e}"

    try:
        types = infer_type(func_body, context_code, full_file_code)
        findings = []
        for var, t in types.items():
            if 'tenant' in var and 'null' in t:
                findings.append(f"`{var}` may be null or undefined.")
        if '->tenant()' in func_body:
            findings.append("`tenant()` called without ID.")
        if findings:
            response += "\n- **Type-Based Checks**:\n" + "\n".join(f"  - {f}" for f in findings)
    except Exception as e:
        response += f"\n- **Type-Based Checks**: ❌ Error: {e}"

    return response
