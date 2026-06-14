import os
from typing import Literal
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def load_prompt(filename: str) -> str:
    """Loads a prompt template from the /prompts/ directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "prompts", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def get_llm(role: str, system_instruction: str = None):
    """
    Returns the appropriate LLM based on the agent role defined in docs/roles.md.
    Now consolidated to Gemini for all roles.
    """
    # 3.1 is the latest version - using it as the team standard for cost/performance.
    model_name = "gemini-3.1-flash-lite"

    # Default system instructions if none provided
    if not system_instruction:
        instructions = {
            "researcher": "You are a world-class Quantitative Researcher. Focus on falsifiable hypotheses and clear mathematical rules.",
            "engineer": "You are a Senior Software Engineer. Write clean, modular Python code following the JSON results contract.",
            "reviewer": "You are a strict QA Reviewer. Your only job is to find flaws, missing details, or poor formatting in IT tickets.",
            "risk_manager": "You are a Professional Risk Manager. Evaluate strategies for safety, position sizing, and ruin prevention.",
        }
        system_instruction = instructions.get(
            role.lower(), "You are a helpful assistant."
        )

        # Try to load a specialized system instruction from file if it exists
        file_instruction = load_prompt(f"system_{role.lower()}.txt")
        if file_instruction:
            system_instruction = file_instruction

    # Temperature settings based on role
    if role.lower() in ["researcher", "engineer"]:
        temp = 0.7
    else:
        temp = 0.0

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temp,
        model_kwargs={"system_instruction": system_instruction},
    )
