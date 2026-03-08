"""
infra/github.py — GitHub API helpers.

Used to post @openreview comments on PR submissions.
"""

from __future__ import annotations

import re

import httpx


class GitHubError(Exception):
    """Raised when a GitHub API call fails."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


async def post_openreview_comment(pr_url: str, github_token: str) -> None:
    """
    Post `@openreview` as a comment on the given GitHub PR.

    Parses the PR URL to extract owner, repo, and PR number, then calls
    the GitHub Issues Comments API. No-ops immediately if github_token is empty.

    Raises:
        ValueError: if pr_url is not a valid GitHub PR URL
        GitHubError: if the GitHub API returns a non-2xx response
    """
    if not github_token:
        return

    m = _PR_URL_RE.match(pr_url)
    if not m:
        raise ValueError(f"Not a valid GitHub PR URL: {pr_url!r}")

    owner = m.group("owner")
    repo = m.group("repo")
    number = m.group("number")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers, json={"body": "@openreview"})

    if response.status_code not in (200, 201):
        raise GitHubError(
            response.status_code,
            f"GitHub API error {response.status_code}: {response.text[:200]}",
        )
