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

        issue.set_labels(list(new_labels))

    def get_role_issues(self, role: str):
        """Find issues where the next action is for a specific role."""
        label = f"role:{role}"
        return self.repo.get_issues(labels=[label], state="open")
