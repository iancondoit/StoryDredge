#!/bin/bash
# process_remaining_sa_issues.sh - Process remaining San Antonio Express News issues with improved techniques
# This script uses the updated split_articles.py with aggressive mode to handle issues with poor OCR quality

# Set environment
source .venv/bin/activate
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/sa_batch_retry_${TIMESTAMP}.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "Starting improved San Antonio Express News batch processing at $(date)" | tee -a "$LOG_FILE"

# Analyze which issues failed in the previous run
echo "Extracting issues from search results..." | tee -a "$LOG_FILE"

# Read the original search results to get all issue IDs and dates
python -c "
import json
import sys
from pathlib import Path

try:
    # Load the search results
    search_file = Path('san_antonio_issues_search.json')
    if not search_file.exists():
        print('Error: san_antonio_issues_search.json not found.')
        sys.exit(1)
        
    with open(search_file, 'r') as f:
        issues = json.load(f)
    
    # Extract archive IDs and dates
    issues_data = []
    for issue in issues:
        if 'archive_id' in issue and 'date' in issue:
            issues_data.append({
                'archive_id': issue['archive_id'],
                'date': issue['date']
            })
    
    # Save to a temporary file
    with open('all_sa_issues.json', 'w') as f:
        json.dump(issues_data, f, indent=2)
    
    print(f'Successfully extracted {len(issues_data)} issues')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" | tee -a "$LOG_FILE"

# Find which issues were successfully processed
python -c "
import json
import sys
from pathlib import Path

try:
    # Load all issues
    with open('all_sa_issues.json', 'r') as f:
        all_issues = json.load(f)
    
    # Check which dates have articles
    articles_dir = Path('output/articles')
    if not articles_dir.exists():
        print('Error: articles directory not found.')
        sys.exit(1)
    
    # Find processed dates
    processed_dates = set()
    for file in articles_dir.glob('????-??-??--*.json'):
        date_str = file.name.split('--')[0]
        processed_dates.add(date_str)
    
    # Identify unprocessed issues
    unprocessed_issues = []
    for issue in all_issues:
        date = issue['date']
        if date not in processed_dates:
            unprocessed_issues.append(issue)
    
    # Save unprocessed issues
    with open('unprocessed_sa_issues.json', 'w') as f:
        json.dump(unprocessed_issues, f, indent=2)
    
    print(f'Found {len(unprocessed_issues)} unprocessed issues out of {len(all_issues)}')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" | tee -a "$LOG_FILE"

# Count unprocessed issues
UNPROCESSED_COUNT=$(python -c "
import json
with open('unprocessed_sa_issues.json', 'r') as f:
    print(len(json.load(f)))
")

echo "Found $UNPROCESSED_COUNT unprocessed issues to process" | tee -a "$LOG_FILE"

if [ "$UNPROCESSED_COUNT" -eq 0 ]; then
    echo "All issues have been processed! Nothing to do." | tee -a "$LOG_FILE"
    exit 0
fi

# Process each unprocessed issue
echo "Starting processing of unprocessed issues..." | tee -a "$LOG_FILE"

# Process each issue one by one with our improved pipeline
python -c "
import json
import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(cmd, description):
    print(f'Running: {description}')
    print(f'Command: {cmd}')
    try:
        subprocess.run(cmd, check=True, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'Error: {e}')
        return False

try:
    # Load unprocessed issues
    with open('unprocessed_sa_issues.json', 'r') as f:
        issues = json.load(f)
    
    success_count = 0
    total_count = len(issues)
    
    for i, issue in enumerate(issues):
        archive_id = issue['archive_id']
        date = issue['date']
        
        print(f'\\n[{i+1}/{total_count}] Processing issue: {date} ({archive_id})')
        
        # Step 1: Fetch the issue
        if not run_command(f'python scripts/fetch_issue.py {archive_id}', 
                         'Fetching issue from archive.org'):
            print(f'Failed to fetch issue: {archive_id}')
            continue
        
        # Step 2: Clean the text
        if not run_command(f'python scripts/clean_text.py {date}',
                         'Cleaning OCR text'):
            print(f'Failed to clean text for issue: {date}')
            continue
        
        # Step 3: Split into articles with aggressive mode
        if not run_command(f'python scripts/split_articles.py {date} --aggressive-mode',
                         'Splitting into articles (aggressive mode)'):
            print(f'Failed to split articles for issue: {date}')
            continue
        
        # Verify articles were created
        articles_dir = Path('output/articles')
        article_count = len(list(articles_dir.glob(f'{date}--*.json')))
        
        if article_count == 0:
            print(f'No articles were created for {date}')
            continue
        
        # Step 4: Pre-filter to find news articles
        if not run_command(f'python scripts/prefilter_news.py {date} --max-articles 50',
                         'Pre-filtering for news articles'):
            print(f'Failed to pre-filter for issue: {date}')
            continue
        
        # Step 5: Classify articles
        news_list_path = f'output/high_confidence_news_{date}.txt'
        if Path(news_list_path).exists():
            if not run_command(f'python scripts/classify_articles.py --file-list {news_list_path} --batch-size 10',
                             'Classifying articles'):
                print(f'Failed to classify articles for issue: {date}')
                continue
        else:
            print(f'No news articles found for {date}, skipping classification')
        
        success_count += 1
        print(f'✅ Successfully processed issue: {date}')
    
    # Final summary
    print(f'\\nProcessing complete: {success_count}/{total_count} issues processed successfully')
    
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" | tee -a "$LOG_FILE"

# Move all processed articles to HSA-ready directory structure
echo "Moving processed articles to HSA-ready directory structure..." | tee -a "$LOG_FILE"
python scripts/migrate_and_sanitize.py || {
    echo "ERROR: Failed to migrate articles to HSA-ready structure" | tee -a "$LOG_FILE"
    exit 1
}

# Filter and finalize for HSA
echo "Filtering and finalizing for HSA" | tee -a "$LOG_FILE"
python scripts/filter_and_finalize.py || {
    echo "ERROR: Failed to filter and finalize for HSA" | tee -a "$LOG_FILE"
    exit 1
}

# Count how many issues/articles were processed
echo "Verifying results..." | tee -a "$LOG_FILE"
python -c "
import os
import json
from pathlib import Path

# Find all issue directories
classified_dir = Path('output/classified')
issues = []
article_count = 0

for year_dir in classified_dir.glob('[0-9][0-9][0-9][0-9]'):
    for month_dir in year_dir.glob('[0-9][0-9]'):
        for day_dir in month_dir.glob('[0-9][0-9]'):
            issue_date = f'{year_dir.name}-{month_dir.name}-{day_dir.name}'
            issue_articles = list(day_dir.glob('*.json'))
            if issue_articles:
                issues.append((issue_date, len(issue_articles)))
                article_count += len(issue_articles)

# Sort by date
issues.sort()

# Display results
for issue_date, count in issues:
    print(f'Issue {issue_date}: {count} articles')

print(f'Total: {len(issues)} issues with {article_count} articles processed')
" | tee -a "$LOG_FILE"

echo "Processing completed at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" 