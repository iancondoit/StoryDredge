#!/usr/bin/env python3
"""
new_test.py - A clean implementation to test OpenAI classification
"""

import os
import json
import sys
from pathlib import Path
from openai import OpenAI

def main():
    """Main function to process an article with OpenAI."""
    if len(sys.argv) < 2:
        print("Usage: python new_test.py <path_to_article.json>")
        print("Example: python new_test.py storydredge/test_article/1977-08-14--phone-strike-clutches-bell.json")
        return
    
    # Get article path
    article_path = Path(sys.argv[1])
    if not article_path.exists():
        print(f"Error: Article file not found: {article_path}")
        return
    
    # Load the article
    print(f"Loading article from: {article_path}")
    with open(article_path, 'r', encoding='utf-8') as f:
        article = json.load(f)
    
    # Load API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set or empty")
        print("Please set it with: export OPENAI_API_KEY=your_key")
        sys.exit(1)
        
    print("Initializing OpenAI client")
    client = OpenAI(api_key=api_key)
    
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
    
    # Call OpenAI API
    print("Calling OpenAI API...")
    
    try:
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Extract and parse the JSON response
        completion_text = response.choices[0].message.content
        print(f"Response received, length: {len(completion_text)} characters")
        
        metadata = json.loads(completion_text)
        
        # Merge with original metadata
        result = {
            **metadata,
            "timestamp": article.get("timestamp", ""),
            "publication": article.get("publication", ""),
            "source_issue": article.get("source_issue", ""),
            "source_url": article.get("source_url", "")
        }
        
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
        output_path = article_path.with_name(f"new_classified_{article_path.name}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nResult saved to: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
if __name__ == "__main__":
    main() 