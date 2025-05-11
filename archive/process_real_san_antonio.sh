#!/bin/bash
# process_real_san_antonio.sh - Process 50 real San Antonio Express News issues using the proper pipeline
# This script uses the search_archive.py results with verified Archive.org issues

# Set environment
source .venv/bin/activate
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/real_san_antonio_${TIMESTAMP}.log"

echo "=============================================================" | tee -a "$LOG_FILE"
echo "Starting batch processing of 50 real San Antonio Express-News issues" | tee -a "$LOG_FILE"
echo "Start time: $(date)" | tee -a "$LOG_FILE"
echo "=============================================================" | tee -a "$LOG_FILE"

# We've already searched for the issues using search_archive.py
# and saved the results to san_antonio_actual_issues.json

# The search verified that all 50 issues have OCR text available
echo "Using 50 verified San Antonio Express News issues from Archive.org" | tee -a "$LOG_FILE"
echo "Issues found with search_archive.py and saved to san_antonio_actual_issues.json" | tee -a "$LOG_FILE"

# Process only a subset initially to validate
echo "Processing first 10 issues to validate process..." | tee -a "$LOG_FILE"
python -c "
import json
import sys
try:
    # Load all issues
    with open('san_antonio_actual_issues.json', 'r') as f:
        all_issues = json.load(f)
    
    # Take the first 10
    subset_issues = all_issues[:10]
    
    # Save to a subset file
    with open('sa_test_issues.json', 'w') as f:
        json.dump(subset_issues, f, indent=2)
    
    print(f'Successfully extracted first 10 issues to sa_test_issues.json')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" | tee -a "$LOG_FILE"

# Run the batch process with appropriate settings
echo "Processing first 10 issues..." | tee -a "$LOG_FILE"
python scripts/batch_process.py \
  --issues sa_test_issues.json \
  --skip-existing \
  --max-articles 100 2>&1 | tee -a "$LOG_FILE"

# Count the processed articles in hsa-ready for the first 10 issues
echo "Counting processed articles in hsa-ready directory for first 10 issues..." | tee -a "$LOG_FILE"
python -c "
import os
from pathlib import Path

hsa_ready_dir = Path('output/hsa-ready')
year_dirs = [d for d in hsa_ready_dir.iterdir() if d.is_dir()]

total_issues = 0
total_articles = 0

for year_dir in year_dirs:
    for month_dir in year_dir.iterdir():
        if month_dir.is_dir():
            for day_dir in month_dir.iterdir():
                if day_dir.is_dir():
                    article_files = list(day_dir.glob('*.json'))
                    if article_files:
                        total_issues += 1
                        total_articles += len(article_files)
                        print(f'Issue {year_dir.name}-{month_dir.name}-{day_dir.name}: {len(article_files)} articles')

print(f'Total: {total_issues} issues with {total_articles} articles processed')
" | tee -a "$LOG_FILE"

echo "First 10 issues completed. Starting full batch processing..." | tee -a "$LOG_FILE"

# Process all 50 issues (continuing from where we left off due to skip-existing)
echo "Processing all 50 issues..." | tee -a "$LOG_FILE"
python scripts/batch_process.py \
  --issues san_antonio_actual_issues.json \
  --skip-existing \
  --max-articles 100 2>&1 | tee -a "$LOG_FILE"

echo "=============================================================" | tee -a "$LOG_FILE"
echo "Batch processing completed" | tee -a "$LOG_FILE"
echo "End time: $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=============================================================" | tee -a "$LOG_FILE"

# Final count of all processed articles
echo "Counting final processed articles in hsa-ready directory..." | tee -a "$LOG_FILE"
python -c "
import os
from pathlib import Path

hsa_ready_dir = Path('output/hsa-ready')
year_dirs = [d for d in hsa_ready_dir.iterdir() if d.is_dir()]

total_issues = 0
total_articles = 0

for year_dir in year_dirs:
    for month_dir in year_dir.iterdir():
        if month_dir.is_dir():
            for day_dir in month_dir.iterdir():
                if day_dir.is_dir():
                    article_files = list(day_dir.glob('*.json'))
                    if article_files:
                        total_issues += 1
                        total_articles += len(article_files)
                        print(f'Issue {year_dir.name}-{month_dir.name}-{day_dir.name}: {len(article_files)} articles')

print(f'Final total: {total_issues} issues with {total_articles} articles processed')
" | tee -a "$LOG_FILE" 