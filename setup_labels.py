import os
from github import Github
from dotenv import load_dotenv

load_dotenv()


def setup_labels():
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO")  # e.g., "username/trading-bot-team"

    if not token or not repo_name:
        print("Please ensure GITHUB_TOKEN and GITHUB_REPO are set in .env")
        return

    g = Github(token)
    repo = g.get_repo(repo_name)

    labels = {
        # Roles
        "role:researcher": "FBCA04",
        "role:engineer": "1D76DB",
        "role:reviewer": "D4C5F9",
        "role:risk_manager": "E11D21",
        "role:manager": "006B75",
        # Stages
        "stage:proposal": "E99695",
        "stage:approved-spec": "C2E0C6",
        "stage:implementation": "BFDADC",
        "stage:review": "FEF2C0",
        "stage:backtest": "D4C5F9",
        "stage:done": "0E8A16",
        "stage:rejected": "B60205",
        # Types
        "type:strategy": "5319E7",
        "type:bug": "D93F0B",
        "type:infra": "0052CC",
    }

    for name, color in labels.items():
        try:
            repo.create_label(name, color)
            print(f"Created label: {name}")
        except:
            print(f"Label {name} already exists or error occurred.")


if __name__ == "__main__":
    setup_labels()
