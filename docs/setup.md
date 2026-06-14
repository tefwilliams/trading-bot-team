# Setup

## Per-machine setup

1. Clone the repo:
```
   git clone git@github.com:tefwilliams/trading-bot-team.git
   cd trading-bot-team
```

2. Create a virtualenv and install deps:
```
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
```

3. Create a `.env` file (NOT committed) with:
```
   ANTHROPIC_API_KEY=...
   GOOGLE_API_KEY=...
   GITHUB_TOKEN=...
```

   - Anthropic key: https://console.anthropic.com
   - Google AI Studio key: https://aistudio.google.com
   - GitHub PAT (fine-grained, `repo` scope on this repo only): https://github.com/settings/tokens

4. Verify GitHub access:
```
   gh auth status
```

## Working with Claude Code or Gemini

This project uses "Agent-Centric Development." When using an AI tool (Gemini, Claude, Cursor) to modify this repository:

1. **Context Loading**: Ensure your AI assistant reads `DEVELOPER_GUIDE.md` and the `docs/` folder before suggesting changes.
2. **Verification Prompt**: Explicitly ask the AI: *"Review your proposed changes against the invariants in `DEVELOPER_GUIDE.md`. Does this maintain the Technical Interface Contract?"*
3.  **Strict Mode**: If the AI is generating an agent prompt (e.g., in `engineer.py`), ensure it includes a "Self-Reflection Mandate" in the prompt text to force the agent to double-check its own output.

The `DEVELOPER_GUIDE.md` is the source of truth for technical interaction rules; the `docs/` folder provides the architectural and business context.
