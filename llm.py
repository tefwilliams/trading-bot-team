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

    # Researchers and Engineers get the more creative model to help with ideation and problem-solving
    if role.lower() in ["researcher", "engineer"]:
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=0.7,  # Thinking models often benefit from slight temperature
        )

    # Reviewers get a more stable model to ensure consistent feedback quality
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        temperature=0,
        system_instruction="You are a strict QA Reviewer. Your only job is to find flaws, missing details, or poor formatting in IT tickets.",
    )
