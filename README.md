# GitHub Commit Collector

A modern, clean Python program to collect commit messages from GitHub repositories for a given organization and time range. This tool provides comprehensive commit data export with filtering options and detailed statistics.

## Features

- ✅ **Comprehensive Commit Collection**: Gather commits from all repositories in a GitHub organization
- 🔍 **Flexible Filtering**: Filter by author, date range, exclude merge commits
- 📊 **Detailed Statistics**: Optional commit statistics including lines added/deleted
- 🌿 **Multi-Branch Support**: Collect from main branch only or all branches
- ⚡ **Parallel Processing**: Fast collection using concurrent processing
- 📄 **CSV Export**: Clean CSV output with customizable fields
- 🎯 **Fuzzy Author Matching**: Smart author name matching for filtering
- 🔧 **Configurable**: Extensive configuration options for different use cases

## Prerequisites

1. **GitHub CLI**: Install the GitHub CLI tool
   ```bash
   # On macOS
   brew install gh
   
   # On Ubuntu/Debian
   sudo apt install gh
   
   # On Windows
   winget install --id GitHub.cli
   ```

2. **Authentication**: Authenticate with GitHub
   ```bash
   gh auth login
   ```

3. **Python 3.7+**: Ensure you have Python 3.7 or higher installed

## Installation

1. Clone or download the repository files:
   - `github_commit_collector.py` (main program)
   - `config.py` (configuration settings)
   - `github_client.py` (GitHub API client)
   - `data_processor.py` (data processing utilities)

2. No additional Python packages required - uses only standard library modules

## Usage

### Basic Usage

```bash
# Collect all commits from an organization since 2025-01-01
python github_commit_collector.py seekrtech

# Collect commits with a custom start date
python github_commit_collector.py seekrtech --since 2024-01-01T00:00:00Z
```

### Advanced Usage

```bash
# Filter commits by author (supports fuzzy matching)
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

# Process only specific repositories
python github_commit_collector.py seekrtech --repos repo1 repo2 repo3

# Verbose output for debugging
python github_commit_collector.py seekrtech --verbose
```

### Complete Example

```bash
# Comprehensive collection with all features
python github_commit_collector.py seekrtech \
  --author "ezoushen" \
  --since 2025-01-01T00:00:00Z \
  --until 2025-12-31T23:59:59Z \
  --stats \
  --all-branches \
  --no-merge \
  --output ezoushen_commits_2025.csv \
  --verbose
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `organization` | GitHub organization name (required) | - |
| `--since` | Start date for commit collection (ISO format) | `2025-01-01T00:00:00Z` |
| `--until` | End date for commit collection (ISO format) | None (present) |
| `--author` | Filter commits by author name (fuzzy matching) | None |
| `--output`, `-o` | Output CSV filename | Auto-generated |
| `--stats` | Include commit statistics (lines added/deleted) | False |
| `--all-branches` | Collect from all branches | False (main only) |
| `--no-merge` | Exclude merge commits | False |
| `--batch-size` | Repositories to process in parallel | 10 |
| `--max-workers` | Maximum concurrent workers | 5 |
| `--timeout` | API request timeout (seconds) | 30 |
| `--verbose`, `-v` | Enable verbose logging | False |
| `--repos` | Specific repositories to process | All repos |

## Output Format

The program generates CSV files with the following columns:

### Basic Output
- `timestamp`: Commit timestamp (ISO format)
- `repository`: Repository name
- `message`: Commit message (truncated to 500 chars)
- `author`: Author name
- `sha`: Short commit SHA (8 characters)

### With Branches (`--all-branches`)
- All basic fields plus:
- `branch`: Branch name

### With Statistics (`--stats`)
- All fields plus:
- `additions`: Lines added
- `deletions`: Lines deleted
- `total_changes`: Total lines changed

## Configuration

The program uses several configuration files:

- `config.py`: Main configuration settings
- `github_client.py`: GitHub API interaction logic
- `data_processor.py`: Data processing and filtering utilities

You can modify these files to customize behavior, add new features, or adjust default settings.

## Performance Considerations

- **Basic Collection**: Fast, collects essential commit data
- **With Statistics**: Slower due to additional API calls for each commit
- **All Branches**: Slower due to processing multiple branches per repository
- **Parallel Processing**: Configurable batch size and worker count for optimal performance

### Typical Performance
- ~100 repositories: 2-5 minutes (basic)
- ~100 repositories: 10-20 minutes (with stats)
- Large organizations (500+ repos): 30+ minutes (with stats)

## Error Handling

The program includes comprehensive error handling:

- **GitHub CLI Issues**: Checks for installation and authentication
- **API Rate Limits**: Implements retry logic with exponential backoff
- **Network Timeouts**: Configurable timeouts with retry attempts
- **Data Validation**: Validates date formats and required parameters
- **Partial Failures**: Continues processing even if some repositories fail

## Examples

### Example 1: Basic Team Review
```bash
# Collect all commits from your team for the past month
python github_commit_collector.py myorg --since 2025-01-01
```

### Example 2: Individual Developer Analysis
```bash
# Get detailed statistics for a specific developer
python github_commit_collector.py myorg --author "john.doe" --stats --all-branches
```

### Example 3: Release Preparation
```bash
# Collect commits for release notes (excluding merge commits)
python github_commit_collector.py myorg --since 2025-01-01 --until 2025-01-31 --no-merge
```

### Example 4: Code Review Analysis
```bash
# Analyze largest commits for code review
python github_commit_collector.py myorg --stats --output large_commits.csv
```

## Troubleshooting

### Common Issues

1. **GitHub CLI Not Found**
   ```
   Error: GitHub CLI (gh) is not installed or not authenticated
   ```
   **Solution**: Install GitHub CLI and run `gh auth login`

2. **Rate Limiting**
   ```
   Error: API rate limit exceeded
   ```
   **Solution**: Wait and retry, or reduce `--batch-size` and `--max-workers`

3. **Invalid Date Format**
   ```
   Error: Invalid --since date format
   ```
   **Solution**: Use ISO format like `2025-01-01T00:00:00Z`

4. **No Commits Found**
   ```
   Warning: No commits found matching the criteria
   ```
   **Solution**: Check date range, author filter, or organization name

### Debug Mode

Run with `--verbose` flag to see detailed logging:
```bash
python github_commit_collector.py myorg --verbose
```

## Contributing

This is a clean, modular codebase designed for easy extension:

- Add new filters in `data_processor.py`
- Extend GitHub API functionality in `github_client.py`
- Add configuration options in `config.py`
- Enhance the CLI interface in `github_commit_collector.py`

## License

This project is provided as-is for educational and internal use purposes.

## Migration from Old Scripts

If you're upgrading from the old collection of scripts, this new program replaces:
- `get_commits.py` → Basic commit collection
- `get_commits_optimized.py` → Parallel processing
- `get_all_commits.py` → All branches support
- `get_commits_with_stats.py` → Statistics collection
- `filter_my_commits.py` → Author filtering
- `add_stats_to_my_commits.py` → Statistics enhancement

The new program combines all functionality into a single, clean interface with improved error handling and performance.