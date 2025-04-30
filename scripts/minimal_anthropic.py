#!/usr/bin/env python3
"""
minimal_anthropic.py - Minimal implementation using httpx to call Anthropic API directly
"""

import os
import json
import time
import httpx

def process_article(article_path, output_dir=None):
    """Process article with Anthropic API using direct httpx calls."""
    print(f"Processing article: {article_path}")
    
    # Load API key from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set or empty")
        print("Please set it with: export ANTHROPIC_API_KEY=your_key")
        return None
    
    # Load the article
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            article = json.load(f)
        print(f"Article loaded: {article.get('title', 'Untitled')}")
    except Exception as e:
        print(f"Error loading article: {e}")
        return None
    
    # Prepare output directory
    if not output_dir:
        output_dir = os.path.dirname(article_path)
    
    # Extract filename without extension
    filename = os.path.basename(article_path)
    filename_no_ext = os.path.splitext(filename)[0]
    
    # Prepare the prompt
    raw_text = article.get('raw_text', '')
    if not raw_text:
        print("Error: No raw_text found in article")
        return None
    
    print(f"Text length: {len(raw_text)}")
    
    system_prompt = "You are an expert in processing old newspaper articles. Given the raw OCR text of an article, extract structured metadata."
    
    user_prompt = f"""
Extract structured metadata from this newspaper article.

Return a JSON object with the following keys:

- headline (string): The title of the article.
- byline (string, optional): The name of the writer or editor.
- dateline (string, optional): A city and date header like "SAN ANTONIO, AUG. 14 —"
- body (string): The full cleaned article text.
- section (string): One of: "news", "ad", "editorial", "classified", "unknown".
- tags (array of strings): Optional keywords that describe the story.

Here is the article text:
---
{raw_text}
---
"""
    
    # Prepare the API request
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-2.1",
        "max_tokens": 4000,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }
    
    # Make the API call
    print("Calling Anthropic API...")
    start_time = time.time()
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code}, {response.text}")
                return None
            
            result = response.json()
            elapsed_time = time.time() - start_time
            print(f"API call completed in {elapsed_time:.2f} seconds")
            
    except Exception as e:
        print(f"Error calling API: {e}")
        return None
    
    # Extract and parse the response
    try:
        content = result["content"][0]["text"]
        
        # Find JSON in response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            extracted = json.loads(json_str)
            print("Successfully parsed response")
        else:
            print("Error: Could not find JSON in response")
            return None
            
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None
    
    # Merge with original metadata
    final_result = {
        **extracted,
        "timestamp": article.get("timestamp", ""),
        "publication": article.get("publication", ""),
        "source_issue": article.get("source_issue", ""),
        "source_url": article.get("source_url", "")
    }
    
    # Save the result
    output_filename = f"anthropic_classified_{filename_no_ext}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        print(f"Result saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving result: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        article_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        process_article(article_path, output_dir)
    else:
        print("Usage: python minimal_anthropic.py <article_path> [output_dir]")
        sys.exit(1) 