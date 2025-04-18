from langchain.prompts import PromptTemplate

review_prompt = PromptTemplate(
    input_variables=["func_body", "combined", "chat_history", "changed_lines"],
    template="""
You are an expert PHP (Yii + EMongoDB) reviewer.

Function:
{func_body}

Static Checks and Type Inference:
{combined}

{chat_history}

Changed Code:
{changed_lines}

Instructions:
- Only analyze and comment on the changed lines.
- Ignore unchanged code unless needed for context.
- Be concise and strict: only mention real issues in the lines provided.
"""
)
