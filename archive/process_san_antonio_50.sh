#!/bin/bash
# process_san_antonio_50.sh - Process 50 San Antonio Express News issues using the proper pipeline

# Set environment
source .venv/bin/activate
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/san_antonio_50_${TIMESTAMP}.log"

echo "=============================================================" | tee -a "$LOG_FILE"
echo "Starting batch processing of 50 San Antonio Express-News issues" | tee -a "$LOG_FILE"
echo "Start time: $(date)" | tee -a "$LOG_FILE"
echo "=============================================================" | tee -a "$LOG_FILE"

# Run the batch process with appropriate settings
# --skip-existing: Skip issues that have already been processed (in case of restart)
# --max-articles 100: Limit to 100 articles per issue to manage processing time
python scripts/batch_process.py \
  --issues data/san_antonio_50.json \
  --skip-existing \
  --max-articles 100 2>&1 | tee -a "$LOG_FILE"

echo "=============================================================" | tee -a "$LOG_FILE"
echo "Batch processing completed" | tee -a "$LOG_FILE"
echo "End time: $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=============================================================" | tee -a "$LOG_FILE"

# Count the processed articles in hsa-ready
echo "Counting processed articles in hsa-ready directory..." | tee -a "$LOG_FILE"
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