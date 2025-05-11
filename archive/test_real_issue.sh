#!/bin/bash
# test_real_issue.sh - Test processing a single verified San Antonio Express News issue

# Set environment
source .venv/bin/activate
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/single_real_issue_test_${TIMESTAMP}.log"

# We'll use a known available issue from our search results
TEST_ID="san-antonio-express-news-1977-01-01"
TEST_DATE="1977-01-01"

echo "Testing single issue processing for archive ID: $TEST_ID, date: $TEST_DATE" | tee -a "$LOG_FILE"
echo "Start time: $(date)" | tee -a "$LOG_FILE"

# Create a temporary test JSON file with this single issue
cat > test_real_issue.json << EOF
[
  {
    "archive_id": "$TEST_ID",
    "date": "$TEST_DATE",
    "publication": "San Antonio Express News",
    "title": "San Antonio Express News ($TEST_DATE)",
    "has_ocr": true
  }
]
EOF

# Process the single issue
echo "Processing test issue using batch_process.py..." | tee -a "$LOG_FILE"
python scripts/batch_process.py \
  --issues test_real_issue.json \
  --max-articles 100 2>&1 | tee -a "$LOG_FILE"

# Check if processing created articles in the hsa-ready directory
YEAR=$(echo $TEST_DATE | cut -d'-' -f1)
MONTH=$(echo $TEST_DATE | cut -d'-' -f2)
DAY=$(echo $TEST_DATE | cut -d'-' -f3)
HSA_READY_DIR="output/hsa-ready/$YEAR/$MONTH/$DAY"

if [ -d "$HSA_READY_DIR" ]; then
  HSA_COUNT=$(find "$HSA_READY_DIR" -type f -name "*.json" | wc -l)
  echo "Success! Found $HSA_COUNT articles in hsa-ready structure at $HSA_READY_DIR" | tee -a "$LOG_FILE"
else
  echo "Warning: No hsa-ready directory created for $TEST_DATE" | tee -a "$LOG_FILE"
fi

# Clean up
rm test_real_issue.json

echo "Test completed at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE" 