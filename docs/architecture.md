# StoryDredge Architecture Documentation

This document provides a detailed overview of the StoryDredge architecture, including component interactions, data flow, and design decisions.

## System Overview

StoryDredge implements a modular pipeline architecture that processes newspaper OCR text through a series of stages, from fetching raw OCR text to producing HSA-ready JSON files.

### High-Level Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Fetcher   │───>│   Cleaner   │───>│  Splitter   │───>│ Classifier  │───>│  Formatter  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                 │                  │                  │                  │
       ▼                 ▼                  ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Raw OCR    │    │  Cleaned    │    │  Articles   │    │ Classified  │    │  HSA-Ready  │
│   Text      │    │    Text     │    │   JSON      │    │  Articles   │    │    JSON     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Component Architecture

### 1. Fetcher Component

The Fetcher is responsible for downloading and caching newspaper OCR text from archive.org.

```
┌───────────────────────────────────────────────────────┐
│                     Fetcher                           │
│                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐   │
│  │   HTTP      │    │   Cache     │    │  Rate    │   │
│  │   Client    │───>│  Manager    │───>│ Limiter  │   │
│  └─────────────┘    └─────────────┘    └──────────┘   │
│         │                  │                │         │
└─────────┼──────────────────┼────────────────┼─────────┘
          │                  │                │
          ▼                  ▼                ▼
    ┌──────────┐      ┌──────────────┐   ┌──────────┐
    │Archive.org│      │  Local Cache │   │Retry Logic│
    └──────────┘      └──────────────┘   └──────────┘
```

**Key Interfaces:**
- `fetch_issue(archive_id)` - Downloads and caches a newspaper issue by ID
- `search_archive(query)` - Searches archive.org for newspaper issues

### 2. Cleaner Component

The Cleaner processes raw OCR text to normalize and correct common OCR errors.

```
┌───────────────────────────────────────────────────────┐
│                      Cleaner                          │
│                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐   │
│  │ Normalizer  │    │ Error       │    │ Content  │   │
│  │             │───>│ Correction  │───>│ Filter   │   │
│  └─────────────┘    └─────────────┘    └──────────┘   │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Key Interfaces:**
- `clean_text(text)` - Cleans and normalizes OCR text
- `process_file(input_file, output_file)` - Processes an entire OCR file

### 3. Splitter Component

The Splitter identifies individual articles within the cleaned OCR text.

```
┌───────────────────────────────────────────────────────┐
│                     Splitter                          │
│                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐   │
│  │  Headline   │    │  Article    │    │ Quality  │   │
│  │  Detector   │───>│  Extractor  │───>│ Checker  │   │
│  └─────────────┘    └─────────────┘    └──────────┘   │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Key Interfaces:**
- `detect_headlines(text)` - Identifies potential headlines in the text
- `extract_articles(text, headlines)` - Extracts article content
- `split_file(input_file, output_dir)` - Processes a file into articles

### 4. Classifier Component

The Classifier uses a local LLM to analyze and classify article content.

```
┌───────────────────────────────────────────────────────┐
│                    Classifier                         │
│                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐   │
│  │   Prompt    │    │   Ollama    │    │ Response │   │
│  │  Generator  │───>│   Client    │───>│  Parser  │   │
│  └─────────────┘    └─────────────┘    └──────────┘   │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Key Interfaces:**
- `classify_article(article)` - Classifies a single article
- `classify_batch(articles)` - Classifies a batch of articles

### 5. Formatter Component

The Formatter transforms classified articles into HSA-ready JSON format.

```
┌───────────────────────────────────────────────────────┐
│                    Formatter                          │
│                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐   │
│  │  Field      │    │  Schema     │    │ Output   │   │
│  │  Mapper     │───>│  Validator  │───>│ Writer   │   │
│  └─────────────┘    └─────────────┘    └──────────┘   │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Key Interfaces:**
- `format_article(article)` - Formats a single article
- `process_batch(articles)` - Processes a batch of articles

## Data Flow

1. **Archive.org ID → Raw OCR Text**
   - Fetcher downloads and caches the OCR text

2. **Raw OCR Text → Cleaned Text**
   - Cleaner normalizes and corrects the text

3. **Cleaned Text → Article Objects**
   - Splitter identifies and extracts articles

4. **Article Objects → Classified Articles**
   - Classifier adds metadata and categorizes

5. **Classified Articles → HSA-Ready JSON**
   - Formatter creates final output files

## Design Principles

### 1. Separation of Concerns
Each component handles a single responsibility, with clear interfaces between stages.

### 2. Testability
Components are designed to be independently testable with well-defined inputs and outputs.

### 3. Error Handling
Each component implements proper error handling and graceful degradation.

### 4. Performance
The system optimizes for performance through caching, batch processing, and parallel execution.

### 5. Extensibility
The modular design allows for easy extension or replacement of individual components.

## Configuration

The system uses a central configuration system that allows customization of each component:

```
config/
├── fetcher.yml      # Fetcher configuration
├── cleaner.yml      # Cleaner configuration 
├── splitter.yml     # Splitter configuration
├── classifier.yml   # Classifier configuration
├── formatter.yml    # Formatter configuration
└── pipeline.yml     # Overall pipeline configuration
```

## Error Handling Strategy

1. **Component-Level Handling**
   - Each component handles errors internally when possible
   - Components return appropriate error indicators

2. **Pipeline-Level Handling**
   - The pipeline orchestrator handles component failures
   - Implements retry logic for transient errors

3. **Logging and Monitoring**
   - Comprehensive logging of errors
   - Monitoring of error rates and patterns 