# StoryDredge

StoryDredge is a preprocessing pipeline for digitized newspapers. It pulls OCRed newspaper issues from Archive.org, cleans and formats the raw OCR output into readable article segments, and outputs each article as structured JSON for use in downstream systems like Human Story Atlas (HSA).

**Current Version:** 0.2.5

## Overview

StoryDredge automatically processes digitized newspapers through several steps:

1. Fetch OCR text from Archive.org
2. Clean and normalize the text
3. Split the cleaned text into individual articles
4. Classify articles and extract metadata using OpenAI
5. Sanitize article content and organize directory structure
6. Filter articles based on quality metrics and prepare HSA-ready output

## Project Structure

```
storydredge/
├── archive/                # Archive.org downloads
│   ├── raw/                # Raw OCR files (.txt)
│   └── processed/          # Cleaned OCR files (.txt)
├── output/
│   ├── articles/           # Initial article JSONs (from splitting)
│   ├── classified/         # Articles with OpenAI metadata
│   │   └── YYYY/MM/DD/     # Organized by date
│   ├── hsa-ready/          # Articles ready for HSA consumption
│   │   └── YYYY/MM/DD/     # Organized by date
│   ├── rejected/           # Articles that failed quality filters
│   │   └── YYYY/MM/DD/     # Organized by date
│   └── index.json          # Statistics for each issue
├── scripts/                # Processing pipeline scripts
│   ├── fetch_issue.py      # Downloads and extracts OCR from archive.org
│   ├── clean_text.py       # Normalizes and prepares article text
│   ├── split_articles.py   # Splits OCR text into articles
│   ├── classify_articles.py# Uses OpenAI to extract metadata
│   ├── migrate_and_sanitize.py # Sanitizes and organizes articles
│   ├── filter_and_finalize.py  # Final HSA preparation and filtering
│   └── *.py                # Other utility scripts and tests
├── tests/                  # Unit and integration tests
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (OpenAI API key, etc.)
```

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package installer)
- OpenAI API key (for classification step)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/storydredge.git
   cd storydredge
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Create a `.env` file in the project root
   - Add your OpenAI API key: `OPENAI_API_KEY=your_api_key`
   - Set other configuration options as needed

## Processing Pipeline

### Phase 1: Article Extraction

```bash
# Step 1: Fetch OCR Source
python scripts/fetch_issue.py san-antonio-express-news-1977-08-14

# Step 2: Clean & Normalize OCR
python scripts/clean_text.py 1977-08-14

# Step 3: Split Into Articles
python scripts/split_articles.py 1977-08-14
```

### Phase 2: Classification & Metadata Extraction

```bash
# Step 4: Classify Articles with OpenAI
python scripts/classify_articles.py 1977-08-14

# Step 5: Sanitize & Organize Directory Structure
python scripts/migrate_and_sanitize.py

# Step 6: Filter & Prepare HSA-Ready Articles
python scripts/filter_and_finalize.py
```

### Running Tests

```bash
# Run all tests
pytest 

# Run specific test file
python scripts/test_filter_finalize.py
```

## Output Formats

### HSA-Ready Article Format

After processing through all pipeline steps, articles will have this structure:

```json
{
  "headline": "Mayor Resigns Amid Pressure",
  "byline": "By JAMES WATKINS, Staff Writer",
  "dateline": "SAN ANTONIO, AUG. 14 —",
  "body": "Mayor John Smith announced his resignation...",
  "section": "news",
  "tags": ["politics", "resignation", "scandal"],
  "timestamp": "1977-08-14",
  "publication": "San Antonio Express-News",
  "source_issue": "san-antonio-express-news-1977-08-14",
  "source_url": "https://archive.org/details/san-antonio-express-news-1977-08-14"
}
```

## Statistics & Reporting

The pipeline generates statistics in `output/index.json`:

```json
{
  "1977-08-14": {
    "hsa_ready_count": 57,
    "rejected_count": 620
  }
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.