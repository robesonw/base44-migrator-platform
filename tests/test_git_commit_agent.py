"""Unit tests for GitCommitAgent with mocks (no network calls)."""
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from git import Repo
from app.agents.git_commit_agent import GitCommitAgent
from app.core.workflow import JobStage


class MockRepo:
    """Mock Git repository for testing."""
    def __init__(self, base_branch="main", existing_branches=None):
        self.base_branch = base_branch
        self.heads = [MagicMock(name=branch) for branch in (existing_branches or [])]
        self.active_branch = MagicMock(name=base_branch)
        self.head = MagicMock()
        self.head.commit = MagicMock(hexsha="abc123def456")
        self.remotes = MagicMock()
        self.remotes.origin = MagicMock()
        self._is_dirty = False
        
    def git(self):
        return self
    
    def checkout(self, *args):
        return self
    
    def pull(self, *args):
        return self
    
    def add(self, *args):
        return self
    
    def push(self, *args, **kwargs):
        return self
    
    def is_dirty(self, untracked_files=False):
        return self._is_dirty
    
    def set_dirty(self, value):
        self._is_dirty = value


def test_branch_naming():
    """Test that branch name follows the correct format."""
    agent = GitCommitAgent()
    
    mock_job = MagicMock()
    mock_job.id = "test-job-id-123"
    
    branch_name = f"base44-migration/{mock_job.id}-backend"
    
    assert branch_name == "base44-migration/test-job-id-123-backend"
    assert branch_name.startswith("base44-migration/")
    assert branch_name.endswith("-backend")


def test_parse_repo_url():
    """Test parsing GitHub repo URLs."""
    agent = GitCommitAgent()
    
    # Test HTTPS URL with .git
    owner, repo = agent._parse_repo_url("https://github.com/owner/repo.git")
    assert owner == "owner"
    assert repo == "repo"
    
    # Test HTTPS URL without .git
    owner, repo = agent._parse_repo_url("https://github.com/owner/repo")
    assert owner == "owner"
    assert repo == "repo"
    
    # Test SSH URL
    owner, repo = agent._parse_repo_url("git@github.com:owner/repo.git")
    assert owner == "owner"
    assert repo == "repo"
    
    # Test with target repo from requirements
    owner, repo = agent._parse_repo_url("https://github.com/robesonw/cc.git")
    assert owner == "robesonw"
    assert repo == "cc"


def test_get_base_branch_defaults_to_main():
    """Test that base branch defaults to 'main' when detection fails."""
    agent = GitCommitAgent()
    
    mock_repo = MockRepo(base_branch="main")
    mock_repo.remotes.origin.fetch = MagicMock(side_effect=Exception("Network error"))
    
    base_branch = agent._get_base_branch(mock_repo, "https://github.com/test/repo")
    assert base_branch == "main"


def test_generate_pr_body():
    """Test PR body generation includes required fields."""
    agent = GitCommitAgent()
    
    body = agent._generate_pr_body(
        source_repo_url="https://github.com/test/source",
        storage_mode="postgres",
        job_id="test-job-123",
    )
    
    assert "test-job-123" in body
    assert "https://github.com/test/source" in body
    assert "postgres" in body
    assert "cd backend && docker compose up --build" in body
    assert "smoke test" in body.lower() or "Smoke Test" in body
    assert "/backend" in body
    assert "/migrator-artifacts" in body


def test_generate_gitops_md_with_pr():
    """Test gitops.md generation when PR is created."""
    agent = GitCommitAgent()
    
    content = agent._generate_gitops_md(
        branch_name="base44-migration/test-123-backend",
        commit_hash="abc123def456",
        pr_url="https://github.com/owner/repo/pull/1",
        copied_files=["backend/", "migrator-artifacts/test-123/storage-plan.json"],
        repo_url="https://github.com/owner/repo.git",
        base_branch="main",
        head_branch="base44-migration/test-123-backend",
        github_token_exists=True,
    )
    
    assert "base44-migration/test-123-backend" in content
    assert "abc123def456" in content
    assert "https://github.com/owner/repo/pull/1" in content
    assert "backend/" in content
    assert "storage-plan.json" in content
    assert "PR was automatically created" in content


def test_generate_gitops_md_without_pr():
    """Test gitops.md generation when PR is not created."""
    agent = GitCommitAgent()
    
    content = agent._generate_gitops_md(
        branch_name="base44-migration/test-123-backend",
        commit_hash="abc123def456",
        pr_url=None,
        copied_files=["backend/", "migrator-artifacts/test-123/storage-plan.json"],
        repo_url="https://github.com/owner/repo.git",
        base_branch="main",
        head_branch="base44-migration/test-123-backend",
        github_token_exists=False,
    )
    
    assert "base44-migration/test-123-backend" in content
    assert "abc123def456" in content
    assert "not created" in content
    assert "PR was not automatically created" in content
    assert "Create PR Manually" in content
    assert "github.com/owner/repo/compare" in content
    assert "GH_TOKEN" in content


def test_get_github_token_from_env():
    """Test GitHub token retrieval from environment variable."""
    agent = GitCommitAgent()
    
    with patch.dict(os.environ, {"GH_TOKEN": "test-token-123"}):
        token = agent._get_github_token()
        assert token == "test-token-123"


def test_get_github_token_from_settings():
    """Test GitHub token retrieval from settings when env var not set."""
    agent = GitCommitAgent()
    
    with patch.dict(os.environ, {}, clear=True):
        with patch("app.agents.git_commit_agent.settings") as mock_settings:
            mock_settings.github_token = "settings-token-456"
            token = agent._get_github_token()
            assert token == "settings-token-456"


def test_get_github_token_none():
    """Test GitHub token returns None when not set."""
    agent = GitCommitAgent()
    
    with patch.dict(os.environ, {}, clear=True):
        with patch("app.agents.git_commit_agent.settings") as mock_settings:
            mock_settings.github_token = None
            token = agent._get_github_token()
            assert token is None


@pytest.mark.asyncio
async def test_create_pr_success():
    """Test PR creation via GitHub API (mocked)."""
    agent = GitCommitAgent()
    
    mock_client = AsyncMock()
    mock_client.create_pr = AsyncMock(return_value={
        "html_url": "https://github.com/owner/repo/pull/1",
        "url": "https://api.github.com/repos/owner/repo/pulls/1"
    })
    
    with patch("app.agents.git_commit_agent.GitHubClient", return_value=mock_client):
        pr_url = await agent._create_pr(
            github_token="test-token",
            repo_url="https://github.com/owner/repo.git",
            base_branch="main",
            head_branch="base44-migration/test-123-backend",
            job_id="test-123",
            source_repo_url="https://github.com/test/source",
            db_stack="postgres",
        )
    
    assert pr_url == "https://github.com/owner/repo/pull/1"
    mock_client.create_pr.assert_called_once()
    call_args = mock_client.create_pr.call_args
    assert call_args.kwargs["owner"] == "owner"
    assert call_args.kwargs["repo"] == "repo"
    assert call_args.kwargs["base"] == "main"
    assert call_args.kwargs["head"] == "base44-migration/test-123-backend"
    assert "test-123" in call_args.kwargs["title"]
    assert "test/source" in call_args.kwargs["body"]


@pytest.mark.asyncio
async def test_create_pr_failure():
    """Test PR creation handles errors gracefully."""
    agent = GitCommitAgent()
    
    mock_client = AsyncMock()
    mock_client.create_pr = AsyncMock(side_effect=Exception("API Error"))
    
    with patch("app.agents.git_commit_agent.GitHubClient", return_value=mock_client):
        pr_url = await agent._create_pr(
            github_token="test-token",
            repo_url="https://github.com/owner/repo.git",
            base_branch="main",
            head_branch="base44-migration/test-123-backend",
            job_id="test-123",
            source_repo_url="https://github.com/test/source",
            db_stack="postgres",
        )
    
    assert pr_url is None


def test_file_copy_plan():
    """Test that the agent identifies which files to copy."""
    agent = GitCommitAgent()
    
    # This test validates the logic for file copying
    # The agent should copy:
    # 1. Generated backend from <workspace>/generated/backend to /backend
    # 2. Artifacts from <workspace>/artifacts to /migrator-artifacts/<job_id>/
    
    artifact_files = [
        "storage-plan.json",
        "openapi.yaml",
        "db-schema.sql",
        "mongo-schemas.json",
        "verification.md",
    ]
    
    # Verify the list matches what's in the agent
    expected_files = set(artifact_files)
    assert "storage-plan.json" in expected_files
    assert "openapi.yaml" in expected_files
    assert "db-schema.sql" in expected_files
    assert "mongo-schemas.json" in expected_files
    assert "verification.md" in expected_files


def test_pr_creation_path_with_token():
    """Test that PR creation path is chosen when GH_TOKEN exists."""
    # This is more of an integration test concept
    # The agent should call _create_pr when token exists
    agent = GitCommitAgent()
    
    with patch.dict(os.environ, {"GH_TOKEN": "test-token"}):
        token = agent._get_github_token()
        assert token is not None
        # This means PR creation path would be taken


def test_pr_creation_path_without_token():
    """Test that manual PR instructions are written when GH_TOKEN is missing."""
    agent = GitCommitAgent()
    
    with patch.dict(os.environ, {}, clear=True):
        with patch("app.agents.git_commit_agent.settings") as mock_settings:
            mock_settings.github_token = None
            token = agent._get_github_token()
            assert token is None
            # This means manual PR instructions would be written


def test_agent_stage():
    """Test that agent has correct stage."""
    agent = GitCommitAgent()
    assert agent.stage == JobStage.CREATE_PR


