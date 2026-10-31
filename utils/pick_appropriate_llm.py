from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def pick_llm(task_level:Literal['Low','Intermediate','High']) -> str:
	"""
	The fn returns the appropriate LLM based on the task level provided by the user. The task level can be one of the following: 'Low', 'Intermediate', or 'High'.
	"""
	if task_level == 'Low':
		model = ChatGoogleGenerativeAI(model = 'gemini-3-flash-preview')
		return model
	elif task_level == 'Intermediate':
		model = ChatGoogleGenerativeAI(model = 'gemini-3.5-flash-lite')
		return model
	elif task_level == 'High':
		model = ChatGoogleGenerativeAI(model = 'gemini-3.8-live')
		return model
	else:
		raise ValueError("Invalid task level. Please choose from 'Low', 'Intermediate', or 'High'.")


if __name__ == "__main__":
	# Example usage
	task_level = 'Low'
	llm = pick_llm(task_level)
	query = "What is the capital of France?"
	print(llm.invoke(query))  
	