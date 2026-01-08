#!/usr/bin/env python3
"""
Script to create a PR from dev to main, reading token from .env file.
Usage: python scripts/create_pr_with_env.py
"""
import os
import sys
import re
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install it with: pip install httpx")
    sys.exit(1)

REPO_OWNER = "robesonw"
REPO_NAME = "base44-migrator-platform"
BASE_BRANCH = "main"
HEAD_BRANCH = "dev"
PR_TITLE = "Merge dev into main"
PR_BODY = """This PR merges the development branch into main.

## Changes
- Development branch setup
- Branch workflow established

## Workflow
- Development work happens on `dev` branch
- Changes are merged to `main` via Pull Requests"""


def get_token_from_env_file():
    """Read GITHUB_TOKEN from .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        return None
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('GITHUB_TOKEN='):
                # Extract token value (handles quoted and unquoted values)
                match = re.match(r'GITHUB_TOKEN=["\']?(.*?)["\']?$', line)
                if match:
                    token = match.group(1).strip()
                    if token:  # Only return non-empty tokens
                        return token
    return None


def create_pr(token: str) -> dict:
    """Create a Pull Request using GitHub API."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = {
        "title": PR_TITLE,
        "head": HEAD_BRANCH,
        "base": BASE_BRANCH,
        "body": PR_BODY,
    }
    
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 422:
            error_data = response.json()
            # Check if PR already exists
            list_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?head={REPO_OWNER}:{HEAD_BRANCH}&base={BASE_BRANCH}&state=open"
            list_response = client.get(list_url, headers=headers)
            if list_response.status_code == 200:
                prs = list_response.json()
                if prs:
                    return prs[0]
            raise Exception(f"GitHub API error: {response.status_code} - {error_data}")
        else:
            response.raise_for_status()
            raise Exception(f"GitHub API error: {response.status_code}")


def main():
    # Try to get token from .env file first
    token = get_token_from_env_file()
    
    # Fall back to environment variable
    if not token:
        token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("ERROR: GitHub token not found.")
        print("\nPlease add your token to the .env file:")
        print('  GITHUB_TOKEN=your_token_here')
        print("\nOr set the GITHUB_TOKEN environment variable.")
        print("\nYou can create a token at: https://github.com/settings/tokens")
        sys.exit(1)
    
    try:
        result = create_pr(token)
        print("SUCCESS: Pull Request created successfully!")
        print(f"Title: {result['title']}")
        print(f"URL: {result['html_url']}")
        print(f"Status: {result['state']}")
        return result['html_url']
    except Exception as e:
        print(f"ERROR: Error creating PR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

