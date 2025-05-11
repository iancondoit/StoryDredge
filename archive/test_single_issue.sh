#!/bin/bash
# test_single_issue.sh - Test processing a single San Antonio Express News issue

# Set environment
source .venv/bin/activate
WORKSPACE_DIR=$(pwd)
LOG_DIR="$WORKSPACE_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/single_issue_test_${TIMESTAMP}.log"

# Use a known good date
TEST_DATE="1977-08-14"
echo "Testing single issue processing for $TEST_DATE" | tee -a "$LOG_FILE"

# Create a temporary date file
echo $TEST_DATE > test_date.txt

# Process the single issue
echo "Processing test issue..." | tee -a "$LOG_FILE"
python scripts/process_high_confidence.py \
  --date-file test_date.txt \
  --batch-size 10 \
  --max-workers 3 \
  --max-articles 50 | tee -a "$LOG_FILE"

# Check if the classified directory has content
CLASSIFIED_DIR="output/classified/$TEST_DATE"
if [ -d "$CLASSIFIED_DIR" ]; then
  FILE_COUNT=$(find "$CLASSIFIED_DIR" -type f -name "*.json" | wc -l)
  echo "Found $FILE_COUNT classified article files for $TEST_DATE" | tee -a "$LOG_FILE"
else
  echo "ERROR: No classified directory found for $TEST_DATE" | tee -a "$LOG_FILE"
  exit 1
fi

# Create the hsa-ready directory structure
YEAR=$(echo $TEST_DATE | cut -d'-' -f1)
MONTH=$(echo $TEST_DATE | cut -d'-' -f2)
DAY=$(echo $TEST_DATE | cut -d'-' -f3)
HSA_READY_DIR="output/hsa-ready/$YEAR/$MONTH/$DAY"
mkdir -p "$HSA_READY_DIR"

# Copy the classified files to the hsa-ready structure
for FILE in "$CLASSIFIED_DIR"/*.json; do
  if [ -f "$FILE" ] && [[ "$FILE" != *"report-"* ]]; then
    FILENAME=$(basename "$FILE")
    CLEANED_NAME="${TEST_DATE}--${FILENAME#*--}"
    cp "$FILE" "$HSA_READY_DIR/$CLEANED_NAME"
  fi
done

# Check the hsa-ready directory
HSA_COUNT=$(find "$HSA_READY_DIR" -type f -name "*.json" | wc -l)
echo "Copied $HSA_COUNT articles to hsa-ready structure at $HSA_READY_DIR" | tee -a "$LOG_FILE"

# Clean up
rm test_date.txt

echo "Test completed at $(date)" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" 