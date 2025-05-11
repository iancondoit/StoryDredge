#!/usr/bin/env python3
"""
direct_test.py - Test the OpenAI classification with detailed debugging
"""

import os
import json
import sys
import traceback

print("Starting direct test script...")

try:
    # Load API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set or empty")
        print("Please set it with: export OPENAI_API_KEY=your_key")
        sys.exit(1)
    else:
        # Print masked key for debugging
        masked_key = api_key[:5] + "..." + api_key[-4:] if len(api_key) > 10 else "***masked***"
        print(f"API key loaded: {masked_key}")

    # Import OpenAI after checking API key
    try:
        import openai
        print("OpenAI library imported successfully")
    except ImportError as e:
        print(f"ERROR importing OpenAI: {e}")
        sys.exit(1)

    # Initialize OpenAI client
    try:
        print("Initializing OpenAI client...")
        # Create a clean client without proxies or other problematic arguments
        client = openai.OpenAI(
            api_key=api_key
        )
        print("OpenAI client initialized successfully")
    except Exception as e:
        print(f"ERROR initializing OpenAI client: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Path to test article
    article_path = "storydredge/test_article/1977-08-14--phone-strike-clutches-bell.json"
    print(f"Loading article from: {article_path}")

    # Load the article
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            article = json.load(f)
        print(f"Article loaded successfully, title: {article.get('title', 'No title')}")
    except FileNotFoundError:
        print(f"ERROR: Article file not found at {article_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse JSON: {e}")
        sys.exit(1)

    # Prepare the prompt
    prompt = f"""
You are an expert in processing old newspaper articles. Given the raw OCR text of an article, extract structured metadata.

Return a JSON object with the following keys:

- headline (string): The title of the article.
- byline (string, optional): The name of the writer or editor.
- dateline (string, optional): A city and date header like "SAN ANTONIO, AUG. 14 —"
- body (string): The full cleaned article text.
- section (string): One of: "news", "ad", "editorial", "classified", "unknown".
- tags (array of strings): Optional keywords that describe the story.

Example input:
---
{article["raw_text"][:500]}... (truncated)
---
"""
    print("Prompt prepared")

    # Call OpenAI API
    print("Calling OpenAI API...")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        print("OpenAI API call successful")
    except Exception as e:
        print(f"ERROR calling OpenAI API: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Extract and parse the JSON response
    try:
        completion_text = response.choices[0].message.content
        print(f"Response received, length: {len(completion_text)} characters")
        metadata = json.loads(completion_text)
        print("JSON parsed successfully")
    except Exception as e:
        print(f"ERROR parsing response: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Merge with original metadata
    try:
        result = {
            **metadata,
            "timestamp": article.get("timestamp", ""),
            "publication": article.get("publication", ""),
            "source_issue": article.get("source_issue", ""),
            "source_url": article.get("source_url", "")
        }
        print("Result metadata merged successfully")
    except Exception as e:
        print(f"ERROR merging metadata: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Print the result (truncated)
    print("\nClassification Result (truncated):")
    if "headline" in result:
        print(f"Headline: {result['headline']}")
    if "section" in result:
        print(f"Section: {result['section']}")
    if "byline" in result:
        print(f"Byline: {result['byline']}")
    if "tags" in result and isinstance(result['tags'], list):
        print(f"Tags: {', '.join(result['tags'])}")
    if "body" in result:
        print(f"Body (first 100 chars): {result['body'][:100]}...")

    # Save the result
    output_path = "storydredge/test_article/classified_result.json"
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nResult saved to: {output_path}")
    except Exception as e:
        print(f"ERROR saving result: {e}")
        traceback.print_exc()
        sys.exit(1)

except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Script completed successfully") 