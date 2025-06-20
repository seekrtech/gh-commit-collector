#!/usr/bin/env python3
"""
Configuration settings for GitHub Commit Collector
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CollectionConfig:
    """Configuration for commit collection"""
    organization: str
    since_date: str = "2025-01-01T00:00:00Z"
    until_date: Optional[str] = None
    include_stats: bool = False
    include_all_branches: bool = False
    author_filter: Optional[str] = None
    exclude_merge_commits: bool = False
    max_workers: int = 5
    batch_size: int = 10
    timeout_seconds: int = 30
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.organization:
            raise ValueError("Organization name is required")
        
        # Validate date format
        try:
            datetime.fromisoformat(self.since_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Invalid since_date format. Use ISO format like '2025-01-01T00:00:00Z'")
        
        if self.until_date:
            try:
                datetime.fromisoformat(self.until_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid until_date format. Use ISO format like '2025-12-31T23:59:59Z'")


# Default GitHub CLI command templates
GITHUB_COMMANDS = {
    "list_repos": ["gh", "repo", "list", "{org}", "--limit", "1000", "--json", "name"],
    "list_branches": ["gh", "api", "/repos/{org}/{repo}/branches", "--jq", ".[].name"],
    "get_commits": [
        "gh", "api", "/repos/{org}/{repo}/commits",
        "--method", "GET",
        "-f", "sha={branch}",
        "-f", "since={since}",
        "-f", "per_page=100",
        "--jq", ".[] | {message: .commit.message, author: .commit.author.name, date: .commit.author.date, sha: .sha}"
    ],
    "get_commit_stats": [
        "gh", "api", "/repos/{org}/{repo}/commits/{sha}",
        "--jq", ".stats | {additions: .additions, deletions: .deletions, total: .total}"
    ]
}

# CSV field mappings
CSV_FIELDS = {
    "basic": ["timestamp", "repository", "message", "author", "sha"],
    "with_branches": ["timestamp", "repository", "branch", "message", "author", "sha"],
    "with_stats": ["timestamp", "repository", "branch", "message", "author", "sha", "additions", "deletions", "total_changes"]
}

# Author name similarity configuration
AUTHOR_MATCHING = {
    "similarity_threshold": 0.7,
    "exact_match_threshold": 0.6
}

# Rate limiting and performance settings
PERFORMANCE_SETTINGS = {
    "max_concurrent_repos": 10,
    "max_concurrent_branches": 5,
    "api_timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1.0
}

# Output formatting
OUTPUT_FORMATS = {
    "csv": {
        "encoding": "utf-8",
        "newline": ""
    },
    "console": {
        "success_prefix": "✓",
        "error_prefix": "✗",
        "warning_prefix": "⚠",
        "info_prefix": "📊"
    }
}

def get_default_output_filename(org: str, config: CollectionConfig) -> str:
    """Generate default output filename based on configuration"""
    base_name = f"{org}_commits"
    
    if config.since_date:
        year = config.since_date[:4]
        base_name += f"_{year}"
    
    if config.include_all_branches:
        base_name += "_all_branches"
    
    if config.include_stats:
        base_name += "_with_stats"
    
    if config.author_filter:
        # Sanitize author name for filename
        author_clean = "".join(c for c in config.author_filter if c.isalnum() or c in "._-")
        base_name += f"_{author_clean}"
    
    return f"{base_name}.csv"

def validate_github_cli() -> bool:
    """Check if GitHub CLI is installed and authenticated"""
    import subprocess
    
    try:
        # Check if gh is installed
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
        
        # Check if authenticated
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        return result.returncode == 0
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False