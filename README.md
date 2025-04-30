# StoryDredge

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/yourusername/storydredge)

StoryDredge is a high-performance system for processing historical newspaper archives from Archive.org. It extracts, filters, and classifies newspaper articles using a combination of rule-based identification and AI-powered content analysis.

## Project Structure

```
storydredge/
├── archive/                # Archive.org downloads
│   ├── raw/                # Raw OCR files
│   └── processed/          # Cleaned OCR files
├── data/                   # Configuration files
├── output/                 # All output files
│   ├── articles/           # Initial article JSONs
│   ├── classified/         # Articles with metadata
│   ├── news_candidates/    # High-confidence news articles
│   ├── ads/                # Advertisement articles
│   └── rejected/           # Failed articles
├── cache/                  # Cache for API responses
└── scripts/                # Processing scripts
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/storydredge.git
cd storydredge
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and other settings
```

## Optimized Workflow

StoryDredge uses a multi-stage pipeline to efficiently process historical newspapers:

1. **Extract Articles**: Split newspaper pages into individual articles
2. **Pre-filter**: Aggressively identify high-confidence news articles using pattern matching
3. **Batch Classification**: Process articles in batches with OpenAI to extract metadata
4. **Structured Output**: Save classified articles with consistent metadata format

### Key Optimizations

- **High-Confidence News Filtering**: Reduces articles needing AI processing by ~98%
- **Batch Processing**: Processes multiple articles in a single API call
- **Parallel Execution**: Handles multiple issues concurrently for faster throughput
- **Response Caching**: Caches API responses to avoid redundant calls
- **Multi-Issue Processing**: Processes entire batches of newspaper issues in a single run

## Usage

### Basic Usage

Process a single newspaper issue:

```bash
python scripts/process_high_confidence.py --date 1977-08-14
```

### Advanced Usage

Process multiple issues with custom settings:

```bash
# Process a list of dates
python scripts/process_high_confidence.py --dates 1977-08-14 1977-08-15 1977-08-16 --batch-size=15 --max-workers=4

# Process dates from a file
python scripts/process_high_confidence.py --date-file dates.txt --parallel-issues=5 --max-articles=50
```

### Pipeline Components

Individual scripts can be run separately:

```bash
# Extract high-confidence news articles
python scripts/prefilter_news.py 1977-08-14

# Classify pre-filtered articles
python scripts/classify_articles.py 1977-08-14 --file-list=output/high_confidence_news_1977-08-14.txt
```

## Performance

The optimized workflow dramatically improves processing efficiency:

- **Article Reduction**: From ~1800 to ~30-40 articles per issue (98% reduction)
- **API Calls**: ~3-4 batch calls per issue vs. 180+ individual calls
- **Processing Time**: ~90 seconds per issue vs. 15-20 minutes
- **Cost**: ~$0.07 per issue vs. $3-5 per issue

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| OPENAI_API_KEY | Your OpenAI API key | (required) |
| OPENAI_RATE_LIMIT | Maximum API requests per minute | 20 |
| DEFAULT_PUBLICATION | Default publication name | San Antonio Express-News |
| USE_API_CACHE | Enable API response caching | true |
| API_CACHE_DIR | Directory for cached responses | cache/api_responses |
| CACHE_TTL_DAYS | Cache expiration in days | 30 |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 