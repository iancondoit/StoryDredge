# StoryDredge (Redesigned)

A streamlined pipeline for processing historical newspaper OCR using local LLMs.

This project processes newspaper issues from archive.org and extracts structured news articles for 
integration with the Human Story Atlas (HSA).

## Project Overview

StoryDredge processes OCR text from historical newspaper archives and extracts individual news articles, classifies them, and formats them for integration with the Human Story Atlas system. The redesigned pipeline uses a modular approach with clearly defined components and local LLM processing for improved efficiency and scalability.

### Pipeline Flow

1. **Fetching**: Download and cache newspaper OCR text from archive.org
2. **Cleaning**: Normalize and clean OCR text, fixing common OCR errors
3. **Splitting**: Identify and extract individual articles from the cleaned OCR
4. **Classification**: Use local Llama model to classify articles and extract metadata
5. **Formatting**: Convert classified articles to HSA-ready JSON format

## Directory Structure

```
storydredge/
├── src/                  # Core functionality modules
│   ├── fetcher/          # Archive.org downloading & caching
│   ├── cleaner/          # OCR text cleaning 
│   ├── splitter/         # Article splitting algorithms
│   ├── classifier/       # Local Llama-based classification
│   ├── formatter/        # HSA-ready output formatting
│   └── utils/            # Shared utilities
├── pipeline/             # Pipeline orchestration
├── models/               # Local model storage
├── config/               # Configuration files
├── tests/                # Unit and integration tests
├── data/                 # Sample data and metadata
├── output/               # Processed output files
│   └── hsa-ready/        # HSA-ready JSON output (organized by date)
└── archive/              # Legacy codebase (archived, do not modify)
```

## Installation

```bash
# Option 1: Automated setup (recommended)
./dev-setup.sh

# Option 2: Manual setup
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Ollama for local LLM support
# See https://ollama.ai/download for platform-specific instructions
```

The `dev-setup.sh` script will:
- Check Python version
- Create and activate virtual environment
- Install dependencies
- Set up the required directory structure
- Configure git hooks for code quality

## Using the Pipeline

```bash
# Process a single newspaper issue
python pipeline/main.py --issue <archive_id>

# Process multiple issues from a JSON file
python pipeline/main.py --issues-file <issues_file.json>

# Process issues in parallel (adjust number based on your system)
python pipeline/main.py --issues-file <issues_file.json> --parallel 4
```

## Testing

The project follows test-driven development principles with comprehensive test coverage:

```bash
# Run all tests
./run_tests.py

# Run specific test modules
./run_tests.py tests/test_fetcher/
./run_tests.py tests/test_cleaner/test_ocr_cleaner.py

# Run with coverage
./run_tests.py --cov=src
```

## Integration with Human Story Atlas

The output of this pipeline is structured JSON files that can be directly imported into the Human Story Atlas system. The output follows the specified format:

```json
{
  "headline": "Story Title or Headline",
  "body": "Full text content of the story...",
  "tags": ["tag1", "tag2", "tag3"],
  "section": "news",
  "timestamp": "YYYY-MM-DDTHH:MM:SS.000Z",
  "publication": "Publication Source Name",
  "source_issue": "Original source issue identifier",
  "source_url": "URL or reference to original source",
  "byline": "Author name (if available)",
  "dateline": "Location and date information (if available)"
}
```

Output files are organized by date in the `output/hsa-ready/YYYY/MM/DD/` directory structure.

## Legacy Codebase (Archive)

**IMPORTANT**: The `archive/` directory contains the legacy codebase that has been archived for reference only. Do not modify or extend the code in this directory. All new development should use the modular architecture in the `src/` directory.

The legacy codebase had several limitations that motivated the redesign:
- Complex, hard-to-maintain pipeline
- Slow processing due to API-based classification
- Limited article extraction
- Insufficient test coverage

## Contributing

When contributing to this project, please follow these guidelines:
1. Follow the modular architecture
2. Write tests for new functionality
3. Use the existing utilities in `src/utils/`
4. Maintain compatibility with the HSA output format
5. Document your changes
