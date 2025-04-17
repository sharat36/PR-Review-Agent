from langchain_openai import ChatOpenAI
from infer_type_ai import infer_type

def validate(func_body: str, context_code: str, full_file_code: str) -> str:
    prompt = f"""
You are a reviewer for MongoDB/Yii PHP applications.

Check the following function for **database interaction safety**:

Function:
{func_body}

Context:
{context_code}

Consider:
- Use of `save()`, `update()`, or `find()` without checking result
- Improper criteria queries
- Lack of error handling around DB ops
- Use of deprecated EMongoDocument methods

Return your result in this format:
- **Database Safety**: <summary or 'None'>
"""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        response = llm.invoke(prompt).content.strip()
    except Exception as e:
        response = f"- **Database Safety**: ❌ AI Error: {e}"

    try:
        types = infer_type(func_body, context_code, full_file_code)
        flags = []
        if 'save()' in func_body and 'if' not in func_body:
            flags.append("No `save()` result check found.")
        for var, t in types.items():
            if 'criteria' in var and 'null' in t:
                flags.append(f"`{var}` may be null before DB operation.")
        if flags:
            response += "\n- **Type-Based Checks**:\n" + "\n".join(f"  - {f}" for f in flags)
    except Exception as e:
        response += f"\n- **Type-Based Checks**: ❌ Error: {e}"

    return response
