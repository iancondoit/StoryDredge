#!/bin/bash
# fix_all_archives.sh - Test the improved pipeline with a single issue

set -e  # Exit on any error

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated"
fi

# Set up variables
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/fix_validation_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Function to test a single issue
test_issue() {
    local archive_id=$1
    local date_str=$2
    
    log "Testing pipeline for issue: $archive_id ($date_str)"
    
    # Step 1: Fetch the issue
    log "Fetching issue..."
    python scripts/fetch_issue.py "$archive_id" || {
        log "ERROR: Failed to fetch issue"
        return 1
    }
    
    # Step 2: Clean the text
    log "Cleaning text..."
    python scripts/clean_text.py "$date_str" || {
        log "ERROR: Failed to clean text"
        return 1
    }
    
    # Step 3: Split into articles
    log "Splitting into articles..."
    python scripts/split_articles.py "$date_str" --aggressive-mode || {
        log "ERROR: Failed to split articles"
        return 1
    }
    
    # Step 4: Pre-filter for news articles
    log "Pre-filtering news articles..."
    python scripts/prefilter_news.py "$date_str" || {
        log "ERROR: Failed to pre-filter news"
        return 1
    }
    
    # Step 5: Run article classification 
    log "Classifying articles..."
    news_file_list="output/news_files_${date_str}.txt"
    if [ -f "$news_file_list" ]; then
        python scripts/classify_articles.py "$date_str" --file-list="$news_file_list" || {
            log "ERROR: Failed to classify articles"
            return 1
        }
    else
        log "WARNING: No news files list found, using all articles..."
        python scripts/classify_articles.py "$date_str" || {
            log "ERROR: Failed to classify articles"
            return 1
        }
    fi
    
    # Step 6: Migrate and sanitize
    log "Migrating and sanitizing articles..."
    python scripts/migrate_and_sanitize.py || {
        log "ERROR: Failed to migrate and sanitize"
        return 1
    }
    
    # Step 7: Filter and finalize
    log "Filtering and finalizing for HSA..."
    python scripts/filter_and_finalize.py || {
        log "ERROR: Failed to filter and finalize"
        return 1
    }
    
    # Step 8: Run additional cleanup
    log "Running additional ad cleanup..."
    python cleanup_hsa_ready.py || {
        log "ERROR: Failed to run additional cleanup"
        return 1
    }
    
    log "Pipeline test SUCCESSFUL for $archive_id ($date_str)"
    return 0
}

# Start the test
log "Starting pipeline validation test"

# Test a single known good issue
log "Testing single issue processing"
test_issue "san-antonio-express-news-1974-04-13" "1974-04-13"

# Count the results
HSA_READY_COUNT=$(find output/hsa-ready/1974/04/13 -name "*.json" | wc -l | tr -d '[:space:]')
log "HSA-ready articles for test issue: $HSA_READY_COUNT"

if [ "$HSA_READY_COUNT" -gt 0 ]; then
    log "Single issue test PASSED - found $HSA_READY_COUNT articles"
    
    # Test with a small batch of issues
    log "Testing batch processing with 3 issues"
    
    # Create a temporary JSON file for batch processing
    TEMP_ISSUES_FILE="temp_test_issues.json"
    cat > "$TEMP_ISSUES_FILE" << EOF
[
    {
        "archive_id": "san-antonio-express-news-1974-04-13",
        "date": "1974-04-13",
        "publication": "San Antonio Express-News"
    },
    {
        "archive_id": "san-antonio-express-news-1974-04-14",
        "date": "1974-04-14",
        "publication": "San Antonio Express-News"
    },
    {
        "archive_id": "san-antonio-express-news-1975-01-01",
        "date": "1975-01-01",
        "publication": "San Antonio Express-News"
    }
]
EOF
    
    # Run the improved batch process with the test issues
    log "Running improved batch process..."
    ./improved_batch_process.py --issues "$TEMP_ISSUES_FILE" --aggressive-splitting --extra-ad-filtering --skip-existing || {
        log "ERROR: Batch processing failed"
        rm "$TEMP_ISSUES_FILE"
        exit 1
    }
    
    # Clean up the temporary file
    rm "$TEMP_ISSUES_FILE"
    
    # Count the results for all issues
    TOTAL_ARTICLES=$(find output/hsa-ready -name "*.json" | wc -l | tr -d '[:space:]')
    log "Total HSA-ready articles across all issues: $TOTAL_ARTICLES"
    
    log "Pipeline validation COMPLETE - All tests passed"
    log "You can now safely run the full batch process with 50 issues"
    
    # Display command to run full batch
    echo ""
    echo "To process all 50 issues, run:"
    echo "./improved_batch_process.py --issues san_antonio_issues.json --aggressive-splitting --extra-ad-filtering"
    echo ""
else
    log "Single issue test FAILED - no articles found in HSA-ready directory"
    exit 1
fi

exit 0 