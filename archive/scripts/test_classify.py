#!/usr/bin/env python3
"""
test_classify.py - Test the classification of a single article with OpenAI

Usage:
    python test_classify.py <path_to_article.json>
    
Example:
    python test_classify.py test_article/1977-08-14--phone-strike-clutches-bell.json
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# OpenAI API settings
API_KEY = os.getenv("OPENAI_API_KEY")

def setup_openai():
    """Initialize the OpenAI client with the API key."""
    if not API_KEY:
        print("Error: OPENAI_API_KEY is not set in .env file")
        sys.exit(1)
    
    return openai.OpenAI(
        api_key=API_KEY
    )

def process_article(client, article_path):
    """
    Process a single article with OpenAI.
    
    Args:
        client: OpenAI client
        article_path (Path): Path to the article JSON file
        
    Returns:
        dict: Processed article data with metadata
    """
    # Load the article
    with open(article_path, 'r', encoding='utf-8') as f:
        article = json.load(f)
    
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
{article["raw_text"]}
---
"""
    
    # Call OpenAI API
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
    metadata = json.loads(completion_text)
    
    # Merge with original metadata
    result = {
        **metadata,
        "timestamp": article.get("timestamp", ""),
        "publication": article.get("publication", ""),
        "source_issue": article.get("source_issue", ""),
        "source_url": article.get("source_url", "")
    }
    
    return result

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_classify.py <path_to_article.json>")
        print("Example: python test_classify.py test_article/1977-08-14--phone-strike-clutches-bell.json")
        return
    
    article_path = Path(sys.argv[1])
    if not article_path.exists():
        print(f"Error: Article file not found: {article_path}")
        return
    
    client = setup_openai()
    
    print(f"Processing article: {article_path}")
    
    # Process the article
    result = process_article(client, article_path)
    
    # Print the result
    print("\nClassification Result:")
    print(json.dumps(result, indent=2))
    
    # Save the result
    output_path = article_path.with_name(f"classified_{article_path.name}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nResult saved to: {output_path}")

if __name__ == "__main__":
    main() 