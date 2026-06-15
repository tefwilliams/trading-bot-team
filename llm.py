import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Per-role primary model. All are on the Google AI Studio free tier. Pro is reserved for the single
# hardest reasoning task — judging spec soundness — and nothing else:
# - Strategy Reviewer uses `gemini-2.5-pro` for spec soundness. It fires once per research iteration
#   (before any code), so its ~5 RPM / 50-100 RPD limit is comfortable; it degrades to `gemini-3-flash`
#   on error/throttle. NB: the 3.x Pro models are paid.
# - Researcher, Engineer, and Performance Reviewer use `gemini-3-flash` (strong, high quota).
# - Code Reviewer uses `gemini-3.1-flash-lite` for the mechanical implementation checks.
DEFAULT_MODEL = "gemini-3.1-flash-lite"
ROLE_MODELS = {
    "researcher": "gemini-3-flash",
    "strategy_reviewer": "gemini-2.5-pro",
    "engineer": "gemini-3-flash",
    "code_reviewer": "gemini-3.1-flash-lite",
    "performance_reviewer": "gemini-3-flash",
}

# Per-role fallback model, used only where the primary is rate-limited enough that a graceful
# *degrade* makes sense. Only the Strategy Reviewer qualifies (its free Pro model throttles easily),
# so it degrades to the high-quota `gemini-3-flash`. Other roles rely on the orchestrator's retry loop.
ROLE_FALLBACKS = {
    "strategy_reviewer": "gemini-3-flash",
}

# Per-role sampling temperature. Code generation and critical review want low
# variance; only the Researcher benefits from creative divergence.
ROLE_TEMPS = {
    "researcher": 0.7,
    "strategy_reviewer": 0.0,
    "engineer": 0.3,
    "code_reviewer": 0.0,
    "performance_reviewer": 0.0,
}


def load_prompt(filename: str) -> str:
    """Loads a prompt template from the /prompts/ directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "prompts", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _build_chat(model_name: str, temp: float, system_instruction: str, structured_output):
    """Builds a chat model, optionally bound to a structured-output schema."""
    chat = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temp,
        model_kwargs={"system_instruction": system_instruction},
    )
    if structured_output is not None:
        return chat.with_structured_output(structured_output)
    return chat


def get_llm(role: str, system_instruction: str = None, structured_output=None):
    """
    Returns the LLM for the given agent role (see docs/roles.md). Model and
    temperature are selected per role, with sensible defaults for unlisted roles.

    If `structured_output` (a Pydantic model / schema) is given, the model is bound
    to it so `.invoke()` returns a validated object instead of a message.

    If the role has a ROLE_FALLBACKS entry, the returned runnable degrades to that
    model on any error (e.g. a rate-limited Pro model dropping to gemini-3-flash).
    Roles without an entry rely on the orchestrator's retry loop.
    """
    role_key = role.lower()
    model_name = ROLE_MODELS.get(role_key, DEFAULT_MODEL)
    temp = ROLE_TEMPS.get(role_key, 0.0)

    # Load system instructions from file or fallback to passed argument.
    # This prioritizes externalized prompts per the Developer Guide.
    if not system_instruction:
        system_instruction = (
            load_prompt(f"system_{role_key}.md")
            or load_prompt(f"system_{role_key}.txt")
            or "You are a helpful assistant."
        )

    primary = _build_chat(model_name, temp, system_instruction, structured_output)

    fallback_model = ROLE_FALLBACKS.get(role_key)
    if fallback_model and fallback_model != model_name:
        fallback = _build_chat(fallback_model, temp, system_instruction, structured_output)
        return primary.with_fallbacks([fallback])

    return primary
