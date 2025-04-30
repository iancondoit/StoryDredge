# StoryDredge Scripts

This directory contains the core processing scripts for StoryDredge.

## Setup

Before running any scripts, make sure to set up your environment:

1. Copy `.env.sample` to `.env` in the project root directory
2. Fill in your OpenAI API key and other settings
3. Run the setup script to verify your environment:

```bash
python scripts/setup.py
```

## Processing Pipeline

### Single Issue Processing

To process a single newspaper issue:

```bash
# Step 1: Fetch OCR Source
python scripts/fetch_issue.py san-antonio-express-news-1977-08-14

# Step 2: Clean & Normalize OCR
python scripts/clean_text.py 1977-08-14

# Step 3: Split Into Articles
python scripts/split_articles.py 1977-08-14

# Step 4: Pre-filter Ads
python scripts/prefilter_ads.py 1977-08-14

# Step 5: Classify Articles with OpenAI
python scripts/classify_articles.py 1977-08-14 --file-list=output/news_files_1977-08-14.txt

# Step 6: Sanitize & Organize Directory Structure
python scripts/migrate_and_sanitize.py

# Step 7: Filter & Prepare HSA-Ready Articles  
python scripts/filter_and_finalize.py
```

### Batch Processing

For processing multiple issues at once:

1. Create a JSON file with the issues to process (see `data/sample_issues.json` for format)
2. Run the batch processing script:

```bash
# Process all issues in the file
python scripts/batch_process.py --issues=data/sample_issues.json

# Limit to 100 articles per issue (for testing)
python scripts/batch_process.py --issues=data/sample_issues.json --max-articles=100

# Skip issues that have already been processed
python scripts/batch_process.py --issues=data/sample_issues.json --skip-existing

# Skip fetching if raw files already exist
python scripts/batch_process.py --issues=data/sample_issues.json --skip-fetch
```

## Testing

Quick test of the batch processing pipeline:

```bash
python scripts/test_batch.py
```

This will:
1. Create a test issues file if it doesn't exist
2. Run the setup script
3. Process a small batch with limited articles
4. Verify the results

## Directory Structure

After processing, the following directories will contain:

- `archive/raw/` - Raw OCR files from Archive.org
- `archive/processed/` - Cleaned OCR files
- `output/articles/` - Individual article JSONs (from splitting)
- `output/ads/` - Articles identified as advertisements
- `output/classified/` - Articles with OpenAI metadata, organized by date
- `output/hsa-ready/` - Articles ready for HSA consumption
- `output/rejected/` - Articles that failed quality filters

## Script Details

- `setup.py` - Validates environment and creates directories
- `fetch_issue.py` - Downloads OCR from Archive.org
- `clean_text.py` - Normalizes text
- `split_articles.py` - Divides OCR into individual articles
- `prefilter_ads.py` - Identifies obvious advertisements
- `classify_articles.py` - Uses OpenAI to extract metadata
- `migrate_and_sanitize.py` - Organizes by date and cleans content
- `filter_and_finalize.py` - Prepares final output
- `batch_process.py` - Processes multiple issues sequentially
- `test_batch.py` - Tests the batch processing pipeline

## Rate Limiting

The OpenAI API has rate limits. By default, the `classify_articles.py` script is 
configured to limit requests to 20 per minute, but you can adjust this in the `.env` file:

```
OPENAI_RATE_LIMIT=20  # Requests per minute
```

For large batches, this rate limiting prevents API errors and ensures reliable processing.

## Troubleshooting

If you encounter issues:

1. Check that your OpenAI API key is valid
2. Verify all directories exist (run `setup.py`)
3. For archive.org connection issues, try a different issue ID
4. If classification is failing, check API responses in logs

## Analysis

After batch processing, view metrics:

```bash
python scripts/analyze_batch_results.py
```

This generates reports on processing times and article distributions. 