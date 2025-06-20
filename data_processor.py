#!/usr/bin/env python3
"""
Data processing utilities for commit data
"""

import csv
import logging
from typing import List, Dict, Set, Optional
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime

from config import CSV_FIELDS, OUTPUT_FORMATS, AUTHOR_MATCHING

logger = logging.getLogger(__name__)

class DataProcessor:
    """Handles data processing, filtering, and output operations"""
    
    def __init__(self):
        pass
    
    def filter_by_author(self, commits: List[Dict], author_pattern: str) -> List[Dict]:
        """Filter commits by author name with fuzzy matching"""
        if not author_pattern:
            return commits
        
        filtered_commits = []
        matched_authors = set()
        
        for commit in commits:
            if self._is_author_match(commit['author'], author_pattern):
                filtered_commits.append(commit)
                matched_authors.add(commit['author'])
        
        logger.info(f"Author filter '{author_pattern}' matched: {sorted(matched_authors)}")
        logger.info(f"Filtered to {len(filtered_commits)} commits from {len(commits)} total")
        
        return filtered_commits
    
    def _is_author_match(self, author_name: str, pattern: str) -> bool:
        """Check if author name matches the pattern with fuzzy matching"""
        author_lower = author_name.lower()
        pattern_lower = pattern.lower()
        
        # Direct substring match
        if pattern_lower in author_lower or author_lower in pattern_lower:
            return True
        
        # Generate variations of the pattern
        variations = self._generate_author_variations(pattern_lower)
        
        for variation in variations:
            if variation in author_lower or self._similarity(author_lower, variation) > AUTHOR_MATCHING["similarity_threshold"]:
                return True
        
        # Overall similarity check
        if self._similarity(author_lower, pattern_lower) > AUTHOR_MATCHING["exact_match_threshold"]:
            return True
        
        return False
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a, b).ratio()
    
    def _generate_author_variations(self, pattern: str) -> List[str]:
        """Generate common variations of an author name"""
        variations = [pattern]
        
        # Split on common separators and create variations
        if ' ' in pattern:
            parts = pattern.split()
            variations.extend(parts)  # Individual parts
            variations.append(''.join(parts))  # Concatenated
        
        if '-' in pattern:
            variations.extend(pattern.split('-'))
        
        if '_' in pattern:
            variations.extend(pattern.split('_'))
        
        # Add common prefixes/suffixes
        if len(pattern) > 4:
            variations.append(pattern[:4])  # First 4 chars
            variations.append(pattern[-4:])  # Last 4 chars
        
        return list(set(variations))
    
    def exclude_merge_commits(self, commits: List[Dict]) -> List[Dict]:
        """Filter out merge commits"""
        filtered = [c for c in commits if not c['message'].startswith('Merge')]
        logger.info(f"Excluded {len(commits) - len(filtered)} merge commits")
        return filtered
    
    def generate_statistics(self, commits: List[Dict]) -> Dict:
        """Generate comprehensive statistics from commit data"""
        if not commits:
            return {}
        
        stats = {
            'total_commits': len(commits),
            'unique_authors': len(set(c['author'] for c in commits)),
            'unique_repositories': len(set(c['repository'] for c in commits)),
            'date_range': {
                'earliest': min(c['timestamp'][:10] for c in commits),
                'latest': max(c['timestamp'][:10] for c in commits)
            },
            'repository_breakdown': defaultdict(int),
            'author_breakdown': defaultdict(int),
            'branch_breakdown': defaultdict(int) if 'branch' in commits[0] else None
        }
        
        # Calculate totals if stats are available
        if 'additions' in commits[0]:
            total_additions = sum(c.get('additions', 0) for c in commits)
            total_deletions = sum(c.get('deletions', 0) for c in commits)
            stats.update({
                'total_additions': total_additions,
                'total_deletions': total_deletions,
                'net_changes': total_additions - total_deletions,
                'repository_stats': defaultdict(lambda: {'commits': 0, 'additions': 0, 'deletions': 0})
            })
        
        # Aggregate data
        for commit in commits:
            repo = commit['repository']
            author = commit['author']
            
            stats['repository_breakdown'][repo] += 1
            stats['author_breakdown'][author] += 1
            
            if stats['branch_breakdown'] is not None and 'branch' in commit:
                branch_key = f"{repo}:{commit['branch']}"
                stats['branch_breakdown'][branch_key] += 1
            
            if 'additions' in commit:
                repo_stats = stats['repository_stats'][repo]
                repo_stats['commits'] += 1
                repo_stats['additions'] += commit.get('additions', 0)
                repo_stats['deletions'] += commit.get('deletions', 0)
        
        return stats
    
    def print_statistics(self, stats: Dict) -> None:
        """Print formatted statistics to console"""
        if not stats:
            print("No statistics available")
            return
        
        prefix = OUTPUT_FORMATS["console"]["info_prefix"]
        
        print(f"\n{prefix} Commit Collection Statistics:")
        print(f"   - Total commits: {stats['total_commits']:,}")
        print(f"   - Unique authors: {stats['unique_authors']}")
        print(f"   - Repositories: {stats['unique_repositories']}")
        print(f"   - Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        # Print code change statistics if available
        if 'total_additions' in stats:
            print(f"   - Lines added: {stats['total_additions']:,}")
            print(f"   - Lines deleted: {stats['total_deletions']:,}")
            print(f"   - Net change: {stats['net_changes']:+,}")
        
        # Top repositories
        if stats['repository_breakdown']:
            print(f"\n📈 Top repositories by commit count:")
            top_repos = sorted(stats['repository_breakdown'].items(), key=lambda x: x[1], reverse=True)[:10]
            for repo, count in top_repos:
                print(f"   - {repo}: {count} commits")
        
        # Top authors
        if len(stats['author_breakdown']) > 1:  # Only show if multiple authors
            print(f"\n👥 Top contributors:")
            top_authors = sorted(stats['author_breakdown'].items(), key=lambda x: x[1], reverse=True)[:5]
            for author, count in top_authors:
                print(f"   - {author}: {count} commits")
        
        # Repository statistics with code changes
        if 'repository_stats' in stats and stats['repository_stats']:
            print(f"\n💾 Repository breakdown with code changes:")
            for repo, repo_stats in sorted(stats['repository_stats'].items(), 
                                         key=lambda x: x[1]['commits'], reverse=True)[:10]:
                net_change = repo_stats['additions'] - repo_stats['deletions']
                print(f"   - {repo}: {repo_stats['commits']} commits, "
                      f"+{repo_stats['additions']:,}/-{repo_stats['deletions']:,} "
                      f"(net: {net_change:+,})")
    
    def save_to_csv(self, commits: List[Dict], filename: str, include_branches: bool = False, 
                   include_stats: bool = False) -> None:
        """Save commits to CSV file with appropriate field selection"""
        if not commits:
            logger.warning("No commits to save")
            return
        
        # Determine field names based on data structure
        if include_stats and 'additions' in commits[0]:
            fieldnames = CSV_FIELDS["with_stats"]
        elif include_branches and 'branch' in commits[0]:
            fieldnames = CSV_FIELDS["with_branches"]
        else:
            fieldnames = CSV_FIELDS["basic"]
        
        # Filter fieldnames to only include fields present in the data
        available_fields = set(commits[0].keys())
        fieldnames = [field for field in fieldnames if field in available_fields]
        
        try:
            with open(filename, 'w', newline=OUTPUT_FORMATS["csv"]["newline"], 
                     encoding=OUTPUT_FORMATS["csv"]["encoding"]) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for commit in commits:
                    # Only write fields that exist in the commit data
                    row = {field: commit.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            logger.info(f"✅ Saved {len(commits)} commits to {filename}")
            
        except IOError as e:
            raise Exception(f"Failed to save CSV file: {e}")
    
    def load_from_csv(self, filename: str) -> List[Dict]:
        """Load commits from CSV file"""
        try:
            commits = []
            with open(filename, 'r', encoding=OUTPUT_FORMATS["csv"]["encoding"]) as csvfile:
                reader = csv.DictReader(csvfile)
                commits = list(reader)
            
            logger.info(f"Loaded {len(commits)} commits from {filename}")
            return commits
            
        except IOError as e:
            raise Exception(f"Failed to load CSV file: {e}")
    
    def find_largest_commits(self, commits: List[Dict], limit: int = 10) -> List[Dict]:
        """Find commits with the most changes (requires stats data)"""
        if not commits or 'total_changes' not in commits[0]:
            return []
        
        # Filter out commits with no changes and sort by total changes
        commits_with_changes = [c for c in commits if c.get('total_changes', 0) > 0]
        return sorted(commits_with_changes, key=lambda x: int(x.get('total_changes', 0)), reverse=True)[:limit]
    
    def get_commit_timeline(self, commits: List[Dict]) -> Dict[str, int]:
        """Get commit count by date"""
        timeline = defaultdict(int)
        for commit in commits:
            date = commit['timestamp'][:10]  # Extract YYYY-MM-DD
            timeline[date] += 1
        return dict(timeline)