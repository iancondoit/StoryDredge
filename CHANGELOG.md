# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-04-30

### Added
- New `prefilter_news.py` script with advanced pattern matching for identifying news articles
- Sophisticated scoring system for identifying high-confidence news articles
- Multi-issue batch processing capability in `process_high_confidence.py`
- Response caching system to avoid redundant API calls
- Comprehensive README with usage examples
- Version tracking system
- Performance metrics reporting
- Support for parallel processing of multiple issues

### Changed
- Optimized `classify_articles.py` to process articles in batches
- Improved directory structure for more efficient organization
- Enhanced error handling and logging throughout the codebase
- Consolidated processing workflow for much faster throughput

### Optimized
- Reduced API calls by ~98% using intelligent pre-filtering
- Implemented batch processing to reduce overhead
- Added parallel execution for faster processing of multiple issues
- Cached API responses to eliminate redundant processing
- Processing time reduced from hours to minutes per issue

## [0.2.5] - 2025-03-15

### Added
- Basic project structure and processing pipeline
- Scripts for downloading and processing OCR text from Archive.org
- Article extraction and classification with OpenAI
- Simple batch processing capabilities

### Fixed
- Initial path reference issues in scripts
- OCR text cleaning improvements 