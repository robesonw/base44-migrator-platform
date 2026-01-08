from __future__ import annotations
import httpx
from dataclasses import dataclass
from app.core.config import settings

@dataclass
class GitHubClient:
    token: str
    api_base: str = settings.github_api_base

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    async def create_pr(self, owner: str, repo: str, head: str, base: str, title: str, body: str) -> dict:
        url = f"{self.api_base}/repos/{owner}/{repo}/pulls"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                url,
                headers=self._headers(),
                json={"title": title, "head": head, "base": base, "body": body},
            )
            r.raise_for_status()
            return r.json()

# NOTE: For production, prefer a GitHub App installation token over a PAT.
