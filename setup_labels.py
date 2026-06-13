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
        # Statuses (Mapping to LangGraph nodes)
        "status:researcher": "FBCA04",
        "status:engineer": "1D76DB",
        "status:reviewer": "D4C5F9",
        "status:risk_manager": "E11D21",
        "status:backtester": "D4C5F9",
        "status:historian": "006B75",
        "status:manager": "0E8A16",
        "status:product_manager": "6B4FAD",
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
