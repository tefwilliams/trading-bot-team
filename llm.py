import os
from typing import Literal
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def get_llm(role: str):
    """
    Returns the appropriate LLM based on the agent role defined in docs/roles.md.
    Now consolidated to Gemini for all roles.
    """
    
    if role.lower() in ["researcher", "engineer"]:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-thinking-exp-01-21",
            temperature=0.7
        )
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0
    )
