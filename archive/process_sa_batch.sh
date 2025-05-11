#!/bin/bash
# process_sa_batch.sh - Process 50 San Antonio Express News issues from archive.org
# This script:
# 1. Searches archive.org for issues
# 2. Downloads and processes them
# 3. Ensures they're formatted in the hsa-ready directory structure

# Set environment
source .venv/bin/activate
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/sa_batch_${TIMESTAMP}.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "Starting San Antonio Express News batch processing at $(date)" | tee -a "$LOG_FILE"

# STEP 1: Search for San Antonio Express News issues on archive.org
echo "Searching for San Antonio Express News issues on archive.org..." | tee -a "$LOG_FILE"
python search_archive.py \
  --query "San Antonio Express News" \
  --start-date 1977-01-01 \
  --end-date 1977-12-31 \
  --limit 50 \
  --output san_antonio_issues_search.json | tee -a "$LOG_FILE"

# STEP 2: Extract dates from the search results
echo "Extracting dates from search results..." | tee -a "$LOG_FILE"
python -c "
import json
import sys
try:
    with open('san_antonio_issues_search.json', 'r') as f:
        issues = json.load(f)
    
    dates = [issue.get('date') for issue in issues if issue.get('date')]
    
    # Sort dates
    dates.sort()
    
    # Limit to 50 issues
    dates = dates[:50]
    
    # Save dates to file
    with open('sa_dates.txt', 'w') as f:
        f.write('\n'.join(dates))
    
    print(f'Successfully extracted {len(dates)} dates')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" | tee -a "$LOG_FILE"

# STEP 3: Create batch processing config
echo "Setting up batch processing..." | tee -a "$LOG_FILE"

# Determine optimal batch settings based on available resources
# Adjust these settings based on your machine and API rate limits
BATCH_SIZE=10        # Number of articles to process in each API call
MAX_WORKERS=4        # Number of concurrent API calls
PARALLEL_ISSUES=3    # Number of issues to process in parallel
MAX_ARTICLES=50      # Maximum number of articles to identify per issue

# STEP 4: Process the issues in batches
echo "Processing issues in batches..." | tee -a "$LOG_FILE"
python scripts/process_high_confidence.py \
  --date-file sa_dates.txt \
  --batch-size $BATCH_SIZE \
  --max-workers $MAX_WORKERS \
  --parallel-issues $PARALLEL_ISSUES \
  --max-articles $MAX_ARTICLES | tee -a "$LOG_FILE"

# STEP 5: Ensure all processed articles are in the hsa-ready directory structure
echo "Moving processed articles to hsa-ready directory structure..." | tee -a "$LOG_FILE"

# Create the migrate_to_hsa_ready.py script if it doesn't exist
if [ ! -f "migrate_to_hsa_ready.py" ]; then
cat > migrate_to_hsa_ready.py << 'EOF'
#!/usr/bin/env python3
"""
migrate_to_hsa_ready.py - Move processed articles to the hsa-ready directory structure
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

def migrate_articles():
    """Migrate processed articles to hsa-ready structure"""
    
    workspace_dir = Path().resolve()
    output_dir = workspace_dir / "output"
    classified_dir = output_dir / "classified"
    hsa_ready_dir = output_dir / "hsa-ready"
    
    # Ensure hsa-ready directory exists
    hsa_ready_dir.mkdir(exist_ok=True, parents=True)
    
    # Get list of dates from date file
    date_file = workspace_dir / "sa_dates.txt"
    processed_dates = []
    
    if date_file.exists():
        with open(date_file, 'r') as f:
            processed_dates = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(processed_dates)} dates to migrate")
    
    # Process each date
    for date_str in processed_dates:
        try:
            year, month, day = date_str.split('-')
            
            # Source directory with classified articles
            source_dir = classified_dir / date_str
            
            if not source_dir.exists():
                print(f"No classified articles found for {date_str}, skipping")
                continue
                
            # Destination directory in hsa-ready format
            dest_dir = hsa_ready_dir / year / month / day
            dest_dir.mkdir(exist_ok=True, parents=True)
            
            # Get all JSON files in the source directory
            json_files = list(source_dir.glob("*.json"))
            article_files = [f for f in json_files if f.name != f"report-{date_str}.json"]
            
            print(f"Processing {date_str}: {len(article_files)} articles")
            
            # Process each article file
            for article_file in article_files:
                try:
                    with open(article_file, 'r') as f:
                        article = json.load(f)
                    
                    # Create standardized filename
                    filename = f"{date_str}--{article_file.stem.split('--')[-1]}.json"
                    dest_file = dest_dir / filename
                    
                    # Copy file to destination
                    shutil.copy2(article_file, dest_file)
                    
                except Exception as e:
                    print(f"Error processing article {article_file}: {e}")
            
            print(f"Successfully migrated articles for {date_str}")
            
        except Exception as e:
            print(f"Error processing date {date_str}: {e}")
    
    print("Migration complete!")

if __name__ == "__main__":
    migrate_articles()
EOF

chmod +x migrate_to_hsa_ready.py
fi

# Run the migration script
python migrate_to_hsa_ready.py | tee -a "$LOG_FILE"

# STEP 6: Verify results
echo "Verifying results..." | tee -a "$LOG_FILE"

# Count number of processed issues in hsa-ready structure
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

echo "Processing completed at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" 