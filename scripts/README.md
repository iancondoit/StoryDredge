# StoryDredge Processing Pipeline

This document outlines the complete processing pipeline for StoryDredge to convert newspaper archives into clean, structured data for downstream use in Human Story Atlas (HSA).

## Processing Steps

The StoryDredge pipeline consists of the following sequential steps:

1. **Fetch OCR** - Retrieve OCR'd text from newspaper archive sources
2. **Clean Text** - Remove artifacts and normalize text from the OCR process
3. **Split Articles** - Segment the newspaper text into individual articles
4. **Classify with OpenAI** - Use AI to extract structured metadata from articles
5. **Filter & Sanitize** - Standardize formatting and organize directory structure
6. **HSA-Ready Output** - Final filtering and preparation for HSA ingestion

## Pipeline Scripts

### 1-4. Initial Processing Scripts
The scripts for the initial steps are in the main StoryDredge repository.

### 5. Filter & Sanitize (`migrate_and_sanitize.py`)
This script:
- Migrates articles to a YYYY/MM/DD directory structure
- Sanitizes article text (removes excess line breaks, weird characters, normalizes punctuation)
- Creates a clean, consistent format for all articles

### 6. HSA-Ready Output (`filter_and_finalize.py`)
This script:
- Filters out unsuitable articles based on criteria
  - Excludes articles with section type "ad", "classified", or "unknown"
  - Excludes articles with missing headline or body
  - Excludes articles with low-quality content (too short, too many symbols, etc.)
- Applies final sanitization if needed
- Organizes content into dedicated HSA-ready directory structure
- Updates index.json with statistics for each processed issue

## Directory Structure

```
storydredge/
├── output/
│   ├── classified/          # Classified articles (raw)
│   │   └── YYYY/MM/DD/      # Organized by date
│   ├── hsa-ready/           # Articles ready for HSA consumption
│   │   └── YYYY/MM/DD/      # Organized by date
│   ├── rejected/            # Articles that failed filtering rules
│   │   └── YYYY/MM/DD/      # Organized by date
│   └── index.json           # Statistics for each issue
└── scripts/                 # Processing pipeline scripts
```

## Usage

To process a new newspaper issue through the entire pipeline:

1. Run the initial OCR and classification steps
2. Run the sanitization and organization step:
```
python migrate_and_sanitize.py
```
3. Run the HSA filtering and finalization step:
```
python scripts/filter_and_finalize.py
```

After these steps, HSA-ready articles will be available in the `output/hsa-ready/` directory with the appropriate structure. 