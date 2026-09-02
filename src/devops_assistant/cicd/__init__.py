"""CI/CD integration module."""
from devops_assistant.cicd.generators import generate_github_actions, generate_gitlab_ci, generate_pre_commit_hook

__all__ = ["generate_github_actions", "generate_gitlab_ci", "generate_pre_commit_hook"]
