# StoryDredge v1.0.0 (stable)

A streamlined pipeline for processing historical newspaper OCR using local LLMs.

This project processes newspaper issues from archive.org and extracts structured news articles for 
integration with the Human Story Atlas (HSA).

## Recent Improvements

Several key improvements have been made to the StoryDredge pipeline:

1. **Fast Rule-based Classification**: Articles are now classified using a high-performance rule-based system by default, processing hundreds of articles in under a second. LLM-based classification remains available as an option.

2. **Enhanced Entity Extraction**: The system now extracts people, organizations, and locations from articles and adds them to the tags array in the HSA-ready output.

3. **Improved Directory Structure**: The pipeline now uses a cleaner directory structure with temporary files stored in a dedicated temp directory and final output in the properly organized hsa-ready folder.

4. **Comprehensive Testing**: New test scripts verify all aspects of the pipeline, including directory structure, rule-based classification, and entity tag extraction.

For full details on these improvements, see [docs/pipeline_improvements.md](docs/pipeline_improvements.md).

## Project Overview

StoryDredge processes OCR text from historical newspaper archives and extracts individual news articles, classifies them, and formats them for integration with the Human Story Atlas system. The redesigned pipeline uses a modular approach with clearly defined components and local LLM processing for improved efficiency and scalability.

### Pipeline Flow

1. **Fetching**: Download and cache newspaper OCR text from archive.org
2. **Cleaning**: Normalize and clean OCR text, fixing common OCR errors
3. **Splitting**: Identify and extract individual articles from the cleaned text
4. **Classification**: Classify each article by type and extract metadata using local LLMs
5. **Formatting**: Structure and format the articles for Human Story Atlas integration

### HSA Output Format

The final output of the pipeline is a series of JSON files in the `output/hsa-ready/YYYY/MM/DD/` directory with the following structure:

```json
{
  "headline": "AND SAVE MONEY",
  "body": "AND SAVE MONEY. \nSANTA CLAUS left another carload of oil \nstocks in your chimney...",
  "tags": ["news"],
  "section": "news",
  "timestamp": "1922-01-01T00:00:00.000Z",
  "publication": "Atlanta Constitution",
  "source_issue": "per_atlanta-constitution_1922-01-01_54_203",
  "source_url": "https://archive.org/details/per_atlanta-constitution_1922-01-01",
  "byline": ""
}
```

All fields are required except for `byline` and `dateline` which are optional. The HSA formatter will attempt to add default values for missing fields when possible.

## Local Development

### Prerequisites
- Python 3.10+
- Ollama for local LLM support

### Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/storydredge-redesigned.git
cd storydredge-redesigned
```

2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Install Ollama and pull the required models
```bash
# Follow instructions at https://ollama.ai/
ollama pull llama2:7b
```

## Usage

### Basic Usage

Process a single newspaper issue:
```bash
python pipeline/main.py --issue <issue_identifier>
```

Process a batch of issues:
```bash
python pipeline/batch.py --issues_file <path_to_issues_file.json>
```

### Pipeline Diagnostics

Diagnose pipeline issues for a specific newspaper issue:
```bash
python scripts/diagnose_pipeline.py --issue <issue_identifier>
```

Generate an HTML report with detailed diagnostics:
```bash
python scripts/diagnose_pipeline.py --issue <issue_identifier> --report report.html
```

Attempt to fix formatter issues:
```bash
python scripts/diagnose_pipeline.py --issue <issue_identifier> --fix formatter
```

### Verify Output Format

Verify that output files match the required HSA format:
```bash
python scripts/verify_output_format.py --dir output/hsa-ready
```

Show a sample of the expected HSA output format:
```bash
python scripts/verify_output_format.py --sample
```

### Testing

Run the test suite:
```bash
pytest tests/
```

#### Testing with Atlanta Constitution Data

The StoryDredge pipeline has been successfully tested with real OCR data from the Atlanta Constitution newspaper archive (1922). This testing verified:

- The OCR fetching component can correctly download files from archive.org following HTTP redirects
- The OCR cleaning component successfully normalizes text and removes noise
- The article splitting component can identify and extract hundreds of articles per issue
- Typical issues yield 200-500 articles each with good headline detection

To try testing with Atlanta Constitution data:
```bash
PYTHONPATH=. python scripts/test_atlanta_constitution_direct.py
```

See the [Atlanta Constitution Testing Guide](docs/testing/atlanta_constitution_testing.md) for more details.

## Legacy Codebase

The original StoryDredge codebase is preserved in the `archive/` directory for reference. The new implementation improves upon the original with a more modular design, better error handling, and local LLM processing.

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
├── scripts/              # Utility scripts and tools
│   ├── diagnose_pipeline.py    # Pipeline diagnostic tool
│   └── verify_output_format.py # Output format verification
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

### Error Handling and Logging

The pipeline includes robust error handling and detailed logging:

- Logs are stored in the `logs/` directory with separate log files for each component
- The formatter component provides detailed logs of validation issues in `logs/formatter.log`
- Log level can be configured in `config/pipeline.yml`

To debug pipeline issues:
1. Check component-specific logs in the `logs/` directory
2. Use the diagnostic tool: `python scripts/diagnose_pipeline.py --issue <issue_id> --verbose`
3. Review the validation report: `python scripts/verify_output_format.py`

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

## Testing with the Atlanta Constitution Dataset

StoryDredge has built-in support for testing with the Atlanta Constitution newspaper collection:

### Getting Started with Atlanta Constitution Tests

We've created utilities to streamline testing with the Atlanta Constitution dataset:

```bash
# Prepare a test dataset from January 1922 issues
python scripts/prepare_atlanta_constitution_dataset.py --start-date 1922-01-01 --end-date 1922-01-31

# Run a comprehensive test (dataset preparation, tests, and pipeline)
python scripts/run_atlanta_constitution_test.py --prepare --test --run-pipeline

# Run with parallel processing
python scripts/run_atlanta_constitution_test.py --prepare --run-pipeline --workers 4
```

### Why the Atlanta Constitution?

The [Atlanta Constitution collection](https://archive.org/details/pub_atlanta-constitution) is ideal for testing because:
- It spans many decades (1881-1945)
- Most issues have OCR text available
- It contains diverse content types
- OCR quality varies, providing a good test of robustness

### Documentation

Detailed documentation for testing with this dataset is available at:
- [Atlanta Constitution Testing Guide](docs/testing/atlanta_constitution_testing.md)

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

## HSA Formatter

The HSA Formatter is responsible for converting classified articles into the HSA-ready format. It performs the following tasks:

1. **Field mapping**: Converts fields like `title` to `headline` and `raw_text` to `body`
2. **Tag extraction**: Extracts tags from classified articles' metadata (topic, people, organizations, locations)
3. **Section mapping**: Maps category fields to valid HSA section values
4. **Date extraction**: Automatically extracts historical dates from archive.org identifiers like `per_atlanta-constitution_1922-01-01_54_203`
5. **Timestamp formatting**: Ensures consistent timestamp format
6. **Source information enrichment**: Adds source information like publication and source URLs
7. **Validation**: Validates articles against the HSA schema requirements

### Date Extraction Feature

A significant improvement to the formatter is the automatic extraction of publication dates from archive.org identifiers. This ensures articles are correctly organized by their historical publication dates rather than processing dates. The system supports multiple date formats:

- `per_atlanta-constitution_1922-01-01_54_203` (standard hyphenated format)
- `per_chicago-tribune_1934-05-22` (without issue numbers)
- `sim_newcastle-morning-herald_18931015` (compact date format)

This feature automatically creates the proper directory structure (YYYY/MM/DD) for each article based on its historical date, making the HSA data organization historically accurate and easier to navigate.

### Usage

To convert classified articles to HSA-ready format:

```bash
# Process all classified articles
python scripts/rebuild_hsa_output.py

# Process with custom input/output directories
python scripts/rebuild_hsa_output.py --input-dir custom_input --output-dir custom_output
```

### Output Structure

HSA-ready articles are organized in the output directory with the following structure:

```
output/hsa-ready/
  └── YYYY/
      └── MM/
          └── DD/
              └── article-title-timestamp.json
```

### Metadata Extraction

The HSAFormatter extracts metadata from the classified articles to populate the tags field:

- **Category**: The article's main category becomes a tag
- **Topic**: The topic from metadata is added as a tag
- **People**: Names of people mentioned in the article
- **Organizations**: Names of organizations mentioned in the article
- **Locations**: Geographic locations mentioned in the article

This ensures that the HSA-ready articles have rich metadata for search and organization.
