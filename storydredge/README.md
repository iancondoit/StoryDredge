# StoryDredge

StoryDredge is a preprocessing pipeline for digitized newspapers. It pulls OCRed newspaper issues from Archive.org, cleans and formats the raw OCR output into readable article segments, and outputs each article as structured JSON for use in downstream systems.

**Current Version:** 0.2.0

## Project Structure

```
storydredge/
├── archive/
│   ├── raw/                  # Downloaded OCR files (.txt)
│   └── processed/            # Cleaned OCR files (.txt)
├── output/
│   ├── articles/             # Cleaned article JSONs from Phase 1
│   └── classified/           # Enriched article JSONs with metadata from Phase 2
├── scripts/
│   ├── fetch_issue.py        # Downloads and extracts OCR from archive.org
│   ├── split_articles.py     # Attempts to split OCR text into articles
│   ├── clean_text.py         # Normalizes, trims, and prepares article text
│   └── classify_articles.py  # Uses OpenAI to classify articles and extract metadata
├── data/
│   └── index.json            # Tracks processed issues
├── README.md
├── VERSION                   # Current version number
├── requirements.txt
└── .env
```

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package installer)
- OpenAI API key (for Phase 2)

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
   - Create a `.env` file with Archive.org credentials if needed
   - Set the default publication name
   - Add your OpenAI API key for Phase 2

## Usage

StoryDredge operates as a multi-step pipeline:

### Phase 1: Basic Article Extraction

#### Step 1: Fetch OCR Source

Download the OCR text from Archive.org:

```
python scripts/fetch_issue.py san-antonio-express-news-1977-08-14
```

This will download the OCR text and save it to `archive/raw/1977-08-14.txt`.

#### Step 2: Clean & Normalize

Clean and normalize the OCR text:

```
python scripts/clean_text.py 1977-08-14
```

This will process the OCR text and save the cleaned version to `archive/processed/1977-08-14-clean.txt`.

#### Step 3: Split Into Articles

Split the cleaned text into individual articles:

```
python scripts/split_articles.py 1977-08-14
```

This will detect headlines, split the text into articles, and save each article as a JSON file in `output/articles/`.

### Phase 2: Article Classification & Metadata Extraction

Using OpenAI's GPT models to enhance article data:

```
python scripts/classify_articles.py 1977-08-14
```

This will:
1. Load articles from `output/articles/`
2. Send each article to OpenAI for processing
3. Extract structured metadata (headline, byline, body, etc.)
4. Classify articles by section type (news, ad, editorial, etc.)
5. Save enriched articles to `output/classified/`
6. Generate a report of classification results

You can also filter results by section type:

```
python scripts/classify_articles.py 1977-08-14 --filter=news
```

### Complete Pipeline

To run the complete pipeline for a specific issue:

```
python scripts/fetch_issue.py san-antonio-express-news-1977-08-14
python scripts/clean_text.py 1977-08-14
python scripts/split_articles.py 1977-08-14
python scripts/classify_articles.py 1977-08-14
```

## Output Formats

### Phase 1 Output (Basic Articles)

Each article is saved as a JSON file with the following structure:

```json
{
  "title": "Headline Goes Here",
  "raw_text": "Full article body...",
  "timestamp": "1977-08-14",
  "publication": "San Antonio Express-News",
  "source_issue": "san-antonio-express-news-1977-08-14",
  "source_url": "https://archive.org/details/san-antonio-express-news-1977-08-14"
}
```

### Phase 2 Output (Classified Articles)

After processing with OpenAI, each article is enriched with additional metadata:

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 