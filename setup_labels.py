import os
from github import Github, GithubException
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
        "role:product_manager": "6B4FAD",
        # Stages
        "stage:proposal": "E99695",
        "stage:approved-spec": "C2E0C6",
        "stage:ideation": "5319E7",
        "stage:implementation": "BFDADC",
        "stage:final-review": "0052CC",
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
        except GithubException as e:
            if e.status == 422:
                print(f"Label {name} already exists.")
            else:
                print(f"Error creating {name}: {e.data.get('message')}")


if __name__ == "__main__":
    setup_labels()
