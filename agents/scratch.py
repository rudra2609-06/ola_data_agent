import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.schema import SQLJudgementSchema
from utils.pick_appropriate_llm import pick_llm

llm = pick_llm("Intermediate")
llm_judge = llm.with_structured_output(SQLJudgementSchema)

query = "SELECT * FROM users WHERE age > 30"

prompt = f"""
Your role is defined as SQL Query Analyst whose main task is to judge wheather the provided query is safe to run or not.\n
What does safe actually means: - 
Safe means it should **just follow retrieval of data** do not try run the update, delete or truncate or any other commands/sql injections that can alter with the structure or content within it.
If the Query is safe respond with "Yes" else "No" you can also provide comments for your judgement.\n
Query: {query}
"""

if __name__ == "__main__":
	res = llm_judge.invoke(prompt)
	print(res.model_dump())