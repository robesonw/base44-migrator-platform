#!/usr/bin/env python3
"""
Script to create a Pull Request from dev to main branch.
Usage: python scripts/create_pr.py [--token GITHUB_TOKEN]
"""
import os
import sys
import argparse
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
            # PR might already exist
            error_data = response.json()
            if "already exists" in str(error_data).lower():
                print("⚠️  Pull request from dev to main already exists.")
                # Try to get existing PRs
                list_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?head={REPO_OWNER}:{HEAD_BRANCH}&base={BASE_BRANCH}&state=open"
                list_response = client.get(list_url, headers=headers)
                if list_response.status_code == 200:
                    prs = list_response.json()
                    if prs:
                        print(f"✅ Found existing PR: {prs[0]['html_url']}")
                        return prs[0]
            raise Exception(f"GitHub API error: {response.status_code} - {error_data}")
        else:
            response.raise_for_status()
            raise Exception(f"GitHub API error: {response.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Create a PR from dev to main")
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub personal access token (or set GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()
    
    if not args.token:
        print("Error: GitHub token is required.")
        print("Set GITHUB_TOKEN environment variable or pass --token")
        print("\nYou can create a token at: https://github.com/settings/tokens")
        sys.exit(1)
    
    try:
        result = create_pr(args.token)
        print(f"✅ Pull Request created successfully!")
        print(f"📝 Title: {result['title']}")
        print(f"🔗 URL: {result['html_url']}")
        print(f"📊 Status: {result['state']}")
    except Exception as e:
        print(f"❌ Error creating PR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

