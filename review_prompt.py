from langchain.prompts import PromptTemplate

review_prompt = PromptTemplate(
    input_variables=["func_body", "combined", "chat_history"],
    template="""
You are an expert PHP (Yii + EMongoDB) reviewer.

Function:
{func_body}

Static Checks and Type Inference:
{combined}

{chat_history}

Instructions:
- Be **concise and direct**
- List only **actionable issues** or red flags
- Use **short bullet points** and avoid unnecessary explanation
- If asking clarification, use:
  QUESTION: <your question>
"""
)
