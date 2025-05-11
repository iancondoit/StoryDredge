#!/bin/bash
# efficient_pipeline.sh - Run the StoryDredge pipeline with ad prefiltering
# Usage: ./efficient_pipeline.sh YYYY-MM-DD [max_articles]

set -e  # Exit on errors

if [ $# -lt 1 ]; then
  echo "Usage: ./efficient_pipeline.sh YYYY-MM-DD [max_articles]"
  echo "Example: ./efficient_pipeline.sh 1977-08-14"
  echo "Example: ./efficient_pipeline.sh 1977-08-14 100"
  exit 1
fi

DATE=$1
MAX_ARTICLES=${2:-0}  # Default to 0 (process all)

# Base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

echo "🔍 StoryDredge Efficient Pipeline for $DATE"
echo "============================================"

# Step 1: Fetch OCR Source (if not already done)
if [ ! -f "archive/raw/$DATE.txt" ]; then
  echo "Step 1: Fetching OCR source for $DATE..."
  python scripts/fetch_issue.py "$DATE"
else
  echo "Step 1: OCR source already exists for $DATE, skipping download."
fi

# Step 2: Clean & Normalize OCR
if [ ! -f "archive/processed/$DATE-clean.txt" ]; then
  echo "Step 2: Cleaning and normalizing OCR text..."
  python scripts/clean_text.py "$DATE"
else
  echo "Step 2: Cleaned OCR already exists for $DATE, skipping cleaning."
fi

# Step 3: Split Into Articles
echo "Step 3: Splitting into individual articles..."
python scripts/split_articles.py "$DATE"

# Count articles
ARTICLE_COUNT=$(ls output/articles/$DATE-*.json 2>/dev/null | wc -l | tr -d ' ')
echo "📄 Found $ARTICLE_COUNT total articles"

# Apply max articles limit if specified
if [ $MAX_ARTICLES -gt 0 ] && [ $ARTICLE_COUNT -gt $MAX_ARTICLES ]; then
  echo "⚠️ Limiting to $MAX_ARTICLES articles for processing"
  # Create a temp directory for subset of articles
  mkdir -p output/articles_subset
  # Copy a subset of articles
  ls output/articles/$DATE-*.json | head -n $MAX_ARTICLES | xargs -I{} cp {} output/articles_subset/
  # Use this subset for the rest of processing
  ARTICLE_COUNT=$MAX_ARTICLES
  echo "📄 Working with $ARTICLE_COUNT articles"
fi

# Step 4: Pre-filter to identify ads
echo "Step 4: Pre-filtering to identify ads vs. news content..."
python scripts/prefilter_ads.py "$DATE"

# Read prefilter stats
if [ -f "output/prefilter_report_$DATE.json" ]; then
  NEWS_COUNT=$(grep -o '"news_articles": [0-9]*' "output/prefilter_report_$DATE.json" | grep -o '[0-9]*')
  AD_COUNT=$(grep -o '"ad_articles": [0-9]*' "output/prefilter_report_$DATE.json" | grep -o '[0-9]*')
  echo "🔍 Pre-filter identified $NEWS_COUNT news articles and $AD_COUNT advertisements"
  echo "💰 This will save approximately $(echo "$AD_COUNT * 0.002" | bc -l | xargs printf "%.2f") dollars in OpenAI API costs"
else
  echo "⚠️ Pre-filter report not found, continuing with all articles"
  NEWS_COUNT=$ARTICLE_COUNT
fi

# Step 5: Classify only news content with OpenAI
echo "Step 5: Classifying news content with OpenAI..."
if [ -f "output/news_files_$DATE.txt" ]; then
  python scripts/classify_articles.py "$DATE" --file-list="output/news_files_$DATE.txt"
else
  echo "⚠️ News files list not found, falling back to processing all articles"
  python scripts/classify_articles.py "$DATE"
fi

# Step 6: Migrate & Sanitize
echo "Step 6: Sanitizing and organizing content..."
python scripts/migrate_and_sanitize.py

# Step 7: Filter & Prepare HSA-Ready Content
if [ -f "scripts/filter_and_finalize.py" ]; then
  echo "Step 7: Preparing HSA-ready content..."
  python scripts/filter_and_finalize.py
else
  echo "⚠️ filter_and_finalize.py not found, skipping final preparation"
fi

# Final stats
HSA_READY_COUNT=$(ls output/hsa-ready/$DATE/*.json 2>/dev/null | wc -l | tr -d ' ')
if [ -z "$HSA_READY_COUNT" ]; then
  HSA_READY_COUNT=0
fi

echo ""
echo "✅ Pipeline complete!"
echo "============================================"
echo "📊 Statistics for $DATE:"
echo "   Total Articles Found: $ARTICLE_COUNT"
echo "   Identified as News: $NEWS_COUNT"
echo "   Identified as Ads: $AD_COUNT"
echo "   HSA-Ready Articles: $HSA_READY_COUNT"
echo ""
echo "📁 Output directories:"
echo "   - Articles: output/articles/"
echo "   - Classified: output/classified/"
echo "   - HSA-Ready: output/hsa-ready/$DATE/"
echo "   - Ads: output/ads/"

exit 0 