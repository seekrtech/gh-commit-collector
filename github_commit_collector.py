#!/usr/bin/env python3
"""
GitHub Commit Collector

A modern, clean program to collect commit messages from GitHub repositories
for a given organization and time range, with options for filtering and statistics.

Usage:
    python github_commit_collector.py <organization> [options]

Example:
    python github_commit_collector.py seekrtech --since 2025-01-01 --author ezoushen --stats
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import Optional

from config import CollectionConfig, get_default_output_filename, validate_github_cli
from github_client import GitHubClient, GitHubAPIError
from data_processor import DataProcessor

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Collect GitHub commit messages for an organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - collect all commits from 2025
  python github_commit_collector.py seekrtech

  # Filter by author with fuzzy matching
  python github_commit_collector.py seekrtech --author "ezoushen"

  # Include detailed statistics (lines added/deleted)
  python github_commit_collector.py seekrtech --stats

  # Collect from all branches (default is main branch only)
  python github_commit_collector.py seekrtech --all-branches

  # Custom date range
  python github_commit_collector.py seekrtech --since 2025-01-01 --until 2025-12-31

  # Exclude merge commits
  python github_commit_collector.py seekrtech --no-merge

  # Custom output filename
  python github_commit_collector.py seekrtech --output my_commits.csv

  # Verbose output for debugging
  python github_commit_collector.py seekrtech --verbose
        """
    )
    
    parser.add_argument(
        'organization',
        help='GitHub organization name (e.g., "seekrtech")'
    )
    
    parser.add_argument(
        '--since',
        default='2025-01-01T00:00:00Z',
        help='Start date for commit collection (ISO format, default: 2025-01-01T00:00:00Z)'
    )
    
    parser.add_argument(
        '--until',
        help='End date for commit collection (ISO format, optional)'
    )
    
    parser.add_argument(
        '--author',
        help='Filter commits by author name (supports fuzzy matching)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output CSV filename (auto-generated if not specified)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Include commit statistics (lines added/deleted) - slower but more detailed'
    )
    
    parser.add_argument(
        '--all-branches',
        action='store_true',
        help='Collect commits from all branches (default: main branch only)'
    )
    
    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='Exclude merge commits from results'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of repositories to process in parallel (default: 10)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=5,
        help='Maximum number of concurrent workers (default: 5)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='API request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--repos',
        nargs='+',
        help='Specific repositories to process (default: all repos in organization)'
    )
    
    return parser.parse_args()

def validate_date_format(date_string: str) -> bool:
    """Validate ISO date format"""
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def main() -> int:
    """Main entry point"""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate GitHub CLI
    if not validate_github_cli():
        print("❌ Error: GitHub CLI (gh) is not installed or not authenticated.")
        print("Please install GitHub CLI and run 'gh auth login' first.")
        print("Visit: https://cli.github.com/")
        return 1
    
    # Validate date formats
    if not validate_date_format(args.since):
        print(f"❌ Error: Invalid --since date format: {args.since}")
        print("Use ISO format like: 2025-01-01T00:00:00Z")
        return 1
    
    if args.until and not validate_date_format(args.until):
        print(f"❌ Error: Invalid --until date format: {args.until}")
        print("Use ISO format like: 2025-12-31T23:59:59Z")
        return 1
    
    try:
        # Create configuration
        config = CollectionConfig(
            organization=args.organization,
            since_date=args.since,
            until_date=args.until,
            include_stats=args.stats,
            include_all_branches=args.all_branches,
            author_filter=args.author,
            exclude_merge_commits=args.no_merge,
            max_workers=args.max_workers,
            batch_size=args.batch_size,
            timeout_seconds=args.timeout
        )
        
        # Initialize clients
        github_client = GitHubClient(config)
        data_processor = DataProcessor()
        
        print(f"🚀 Starting commit collection for organization: {args.organization}")
        print(f"📅 Date range: {args.since}" + (f" to {args.until}" if args.until else " to present"))
        
        if args.author:
            print(f"👤 Filtering by author: {args.author}")
        if args.stats:
            print("📊 Including detailed statistics (this will take longer)")
        if args.all_branches:
            print("🌿 Collecting from all branches")
        if args.no_merge:
            print("🚫 Excluding merge commits")
        
        print()
        
        # Collect commits
        if args.repos:
            print(f"📂 Processing specific repositories: {', '.join(args.repos)}")
            commits = github_client.collect_all_commits(args.repos)
        else:
            commits = github_client.collect_all_commits()
        
        if not commits:
            print("⚠️ No commits found matching the criteria")
            return 0
        
        # Apply filters
        if args.author:
            commits = data_processor.filter_by_author(commits, args.author)
            if not commits:
                print(f"⚠️ No commits found for author pattern: {args.author}")
                return 0
        
        if args.no_merge:
            commits = data_processor.exclude_merge_commits(commits)
        
        # Generate output filename if not provided
        output_filename = args.output or get_default_output_filename(args.organization, config)
        
        # Save to CSV
        data_processor.save_to_csv(
            commits, 
            output_filename,
            include_branches=config.include_all_branches,
            include_stats=config.include_stats
        )
        
        # Generate and display statistics
        stats = data_processor.generate_statistics(commits)
        data_processor.print_statistics(stats)
        
        # Show largest commits if stats are available
        if config.include_stats:
            largest_commits = data_processor.find_largest_commits(commits, limit=5)
            if largest_commits:
                print(f"\n🔝 Largest commits by lines changed:")
                for i, commit in enumerate(largest_commits, 1):
                    additions = commit.get('additions', 0)
                    deletions = commit.get('deletions', 0)
                    total = commit.get('total_changes', 0)
                    message = commit['message'][:60] + "..." if len(commit['message']) > 60 else commit['message']
                    print(f"   {i}. {commit['repository']}: +{additions}/-{deletions} (total: {total}) - {message}")
        
        print(f"\n✅ Successfully collected {len(commits)} commits")
        print(f"📄 Results saved to: {output_filename}")
        
        return 0
        
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())