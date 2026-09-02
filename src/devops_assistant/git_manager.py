"""
Git management and repository ingestion module.
"""

import os
import shutil
import tempfile
from typing import Tuple, Optional
import git
from devops_assistant.config import CommitInfo


class GitManager:
    """Manages cloning, diff extraction, and metadata parsing via GitPython."""

    def __init__(self, target_path: str = ".", repo_url: Optional[str] = None, branch: str = "main", depth: int = 1):
        self.repo_url = repo_url
        self.branch = branch
        self.depth = depth
        self.is_temp = False
        
        if repo_url:
            self.working_dir = tempfile.mkdtemp(prefix="devops_repo_")
            self.is_temp = True
            self.repo = self._clone_repo()
        else:
            self.working_dir = os.path.abspath(target_path)
            try:
                self.repo = git.Repo(self.working_dir, search_parent_directories=True)
            except Exception:
                self.repo = None

    def _clone_repo(self) -> git.Repo:
        """Clones a remote repository to a local temporary directory."""
        try:
            return git.Repo.clone_from(
                self.repo_url,
                self.working_dir,
                branch=self.branch,
                depth=self.depth
            )
        except Exception as e:
            # Fallback if depth or branch fails
            try:
                return git.Repo.clone_from(self.repo_url, self.working_dir)
            except Exception as ex:
                raise RuntimeError(f"Failed to clone repository {self.repo_url}: {ex}") from e

    def get_commit_info(self) -> CommitInfo:
        """Extracts commit hash, author, and message from current repository state."""
        if not self.repo:
            return CommitInfo(
                commit_hash="unversioned",
                author="Local Execution",
                message="Analysis of non-git working directory",
                branch=self.branch
            )
        try:
            head = self.repo.head.commit
            branch_name = self.repo.active_branch.name if not self.repo.head.is_detached else "detached"
            return CommitInfo(
                commit_hash=head.hexsha[:8],
                author=f"{head.author.name} <{head.author.email}>",
                message=head.message.strip().split("\n")[0],
                branch=branch_name
            )
        except Exception:
            return CommitInfo(
                commit_hash="head",
                author="Unknown",
                message="Git repository inspection",
                branch=self.branch
            )

    def get_diff(self, base_ref: str = "HEAD~1") -> str:
        """Returns the git diff output string for code review."""
        if not self.repo:
            return ""
        try:
            return self.repo.git.diff(base_ref)
        except Exception:
            try:
                return self.repo.git.diff("HEAD")
            except Exception:
                return ""

    def cleanup(self):
        """Removes temporary directory if repo was cloned remotely."""
        if self.is_temp and os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir, ignore_errors=True)
