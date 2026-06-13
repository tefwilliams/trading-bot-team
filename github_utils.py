import os
import re
from github import Github, GithubException
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

    def set_status(self, issue_number: int, new_status: str):
        """Standardized way to move a ticket to a new status/node."""
        issue = self.get_issue(issue_number)
        current_labels = [l.name for l in issue.get_labels()]

        # Filter out any existing status labels
        cleaned_labels = [l for l in current_labels if not l.startswith("status:")]

        cleaned_labels.append(f"status:{new_status}")
        issue.set_labels(*cleaned_labels)

    def ensure_branch(self, branch_name: str, base_branch: str = "main"):
        """Creates a branch if it doesn't exist."""
        try:
            self.repo.get_branch(branch_name)
        except GithubException:
            base = self.repo.get_branch(base_branch)
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}", sha=base.commit.sha
            )

    def create_or_update_file(self, path: str, message: str, content: str, branch: str):
        """Updates a file if it exists, otherwise creates it."""
        try:
            file = self.repo.get_contents(path, ref=branch)
            self.repo.update_file(path, message, content, file.sha, branch=branch)
        except GithubException:
            self.repo.create_file(path, message, content, branch=branch)

    def create_pull_request(self, title: str, body: str, head: str, base: str = "main"):
        """Creates a PR or returns an existing one."""
        try:
            return self.repo.create_pull(title=title, body=body, head=head, base=base)
        except GithubException as e:
            if e.status == 422:  # PR already exists
                pulls = self.repo.get_pulls(
                    state="open", head=f"{self.repo.owner.login}:{head}"
                )
                return pulls[0]
            raise e

    def extract_code(self, text: str):
        """Extracts the first python code block found in the text."""
        pattern = r"```(?:python)?\s*(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else text.strip()

    def get_status_issues(self, status: str):
        """Find issues where the next action matches a specific status/node."""
        label = f"status:{status}"
        return self.repo.get_issues(labels=[label], state="open")

    def create_issue(self, title: str, body: str, labels: list[str]):
        return self.repo.create_issue(title=title, body=body, labels=labels)

    def get_related_pr(self, issue_number: int):
        """Finds an open PR associated with the strategy issue branch."""
        branch_name = f"strat/issue-{issue_number}"
        # head expects 'owner:branch'
        pulls = self.repo.get_pulls(
            state="open", head=f"{self.repo.owner.login}:{branch_name}"
        )
        return pulls[0] if pulls.totalCount > 0 else None

    def get_pr_context(self, pr_number: int):
        """Gathers diff and review comments from a PR."""
        pr = self.repo.get_pull(pr_number)
        files = pr.get_files()
        diff = ""
        for f in files:
            diff += f"File: {f.filename}\n{f.patch}\n"

        # PR Review comments are specifically on lines of code
        reviews = pr.get_review_comments()
        review_text = "\n".join(
            [f"{r.user.login} (on {r.path}): {r.body}" for r in reviews]
        )

        return diff, review_text

    def get_latest_code_block(self, issue_number: int):
        """Extracts the Python code from the PR branch if it exists, else from comments."""
        # 1. Try to fetch from the strategy branch first (where the PR code lives)
        branch_name = f"strat/issue-{issue_number}"
        file_path = f"strategies/strategy_{issue_number}.py"
        try:
            content = self.repo.get_contents(file_path, ref=branch_name)
            return content.decoded_content.decode("utf-8")
        except GithubException:
            pass

        # 2. Fallback to comments if branch/file doesn't exist
        issue = self.get_issue(issue_number)
        comments = list(issue.get_comments())
        for comment in reversed(comments):
            if "```python" in comment.body:
                return self.extract_code(comment.body)
        if "```python" in issue.body:
            return self.extract_code(issue.body)
        return None
