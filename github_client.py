#!/usr/bin/env python3
"""
GitHub API client for collecting commit information
"""

import subprocess
import json
import logging
import time
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from config import CollectionConfig, GITHUB_COMMANDS, PERFORMANCE_SETTINGS

logger = logging.getLogger(__name__)

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass

class GitHubClient:
    """Client for interacting with GitHub API via GitHub CLI"""
    
    def __init__(self, config: CollectionConfig):
        self.config = config
        self.org = config.organization
        
    def _run_command(self, cmd: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Execute a command with error handling and retries"""
        timeout = timeout or self.config.timeout_seconds
        
        for attempt in range(PERFORMANCE_SETTINGS["retry_attempts"]):
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=timeout
                )
                
                if result.returncode == 0:
                    return result
                
                # If it's the last attempt, raise an error
                if attempt == PERFORMANCE_SETTINGS["retry_attempts"] - 1:
                    raise GitHubAPIError(f"Command failed: {' '.join(cmd)}\nError: {result.stderr}")
                
                # Wait before retry
                time.sleep(PERFORMANCE_SETTINGS["retry_delay"] * (attempt + 1))
                
            except subprocess.TimeoutExpired:
                if attempt == PERFORMANCE_SETTINGS["retry_attempts"] - 1:
                    raise GitHubAPIError(f"Command timed out: {' '.join(cmd)}")
                time.sleep(PERFORMANCE_SETTINGS["retry_delay"] * (attempt + 1))
        
        raise GitHubAPIError(f"All retry attempts failed for command: {' '.join(cmd)}")
    
    def get_repositories(self) -> List[str]:
        """Get list of repositories for the organization"""
        cmd = [c.format(org=self.org) if "{org}" in c else c for c in GITHUB_COMMANDS["list_repos"]]
        
        try:
            result = self._run_command(cmd)
            repo_data = json.loads(result.stdout)
            repositories = [repo['name'] for repo in repo_data]
            logger.info(f"Found {len(repositories)} repositories in {self.org}")
            return repositories
            
        except (json.JSONDecodeError, KeyError) as e:
            raise GitHubAPIError(f"Failed to parse repository list: {e}")
    
    def get_branches(self, repo: str) -> List[str]:
        """Get all branches for a repository"""
        cmd = [c.format(org=self.org, repo=repo) if any(p in c for p in ["{org}", "{repo}"]) else c 
               for c in GITHUB_COMMANDS["list_branches"]]
        
        try:
            result = self._run_command(cmd, timeout=15)
            
            if not result.stdout.strip():
                return ["main", "master"]  # fallback
            
            branches = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return branches if branches else ["main", "master"]
            
        except GitHubAPIError:
            logger.warning(f"Failed to get branches for {repo}, using defaults")
            return ["main", "master"]
    
    def get_commits_for_branch(self, repo: str, branch: str) -> List[Dict]:
        """Get commits for a specific repository branch"""
        cmd_template = GITHUB_COMMANDS["get_commits"]
        cmd = []
        
        for part in cmd_template:
            if "{org}" in part and "{repo}" in part:
                cmd.append(part.format(org=self.org, repo=repo))
            elif "{org}" in part:
                cmd.append(part.format(org=self.org))
            elif "{repo}" in part:
                cmd.append(part.format(repo=repo))
            elif "{branch}" in part:
                cmd.append(part.format(branch=branch))
            elif "{since}" in part:
                cmd.append(part.format(since=self.config.since_date))
            else:
                cmd.append(part)
        
        # Add until date if specified
        if self.config.until_date:
            cmd.extend(["-f", f"until={self.config.until_date}"])
        
        try:
            result = self._run_command(cmd)
            
            if not result.stdout.strip():
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        commit_data = json.loads(line)
                        
                        # Filter merge commits if requested
                        if self.config.exclude_merge_commits and commit_data['message'].startswith('Merge'):
                            continue
                        
                        commits.append({
                            'timestamp': commit_data['date'],
                            'repository': repo,
                            'branch': branch,
                            'message': commit_data['message'].replace('\n', ' ').replace('\r', ' ').strip()[:500],
                            'author': commit_data['author'],
                            'sha': commit_data['sha'][:8]
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse commit in {repo}:{branch}: {e}")
                        continue
            
            return commits
            
        except GitHubAPIError as e:
            logger.error(f"Failed to get commits for {repo}:{branch}: {e}")
            return []
    
    def get_commit_stats(self, repo: str, sha: str) -> Dict[str, int]:
        """Get statistics (additions/deletions) for a specific commit"""
        if not self.config.include_stats:
            return {'additions': 0, 'deletions': 0, 'total': 0}
        
        # Try to get full SHA if we only have partial
        full_sha = sha
        if len(sha) <= 8:
            full_sha = self._get_full_sha(repo, sha)
        
        # Simplified command construction
        cmd = [
            "gh", "api", f"/repos/{self.org}/{repo}/commits/{full_sha}",
            "--jq", ".stats | {additions: .additions, deletions: .deletions, total: .total}"
        ]
        
        try:
            result = self._run_command(cmd, timeout=15)
            
            if result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                return {'additions': 0, 'deletions': 0, 'total': 0}
                
        except (GitHubAPIError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to get stats for {repo}/{sha}: {e}")
            return {'additions': 0, 'deletions': 0, 'total': 0}
    
    def _get_full_sha(self, repo: str, short_sha: str) -> str:
        """Get full SHA from short SHA"""
        # For stats API, we can use the short SHA directly since GitHub accepts partial SHAs
        # as long as they're unique (which 8 characters usually are)
        if len(short_sha) >= 7:  # GitHub typically needs at least 7 characters
            return short_sha
        
        # Only try to expand if it's really short
        cmd = [
            "gh", "api", f"/repos/{self.org}/{repo}/commits",
            "--jq", f".[] | select(.sha | startswith(\"{short_sha}\")) | .sha"
        ]
        
        try:
            result = self._run_command(cmd, timeout=10)
            if result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except GitHubAPIError:
            pass
        
        return short_sha  # Return as-is rather than padding with invalid zeros
    
    def get_commits_for_repo(self, repo: str) -> List[Dict]:
        """Get all commits for a repository (all branches if configured)"""
        try:
            all_commits = []
            commit_shas: Set[str] = set()
            
            if self.config.include_all_branches:
                branches = self.get_branches(repo)
            else:
                branches = ["main"]  # Default to main branch only
            
            for branch in branches:
                branch_commits = self.get_commits_for_branch(repo, branch)
                
                # Deduplicate commits across branches
                for commit in branch_commits:
                    try:
                        sha = commit['sha']
                        if sha not in commit_shas:
                            commit_shas.add(sha)
                            
                            # Add stats if requested
                            if self.config.include_stats:
                                logger.debug(f"Getting stats for {repo}/{sha}")
                                stats = self.get_commit_stats(repo, sha)
                                commit.update({
                                    'additions': stats.get('additions', 0),
                                    'deletions': stats.get('deletions', 0),
                                    'total_changes': stats.get('total', 0)
                                })
                            
                            all_commits.append(commit)
                    except KeyError as e:
                        logger.error(f"KeyError processing commit in {repo}: missing key {e}")
                        logger.error(f"Commit data: {commit}")
                        logger.error(f"Available keys: {list(commit.keys()) if isinstance(commit, dict) else 'not a dict'}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing commit in {repo}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
            
            logger.info(f"✓ {repo}: {len(all_commits)} commits across {len(branches)} branches")
            return all_commits
            
        except Exception as e:
            logger.error(f"Error processing repository {repo}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def collect_all_commits(self, repositories: Optional[List[str]] = None) -> List[Dict]:
        """Collect commits from all repositories with parallel processing"""
        if repositories is None:
            repositories = self.get_repositories()
        
        all_commits = []
        batch_size = self.config.batch_size
        
        logger.info(f"Processing {len(repositories)} repositories in batches of {batch_size}")
        
        for i in range(0, len(repositories), batch_size):
            batch = repositories[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(repositories) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches}: {len(batch)} repos")
            
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_repo = {
                    executor.submit(self.get_commits_for_repo, repo): repo 
                    for repo in batch
                }
                
                for future in as_completed(future_to_repo, timeout=120):
                    repo = future_to_repo[future]
                    try:
                        commits = future.result()
                        all_commits.extend(commits)
                    except Exception as e:
                        logger.error(f"✗ {repo}: {e}")
        
        # Sort by timestamp (newest first)
        all_commits.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"Collected {len(all_commits)} total commits")
        return all_commits