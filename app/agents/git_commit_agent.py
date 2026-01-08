from __future__ import annotations
import os
import re
import shutil
import logging
from pathlib import Path
from typing import List
from git import Repo
import asyncio
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage
from app.core.config import settings
from app.core.github import GitHubClient

log = logging.getLogger(__name__)


class GitCommitAgent(BaseAgent):
    stage = JobStage.CREATE_PR

    def run(self, job, ws) -> AgentResult:
        """Commit generated backend and artifacts to target repo."""
        try:
            # Get paths
            workspace_root = ws.root
            target_repo_dir = workspace_root / "target_repo"
            generated_backend_dir = workspace_root / "generated" / "backend"
            artifacts_dir = ws.artifacts_dir  # This is workspace/ directory

            # Validate inputs
            if not generated_backend_dir.exists():
                return AgentResult(
                    self.stage,
                    False,
                    f"Generated backend directory not found: {generated_backend_dir}",
                    {}
                )

            # Clone target repo
            repo_was_empty = False
            if target_repo_dir.exists() and any(target_repo_dir.iterdir()):
                log.info(f"Target repo already exists at {target_repo_dir}, reusing it")
                repo = Repo(target_repo_dir)
            else:
                log.info(f"Cloning target repo {job.target_repo_url} to {target_repo_dir}")
                try:
                    repo = Repo.clone_from(job.target_repo_url, target_repo_dir, depth=1)
                except Exception as e:
                    # If clone fails (e.g., empty repo), initialize a new repo
                    log.warning(f"Clone failed (may be empty repo): {e}, initializing new repo")
                    repo = Repo.init(target_repo_dir)
                    repo.create_remote("origin", job.target_repo_url)
                    repo_was_empty = True

            # Determine default branch
            base_branch = self._get_base_branch(repo, job.target_repo_url)
            log.info(f"Using base branch: {base_branch}")

            # Create branch name
            branch_name = f"base44-migration/{job.id}-backend"

            # Check if repo is empty (no commits)
            is_empty = False
            try:
                repo.head.commit
            except (ValueError, AttributeError, TypeError):
                is_empty = True
            
            if is_empty or repo_was_empty:
                # Repository is empty, create initial commit and base branch
                log.info(f"Repository is empty, creating initial commit on {base_branch}")
                (target_repo_dir / "README.md").write_text("# Generated Backend\n", encoding="utf-8")
                repo.git.add("README.md")
                repo.git.commit("-m", "Initial commit")
                # Create and checkout base branch
                if base_branch not in [h.name for h in repo.heads]:
                    repo.git.checkout("-b", base_branch)
                else:
                    repo.git.checkout(base_branch)
            else:
                # Repo has commits, checkout base branch
                try:
                    repo.git.checkout(base_branch)
                    try:
                        repo.git.pull("origin", base_branch)
                    except Exception:
                        log.warning(f"Could not pull {base_branch}, continuing")
                except Exception:
                    # Base branch doesn't exist locally, create it from current HEAD
                    repo.git.checkout("-b", base_branch)

            # Create or checkout branch
            if branch_name in [h.name for h in repo.heads]:
                repo.git.checkout(branch_name)
                repo.git.pull("origin", branch_name)
            else:
                repo.git.checkout("-b", branch_name)

            # Copy backend
            backend_dest = target_repo_dir / "backend"
            copied_files = []
            if backend_dest.exists():
                log.info(f"Removing existing backend directory: {backend_dest}")
                shutil.rmtree(backend_dest)
            log.info(f"Copying backend from {generated_backend_dir} to {backend_dest}")
            shutil.copytree(generated_backend_dir, backend_dest)
            copied_files.append(f"backend/ (entire directory)")

            # Copy artifacts
            artifacts_dest_dir = target_repo_dir / "migrator-artifacts" / job.id
            artifacts_dest_dir.mkdir(parents=True, exist_ok=True)
            
            artifact_files = [
                "storage-plan.json",
                "openapi.yaml",
                "db-schema.sql",
                "mongo-schemas.json",
                "verification.md",
            ]
            
            for artifact_file in artifact_files:
                src_path = artifacts_dir / artifact_file
                if src_path.exists():
                    dest_path = artifacts_dest_dir / artifact_file
                    shutil.copy2(src_path, dest_path)
                    copied_files.append(f"migrator-artifacts/{job.id}/{artifact_file}")
                    log.info(f"Copied {artifact_file} to {dest_path}")
                else:
                    log.warning(f"Artifact file not found: {src_path}")

            # Stage all changes
            repo.git.add(all=True)

            # Commit
            commit_message = f"chore: add generated backend for {job.id}"
            if repo.is_dirty(untracked_files=True):
                repo.index.commit(commit_message)
                commit_hash = repo.head.commit.hexsha
                log.info(f"Committed changes with hash: {commit_hash}")
            else:
                commit_hash = repo.head.commit.hexsha
                log.info("No changes to commit (using existing commit)")
                return AgentResult(
                    self.stage,
                    True,
                    "No changes to commit",
                    {
                        "branch": branch_name,
                        "commit_hash": commit_hash,
                        "pushed": False,
                    }
                )

            # Push branch
            try:
                repo.git.push("origin", branch_name, set_upstream=True)
                log.info(f"Pushed branch {branch_name} to origin")
                pushed = True
            except Exception as push_error:
                log.error(f"Failed to push branch: {push_error}")
                pushed = False
                return AgentResult(
                    self.stage,
                    False,
                    f"Failed to push branch: {push_error}",
                    {}
                )

            # Get PR URL (if created)
            pr_url = None
            github_token = self._get_github_token()
            
            if github_token:
                pr_url = asyncio.run(self._create_pr(
                    github_token=github_token,
                    repo_url=job.target_repo_url,
                    base_branch=base_branch,
                    head_branch=branch_name,
                    job_id=job.id,
                    source_repo_url=job.source_repo_url,
                    db_stack=job.db_stack,
                ))
                if pr_url:
                    log.info(f"Created PR: {pr_url}")

            # Write gitops.md (always write, even if PR was created)
            gitops_md_path = artifacts_dir / "gitops.md"
            gitops_content = self._generate_gitops_md(
                branch_name=branch_name,
                commit_hash=commit_hash,
                pr_url=pr_url,
                copied_files=copied_files,
                repo_url=job.target_repo_url,
                base_branch=base_branch,
                head_branch=branch_name,
                github_token_exists=github_token is not None,
            )
            gitops_md_path.write_text(gitops_content, encoding="utf-8")
            log.info(f"Wrote gitops.md to {gitops_md_path}")

            # Also copy gitops.md to artifacts in target repo
            artifacts_gitops_dest = artifacts_dest_dir / "gitops.md"
            shutil.copy2(gitops_md_path, artifacts_gitops_dest)
            copied_files.append(f"migrator-artifacts/{job.id}/gitops.md")

            return AgentResult(
                self.stage,
                True,
                f"Committed and pushed to {branch_name}" + (f", PR: {pr_url}" if pr_url else ""),
                {
                    "branch": branch_name,
                    "commit_hash": commit_hash,
                    "pr_url": pr_url or "not created",
                    "pushed": pushed,
                    "gitops_note": str(gitops_md_path.relative_to(workspace_root)),
                }
            )

        except Exception as e:
            log.exception(f"GitCommitAgent failed: {e}")
            return AgentResult(
                self.stage,
                False,
                f"GitCommitAgent failed: {e}",
                {}
            )

    def _get_base_branch(self, repo: Repo, repo_url: str) -> str:
        """Determine the default branch, defaulting to 'main'."""
        try:
            # Try to get the default branch from remote
            remote = repo.remotes.origin
            remote_refs = remote.fetch()
            for ref in remote_refs:
                if ref.remote_head == "main" or ref.remote_head == "master":
                    return ref.remote_head
            # Fallback to repo's active branch or main
            if repo.active_branch:
                return repo.active_branch.name
            return "main"
        except Exception as e:
            log.warning(f"Could not determine base branch, defaulting to main: {e}")
            return "main"

    def _get_github_token(self) -> str | None:
        """Get GitHub token from environment variable or settings."""
        # Check GH_TOKEN environment variable first (as per requirements)
        token = os.getenv("GH_TOKEN")
        if token:
            return token
        # Also check GITHUB_TOKEN (common alternative)
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
        # Fallback to settings.github_token
        return settings.github_token

    async def _create_pr(
        self,
        github_token: str,
        repo_url: str,
        base_branch: str,
        head_branch: str,
        job_id: str,
        source_repo_url: str,
        db_stack: str,
    ) -> str | None:
        """Create a PR via GitHub API. Returns PR URL or None."""
        try:
            owner, repo_name = self._parse_repo_url(repo_url)
            client = GitHubClient(token=github_token)
            
            # Determine storage mode
            storage_mode = db_stack.lower() if db_stack else "unknown"
            
            # Build PR body
            pr_body = self._generate_pr_body(
                source_repo_url=source_repo_url,
                storage_mode=storage_mode,
                job_id=job_id,
            )
            
            pr_data = await client.create_pr(
                owner=owner,
                repo=repo_name,
                head=head_branch,
                base=base_branch,
                title=f"Backend scaffold (generated) - {job_id}",
                body=pr_body,
            )
            
            pr_url = pr_data.get("html_url") or pr_data.get("url", "")
            return pr_url
        except Exception as e:
            log.error(f"Failed to create PR: {e}")
            return None

    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Parse GitHub repo URL to extract owner and repo name."""
        # Handle formats like:
        # https://github.com/owner/repo.git
        # https://github.com/owner/repo
        # git@github.com:owner/repo.git
        pattern = r"(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$"
        match = re.match(pattern, repo_url)
        if match:
            owner = match.group(1)
            repo_name = match.group(2)
            return owner, repo_name
        raise ValueError(f"Could not parse repo URL: {repo_url}")

    def _generate_pr_body(
        self,
        source_repo_url: str,
        storage_mode: str,
        job_id: str,
    ) -> str:
        """Generate PR body with required information."""
        lines = [
            f"## Backend Scaffold - Job {job_id}",
            "",
            f"**Source Repository:** {source_repo_url}",
            f"**Storage Mode:** {storage_mode}",
            "",
            "## How to Run",
            "",
            "```bash",
            "cd backend && docker compose up --build",
            "```",
            "",
            "## Smoke Test",
            "",
            "```bash",
            "cd backend",
            "docker compose up -d",
            "sleep 5  # Wait for services to start",
            "curl http://localhost:8080/v1/health",
            "```",
            "",
            "## Generated Files",
            "",
            "- Backend code in `/backend`",
            "- Migration artifacts in `/migrator-artifacts/{job_id}/`",
        ]
        return "\n".join(lines)

    def _generate_gitops_md(
        self,
        branch_name: str,
        commit_hash: str,
        pr_url: str | None,
        copied_files: List[str],
        repo_url: str,
        base_branch: str,
        head_branch: str,
        github_token_exists: bool,
    ) -> str:
        """Generate gitops.md content."""
        lines = [
            "# GitOps Operations",
            "",
            f"**Branch:** `{branch_name}`",
            f"**Commit Hash:** `{commit_hash}`",
            f"**PR URL:** {pr_url if pr_url else 'not created'}",
            "",
            "## Repository Information",
            "",
            f"- **Target Repo:** {repo_url}",
            f"- **Base Branch:** {base_branch}",
            f"- **Head Branch:** {head_branch}",
            "",
            "## Copied Files",
            "",
        ]
        
        for file_path in copied_files:
            lines.append(f"- `{file_path}`")
        
        lines.extend([
            "",
            "## Pull Request",
            "",
        ])
        
        if pr_url:
            lines.extend([
                f"PR was automatically created: {pr_url}",
            ])
        else:
            owner, repo_name = self._parse_repo_url(repo_url)
            pr_create_url = f"https://github.com/{owner}/{repo_name}/compare/{base_branch}...{head_branch}"
            lines.extend([
                "PR was not automatically created.",
                "",
                "### Create PR Manually",
                "",
                f"1. Go to: {pr_create_url}",
                "2. Click 'Create Pull Request'",
                f"3. Set base branch to: `{base_branch}`",
                f"4. Set head branch to: `{head_branch}`",
                "5. Fill in PR title and description",
                "6. Submit the PR",
                "",
            ])
            
            if not github_token_exists:
                lines.extend([
                    "### Note",
                    "",
                    "To enable automatic PR creation, set the `GH_TOKEN` environment variable.",
                ])
        
        return "\n".join(lines)

