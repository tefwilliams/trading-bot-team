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

    # Load system instructions from file or fallback to passed argument.
    # This prioritizes externalized prompts per the Developer Guide.
    if not system_instruction:
        system_instruction = (
            load_prompt(f"system_{role.lower()}.md")
            or load_prompt(f"system_{role.lower()}.txt")
            or "You are a helpful assistant."
        )

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
