import sys
import os
import unittest
import json
import tempfile
from unittest.mock import patch, mock_open
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.filter_and_finalize import (
    sanitize_body_text, 
    count_sentences, 
    calculate_symbol_ratio, 
    should_exclude_article
)

class TestFilterFinalize(unittest.TestCase):
    """Test cases for the filter_and_finalize.py functions."""
    
    def test_sanitize_body_text(self):
        """Test the sanitization of article body text."""
        # Test removing excessive line breaks
        self.assertEqual(sanitize_body_text("Line 1\n\n\n\nLine 2"), "Line 1\n\nLine 2")
        
        # Test removing non-printable characters
        self.assertEqual(sanitize_body_text("Text with *symbols* #removed"), "Text with symbols removed")
        
        # Test normalizing punctuation spacing
        self.assertEqual(sanitize_body_text("Text with  , weird spacing ."), "Text with, weird spacing.")
        
        # Test fixing broken spacing
        self.assertEqual(sanitize_body_text("Multiple    spaces"), "Multiple spaces")
        
        # Test un-hyphenating words
        self.assertEqual(sanitize_body_text("hy-\nphenated"), "hyphenated")
        
        # Test trimming whitespace
        self.assertEqual(sanitize_body_text("  Trim spaces  "), "Trim spaces")
        
        # Test compound example
        dirty_text = "  This is *a* text with\n\n\nexcessive #breaks and   spacing  ."
        clean_text = "This is a text with\n\nexcessive breaks and spacing."
        self.assertEqual(sanitize_body_text(dirty_text), clean_text)

    def test_count_sentences(self):
        """Test counting sentences in a text."""
        # Test empty text
        self.assertEqual(count_sentences(""), 0)
        
        # Test single sentence
        self.assertEqual(count_sentences("This is one sentence."), 1)
        
        # Test multiple sentences
        self.assertEqual(count_sentences("Sentence one. Sentence two! Sentence three?"), 3)
        
        # Test with no sentence-ending punctuation
        self.assertEqual(count_sentences("No ending punctuation"), 0)

    def test_calculate_symbol_ratio(self):
        """Test calculating symbol-to-word ratio in a text."""
        # Test empty text
        self.assertEqual(calculate_symbol_ratio(""), 1.0)
        
        # Test text with no symbols
        self.assertEqual(calculate_symbol_ratio("Text with no symbols"), 0.0)
        
        # Test text with symbols
        # 5 words, 2 symbols
        self.assertEqual(calculate_symbol_ratio("Text, with some! symbols"), 0.4)
        
        # Test text with only symbols
        self.assertEqual(calculate_symbol_ratio("!@#$%"), 1.0)

    def test_should_exclude_article(self):
        """Test the article exclusion logic."""
        # Test article with ad section
        ad_article = {"section": "ad", "headline": "Test", "body": "This is a test body."}
        exclude, reason = should_exclude_article(ad_article)
        self.assertTrue(exclude)
        self.assertEqual(reason, "Section type excluded")
        
        # Test article with missing headline
        no_headline = {"section": "news", "body": "This is a test body."}
        exclude, reason = should_exclude_article(no_headline)
        self.assertTrue(exclude)
        self.assertEqual(reason, "Missing headline")
        
        # Test article with missing body
        no_body = {"section": "news", "headline": "Test"}
        exclude, reason = should_exclude_article(no_body)
        self.assertTrue(exclude)
        self.assertEqual(reason, "Missing body")
        
        # Test article with short body
        short_body = {"section": "news", "headline": "Test", "body": "Short."}
        exclude, reason = should_exclude_article(short_body)
        self.assertTrue(exclude)
        self.assertEqual(reason, "Body too short")
        
        # Test article with too few sentences
        few_sentences = {"section": "news", "headline": "Test", "body": "X" * 200}
        exclude, reason = should_exclude_article(few_sentences)
        self.assertTrue(exclude)
        self.assertEqual(reason, "Too few sentences")
        
        # Test article with high symbol ratio
        symbol_heavy = {"section": "news", "headline": "Test", "body": "Text " + "!" * 100 + ". More text."}
        exclude, reason = should_exclude_article(symbol_heavy)
        self.assertTrue(exclude)
        self.assertEqual(reason, "High symbol-to-word ratio")
        
        # Test article that passes all filters
        good_article = {
            "section": "news", 
            "headline": "Test Headline", 
            "body": "This is a good article with sufficient length. It has multiple sentences and normal symbol usage."
        }
        exclude, reason = should_exclude_article(good_article)
        self.assertFalse(exclude)
        self.assertIsNone(reason)

if __name__ == "__main__":
    unittest.main() 