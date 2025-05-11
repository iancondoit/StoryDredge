# Batch Processing with StoryDredge

This document explains how to use the batch processing functionality to process multiple newspaper issues efficiently.

## Overview

The batch processing script (`batch_process.py`) allows you to:

1. Process multiple newspaper issues from different publications and time periods
2. Track processing metrics for each issue (time, article counts)
3. Generate comparative reports across issues and publications

## Usage

### Basic Usage

```bash
python scripts/batch_process.py --issues data/sample_issues.json
```

### Options

- `--issues`: Path to JSON file with issue definitions (required)
- `--max-articles`: Limit processing to X articles per issue (default: 0 = all)
- `--skip-fetch`: Skip fetching if raw files already exist
- `--skip-existing`: Skip issues that have already been processed

### Example

```bash
# Process all sample issues, limiting to 100 articles each
python scripts/batch_process.py --issues data/sample_issues.json --max-articles 100

# Skip already processed issues
python scripts/batch_process.py --issues data/sample_issues.json --skip-existing
```

## Issues JSON Format

The issues JSON file should contain an array of objects with:

- `archive_id`: Archive.org identifier (e.g., "san-antonio-express-news-1977-08-14")
- `date`: Date in YYYY-MM-DD format
- `publication`: Publication name

Example:
```json
[
  {
    "archive_id": "san-antonio-express-news-1977-08-14",
    "date": "1977-08-14",
    "publication": "San Antonio Express-News"
  },
  {
    "archive_id": "chicago-tribune-1925-10-15",
    "date": "1925-10-15",
    "publication": "Chicago Tribune"
  }
]
```

## Output Metrics

After processing, metrics are saved to `output/batch_metrics.json` with:

- Processing time for each step per issue
- Article counts (total, news, ads, HSA-ready)
- Aggregated statistics
- Publication-specific aggregates

## Troubleshooting

- Make sure your OpenAI API key is correctly set in the `.env` file
- Check that all required scripts exist and work individually
- For issues downloading from archive.org, make sure the archive_id is correct and publicly accessible

## Note About Archive.org IDs

The Archive.org identifiers in `sample_issues.json` are examples and may not match actual archive.org items. You may need to:

1. Visit archive.org
2. Search for the newspaper and date
3. Note the identifier in the URL
4. Update your issues.json file with accurate identifiers 