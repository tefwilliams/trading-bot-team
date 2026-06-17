import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Per-role primary model. All are on the Google AI Studio free tier. As of April 2026 the Pro series
# (incl. `gemini-2.5-pro`) was removed from the free tier, so the strongest free model is now
# `gemini-3.5-flash`. It runs every role that benefits from reasoning:
# - Strategy Reviewer (the single hardest reasoning task — judging spec soundness), Researcher,
#   Engineer, and Performance Reviewer all use `gemini-3.5-flash`.
# - Code Reviewer uses the cheaper `gemini-3.1-flash-lite` for mechanical implementation checks. This
#   also keeps it on a *separate* per-model rate-limit bucket (~1,500 RPD) from the flash roles, so the
#   mechanical-review churn doesn't eat into the reasoning roles' quota.
DEFAULT_MODEL = "gemini-3.1-flash-lite"
ROLE_MODELS = {
    "researcher": "gemini-3.5-flash",
    "strategy_reviewer": "gemini-3.5-flash",
    "engineer": "gemini-3.5-flash",
    "code_reviewer": "gemini-3.1-flash-lite",
    "performance_reviewer": "gemini-3.5-flash",
}

# Per-role fallback model, used only where a graceful *degrade* to a different model (and so a
# separate rate-limit bucket) is worthwhile. The Strategy Reviewer is the most reasoning-sensitive
# role, so it degrades to `gemini-2.5-flash` if `gemini-3.5-flash` is throttled. Other roles rely on
# the orchestrator's retry loop.
ROLE_FALLBACKS = {
    "strategy_reviewer": "gemini-2.5-flash",
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
    model on any error (e.g. a throttled gemini-3.5-flash dropping to gemini-2.5-flash).
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
