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

This project is intended to be picked up from any machine with Claude Code or a Gemini-equivalent CLI installed. The `docs/` folder is the source of truth for design context — point your assistant at it when resuming.
