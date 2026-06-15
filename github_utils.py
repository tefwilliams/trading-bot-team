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

    def update_pr_body(self, pr_number: int, body: str):
        """Replaces a PR's description (used by the Engineer to keep it current)."""
        self.repo.get_pull(pr_number).edit(body=body)

    def close_pr(self, pr_number: int):
        """Closes a PR without merging (used when a strategy is abandoned)."""
        self.repo.get_pull(pr_number).edit(state="closed")

    def get_issue_context(self, issue):
        """The issue thread only — the strategy-level channel (spec & reviews).
        Used by the Researcher and Strategy Reviewer, who work at the strategy level."""
        comments = list(issue.get_comments())
        thread = "\n\n".join(f"--- {c.user.login} ---\n{c.body}" for c in comments)
        return f"=== ISSUE #{issue.number} THREAD (strategy spec & reviews) ===\n{thread}"

    def get_pr_context(self, pr_number: int):
        """The PR — the implementation-level channel: description, diff, conversation
        comments (backtest reports & code review) and any inline review comments.
        Used by the Performance Reviewer (PR-only)."""
        pr = self.repo.get_pull(pr_number)

        diff = "".join(f"File: {f.filename}\n{f.patch}\n" for f in pr.get_files())

        conversation = "\n\n".join(
            f"--- {c.user.login} ---\n{c.body}" for c in self.get_issue(pr_number).get_comments()
        )

        inline = "\n".join(
            f"{r.user.login} (on {r.path}): {r.body}" for r in pr.get_review_comments()
        )

        parts = [
            f"=== PR #{pr_number} DESCRIPTION ===\n{pr.body or ''}",
            f"=== PR #{pr_number} CONVERSATION (backtest reports & code review) ===\n{conversation}",
            f"=== PR #{pr_number} DIFF ===\n{diff}",
        ]
        if inline.strip():
            parts.append(f"=== PR #{pr_number} INLINE REVIEW COMMENTS ===\n{inline}")
        return "\n\n".join(parts)

    def get_full_context(self, issue):
        """Both channels — issue thread + PR (if one exists). Returns (text, pr) with
        pr None pre-implementation. Used by the Engineer and Code Reviewer, who must see
        the spec AND the implementation-side feedback."""
        parts = [self.get_issue_context(issue)]
        pr = self.get_related_pr(issue.number)
        if pr:
            parts.append(self.get_pr_context(pr.number))
        return "\n\n".join(parts), pr

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
