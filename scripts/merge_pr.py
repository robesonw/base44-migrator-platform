#!/usr/bin/env python3
"""
Script to merge a Pull Request.
Usage: python scripts/merge_pr.py [PR_NUMBER]
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


def get_token_from_env_file():
    """Read GITHUB_TOKEN from .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        return None
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('GITHUB_TOKEN='):
                match = re.match(r'GITHUB_TOKEN=["\']?(.*?)["\']?$', line)
                if match:
                    token = match.group(1).strip()
                    if token:
                        return token
    return None


def merge_pr(pr_number: int, token: str, merge_method: str = "merge") -> dict:
    """Merge a Pull Request using GitHub API."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = {
        "merge_method": merge_method,  # merge, squash, or rebase
    }
    
    with httpx.Client(timeout=60) as client:
        response = client.put(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 405:
            error_data = response.json()
            raise Exception(f"Cannot merge PR: {error_data.get('message', 'PR may already be merged or not mergeable')}")
        elif response.status_code == 409:
            error_data = response.json()
            raise Exception(f"Merge conflict or other issue: {error_data.get('message', 'PR cannot be merged')}")
        else:
            error_data = response.json() if response.content else {}
            raise Exception(f"GitHub API error: {response.status_code} - {error_data.get('message', 'Unknown error')}")


def get_pr_status(pr_number: int, token: str) -> dict:
    """Get PR status to check if it's mergeable."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    with httpx.Client(timeout=60) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Merge a PR from dev to main")
    parser.add_argument("pr_number", type=int, nargs="?", default=1, help="PR number (default: 1)")
    parser.add_argument("--method", choices=["merge", "squash", "rebase"], default="merge", 
                       help="Merge method: merge (default), squash, or rebase")
    args = parser.parse_args()
    
    # Get token
    token = get_token_from_env_file()
    if not token:
        token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("ERROR: GitHub token not found.")
        print("\nPlease add your token to the .env file:")
        print('  GITHUB_TOKEN=your_token_here')
        sys.exit(1)
    
    try:
        # Check PR status first
        print(f"Checking PR #{args.pr_number} status...")
        pr_status = get_pr_status(args.pr_number, token)
        print(f"PR State: {pr_status['state']}")
        print(f"Mergeable: {pr_status.get('mergeable', 'unknown')}")
        print(f"Title: {pr_status['title']}")
        
        if pr_status['state'] != 'open':
            print(f"PR is not open (state: {pr_status['state']}). Cannot merge.")
            sys.exit(1)
        
        if pr_status.get('merged'):
            print("PR is already merged!")
            print(f"URL: {pr_status['html_url']}")
            sys.exit(0)
        
        # Merge the PR
        print(f"\nMerging PR #{args.pr_number} using {args.method} method...")
        result = merge_pr(args.pr_number, token, args.method)
        print("SUCCESS: Pull Request merged successfully!")
        print(f"Message: {result.get('message', 'Merged')}")
        print(f"URL: {pr_status['html_url']}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

