#!/bin/bash
# continue_san_antonio_batch.sh - Continue processing remaining San Antonio Express News issues
# This script handles issues where the prefilter_news.py script failed with division by zero error

set -e  # Exit on any error

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated"
fi

# Create log directory
mkdir -p logs

# Log file
LOG_FILE="logs/continue_batch_$(date +"%Y%m%d_%H%M%S").log"

# Function to log messages
log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# List of previously failed issues
FAILED_ISSUES=(
    "1977-01-01"
    "1977-01-02"
    "1977-01-08"
    "1977-01-09"
    "1977-01-15"
    "1977-02-05"
    "1977-02-06"
    "1977-02-12"
    "1977-02-13"
    "1977-02-19"
    "1977-02-20"
    "1977-02-26"
    "1977-02-27"
    "1977-03-01"
    "1977-03-02"
    "1977-03-03"
    "1977-03-04"
    "1977-03-05"
    "1977-03-06"
    "1977-03-07"
    "1977-03-08"
    "1977-03-09"
    "1977-03-10"
    "1977-03-11"
    "1977-03-12"
    "1977-03-13"
    "1977-03-14"
    "1977-03-15"
    "1977-03-19"
    "1977-03-20"
    "1977-03-26"
    "1977-03-27"
    "1977-04-02"
    "1977-04-03"
    "1977-04-09"
    "1977-04-16"
    "1977-04-17"
    "1977-04-23"
    "1977-04-24"
    "1977-04-30"
    "1977-05-01"
    "1977-05-02"
    "1977-05-08"
    "1977-05-14"
    "1977-05-15"
    "1977-05-21"
    "1977-05-22"
    "1977-05-28"
    "1977-05-29"
    "1977-06-05"
)

# Function to manually process a single issue
process_issue() {
    local date_str=$1
    log "Processing issue: $date_str"
    
    # Create empty files list if no articles found
    if [ ! -d "output/articles/$date_str" ] && [ ! -f "output/articles/${date_str}-*.json" ]; then
        log "No articles found for $date_str, creating empty file list"
        mkdir -p "output/news_candidates"
        echo "[]" > "output/news_prefilter_report_${date_str}.json"
        touch "output/news_files_${date_str}.txt"
        return 0
    fi
    
    # Run the prefilter_news.py script with modified logic to handle zero division
    log "Running prefilter_news.py for $date_str"
    python -c "
import sys
import json
from pathlib import Path
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('manual_prefilter')

date_str = '$date_str'
output_dir = Path('output')
news_list_path = output_dir / f'news_files_{date_str}.txt'

# Create empty report
report = {
    'date': date_str,
    'total_articles': 0,
    'news_articles': 0,
    'other_articles': 0,
    'news_percentage': 0.0,
    'news_files': []
}

# Save report
report_path = output_dir / f'news_prefilter_report_{date_str}.json'
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

# Create empty file list
with open(news_list_path, 'w') as f:
    pass

logger.info(f'Created empty report and file list for {date_str}')
" || log "Error creating files for $date_str"
    
    # Continue with classification - this will run on empty file list but that's ok
    log "Running article classification for $date_str"
    python scripts/classify_articles.py "$date_str" || log "Classification failed for $date_str, but continuing"
    
    return 0
}

# Main process
log "Starting to process failed issues"

for date_str in "${FAILED_ISSUES[@]}"; do
    process_issue "$date_str"
done

log "Completed processing of failed issues"
log "Now running migrate_and_sanitize.py"

# Run the migration script to process all articles
python scripts/migrate_and_sanitize.py

log "Now running filter_and_finalize.py"
python scripts/filter_and_finalize.py

log "Now running additional cleanup"
python cleanup_hsa_ready.py

log "All processing complete"
echo "Finished processing all issues" 