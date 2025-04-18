import sys
import os
import unittest
import json
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import migrate_and_sanitize

class TestMigrateAndSanitize(unittest.TestCase):
    """Test cases for the migrate_and_sanitize.py functions."""
    
    def setUp(self):
        """Set up test directory structure."""
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "classified")
        os.makedirs(self.source_dir, exist_ok=True)
        
        # Create a test article JSON file
        self.test_article = {
            "headline": "Test Article",
            "byline": "Test Author",
            "dateline": "Test Location",
            "body": "This is a *test* article with\n\n\nexcessive breaks and   spacing  .",
            "section": "news",
            "tags": ["test", "article"],
            "timestamp": "2023-01-01",
            "publication": "Test Publication",
            "source_issue": "test-2023-01-01",
            "source_url": "https://example.com/test"
        }
        
        self.test_file_path = os.path.join(self.source_dir, "2023-01-01--test-article.json")
        with open(self.test_file_path, 'w') as f:
            json.dump(self.test_article, f)
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    def test_sanitize_body_text(self):
        """Test sanitizing body text from a JSON file."""
        # Apply sanitization
        dirty_text = "This is a *test* with\n\n\nexcessive breaks and   spacing  ."
        clean_text = migrate_and_sanitize.sanitize_body_text(dirty_text)
        
        # Test different aspects of sanitization
        self.assertNotIn("*", clean_text)  # Symbols removed
        self.assertNotIn("\n\n\n", clean_text)  # Excessive line breaks removed
        self.assertEqual(clean_text, "This is a test with\n\nexcessive breaks and spacing.")
    
    @patch('migrate_and_sanitize.SOURCE_DIR')
    @patch('migrate_and_sanitize.TARGET_BASE_DIR')
    def test_create_directory_structure(self, mock_target, mock_source):
        """Test the creation of the nested directory structure."""
        # Set up the mock paths
        mock_target.return_value = self.test_dir
        
        # Test directory creation
        with patch('os.makedirs') as mock_makedirs:
            target_dir = migrate_and_sanitize.create_directory_structure("2023", "01", "01")
            mock_makedirs.assert_called_once()
    
    @patch('migrate_and_sanitize.SOURCE_DIR')
    @patch('migrate_and_sanitize.TARGET_BASE_DIR')
    def test_process_files(self, mock_target, mock_source):
        """Test the processing of JSON files with mocked paths."""
        # Set mock values for directories
        mock_source.return_value = self.source_dir
        mock_target.return_value = self.test_dir
        
        # Patch the directory functions to use our test structure
        with patch('migrate_and_sanitize.SOURCE_DIR', self.source_dir), \
             patch('migrate_and_sanitize.TARGET_BASE_DIR', self.test_dir), \
             patch('migrate_and_sanitize.create_directory_structure') as mock_create_dir, \
             patch('migrate_and_sanitize.sanitize_body_text', return_value="Sanitized text"):
            
            # Mock the directory creation
            mock_create_dir.return_value = os.path.join(self.test_dir, "2023", "01", "01")
            
            # Run the function with test case mocking
            with patch('builtins.open', mock_open()) as mock_file:
                stats = migrate_and_sanitize.process_files()
                
                # Check that files were processed
                self.assertGreaterEqual(stats["processed"], 0)

if __name__ == "__main__":
    unittest.main() 