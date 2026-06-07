import os
from github import Github
from dotenv import load_dotenv

load_dotenv()


class GitHubManager:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.repo_name = os.getenv("GITHUB_REPO")
        self.g = Github(self.token)
        self.repo = self.g.get_repo(self.repo_name)

    def get_issue(self, issue_number: int):
        return self.repo.get_issue(number=issue_number)

    def post_comment(self, issue_number: int, body: str):
        issue = self.get_issue(issue_number)
        return issue.create_comment(body)

    def close_issue(self, issue_number: int):
        issue = self.get_issue(issue_number)
        issue.edit(state="closed")

    def update_labels(
        self, issue_number: int, add: list[str] = None, remove: list[str] = None
    ):
        issue = self.get_issue(issue_number)
        current_labels = [l.name for l in issue.get_labels()]

        new_labels = set(current_labels)
        if add:
            new_labels.update(add)
        if remove:
            for r in remove:
                new_labels.discard(r)

        issue.set_labels(*new_labels)

    def transition_role(self, issue_number: int, new_role: str, new_stage: str):
        """Standardized way to move a ticket between agents and stages."""
        issue = self.get_issue(issue_number)
        current_labels = [l.name for l in issue.get_labels()]

        # Filter out any existing role or stage labels
        cleaned_labels = [
            l for l in current_labels if not l.startswith(("role:", "stage:"))
        ]

        cleaned_labels.append(f"role:{new_role}")
        cleaned_labels.append(new_stage)
        issue.set_labels(*cleaned_labels)

    def get_role_issues(self, role: str):
        """Find issues where the next action is for a specific role."""
        label = f"role:{role}"
        return self.repo.get_issues(labels=[label], state="open")

    def create_issue(self, title: str, body: str, labels: list[str]):
        return self.repo.create_issue(title=title, body=body, labels=labels)
