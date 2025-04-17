from langchain.prompts import PromptTemplate

review_prompt = PromptTemplate(
    input_variables=["func_body", "combined", "chat_history"],
    template="""
You are an expert reviewer for PHP (Yii + EMongoDB).

Function:
{func_body}

Validation output from static checks and type inference:
{combined}

{chat_history}

Instructions:
- Use the above "Inferred Types" to understand variables and object structures.
- Only ask a QUESTION if something is clearly missing.
- Prefer to summarize all risks and edge cases.

If asking for clarification, use:
QUESTION: <your question>
"""
)