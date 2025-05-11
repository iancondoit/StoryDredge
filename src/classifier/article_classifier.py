"""
Article Classifier Component

This module contains the ArticleClassifier class which classifies articles using
local LLMs through Ollama.
"""

import json
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from src.utils.errors import StoryDredgeError, ValidationError
from src.utils.config import get_config_manager
from src.utils.progress import ProgressReporter


class OllamaClient:
    """
    Client for interacting with Ollama API.
    
    This class provides methods to interact with the Ollama API for
    generating text using local LLMs.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for the Ollama API
        """
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def generate(self, 
                 prompt: str, 
                 model: str = "llama2", 
                 temperature: float = 0.7,
                 max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use for generation
            temperature: Controls randomness (0.0-1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dictionary containing the model response
            
        Raises:
            StoryDredgeError: If the API request fails
        """
        self.logger.debug(f"Generating text with model {model}")
        
        try:
            # Prepare the request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False  # Ensure we get a complete response, not streaming
            }
            
            # Make the API request to Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60  # Reasonable timeout for LLM generation
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the JSON response
            try:
                result = response.json()
                
                # Ensure we have a 'response' field in our result
                if "response" not in result:
                    result["response"] = result.get("text", result.get("message", ""))
                
                # Log success
                self.logger.debug(f"Successfully generated text with model {model}")
                
                return result
            except ValueError as e:
                # Handle poorly formatted JSON
                self.logger.warning(f"Error parsing JSON from Ollama: {e}")
                # Try to fix common formatting issues
                text = response.text.strip()
                
                # Create a fallback response
                result = {
                    "model": model,
                    "response": text,
                    "done": True
                }
                
                return result
            
        except requests.RequestException as e:
            self.logger.error(f"Error generating text with Ollama: {e}")
            raise StoryDredgeError(f"Ollama API error: {e}")


class PromptTemplates:
    """
    Manages prompt templates for article classification.
    
    This class loads and provides access to prompt templates for
    different classification tasks.
    """
    
    def __init__(self, templates_dir: Union[str, Path] = None):
        """
        Initialize prompt templates.
        
        Args:
            templates_dir: Directory containing prompt templates
        """
        self.logger = logging.getLogger(__name__)
        
        if templates_dir is None:
            templates_dir = Path("config/prompts")
        
        self.templates_dir = Path(templates_dir)
        self.templates = {}
        
        # Load templates from directory
        self._load_templates()
    
    def _load_templates(self):
        """
        Load all prompt templates from the templates directory.
        """
        if not self.templates_dir.exists():
            self.logger.warning(f"Templates directory {self.templates_dir} not found")
            return
            
        self.logger.debug(f"Loading prompt templates from {self.templates_dir}")
        
        # Find all text files in the templates directory
        template_files = list(self.templates_dir.glob("*.txt"))
        
        if not template_files:
            self.logger.warning(f"No template files found in {self.templates_dir}")
            return
            
        # Load each template file
        for file_path in template_files:
            template_name = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    template_content = f.read()
                    
                self.templates[template_name] = template_content
                self.logger.debug(f"Loaded template: {template_name}")
            except Exception as e:
                self.logger.error(f"Error loading template {template_name}: {e}")
        
        self.logger.info(f"Loaded {len(self.templates)} prompt templates")
    
    def get_template(self, template_name: str) -> str:
        """
        Get a prompt template by name.
        
        Args:
            template_name: Name of the template to get
            
        Returns:
            The prompt template string
            
        Raises:
            ValidationError: If the template doesn't exist
        """
        if template_name not in self.templates:
            # Check if template file exists but wasn't loaded
            file_path = self.templates_dir / f"{template_name}.txt"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        template_content = f.read()
                    
                    self.templates[template_name] = template_content
                    return template_content
                except Exception as e:
                    self.logger.error(f"Error loading template {template_name}: {e}")
            
            self.logger.warning(f"Template {template_name} not found, using default")
            
            # Return a basic default template if not found
            return """
            You are an expert newspaper article classifier.
            
            Analyze the following article and classify it into one of these categories:
            - News
            - Opinion
            - Feature
            - Sports
            - Business
            - Entertainment
            - Other
            
            Also extract the following information:
            - Main topic
            - Key people mentioned
            - Key organizations mentioned
            - Key locations mentioned
            
            Article:
            {article_text}
            
            Respond in valid JSON format with the following structure:
            {
                "category": "category_name",
                "confidence": 0.95,
                "metadata": {
                    "topic": "main_topic",
                    "people": ["person1", "person2"],
                    "organizations": ["org1", "org2"],
                    "locations": ["location1", "location2"]
                }
            }
            """
        
        return self.templates[template_name]
        
    def format_template(self, template_name: str, **kwargs) -> str:
        """
        Format a template with the provided variables.
        
        Args:
            template_name: Name of the template to format
            **kwargs: Variables to use for formatting
            
        Returns:
            The formatted template string
            
        Raises:
            ValidationError: If the template doesn't exist
        """
        template = self.get_template(template_name)
        
        try:
            formatted = template.format(**kwargs)
            return formatted
        except KeyError as e:
            error_msg = f"Missing required variable in template {template_name}: {e}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)
        except Exception as e:
            error_msg = f"Error formatting template {template_name}: {e}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)


class ArticleClassifier:
    """
    Classifies newspaper articles using local LLMs through Ollama.
    
    Features:
    - Article classification using LLMs
    - Metadata extraction from articles
    - Batch processing of multiple articles
    - Configurable models and parameters
    """
    
    def __init__(self, model: str = None):
        """
        Initialize the ArticleClassifier.
        
        Args:
            model: Name of the Ollama model to use (default: use config value)
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load()
        self.config = config_manager.config.classifier
        
        # Get configuration values
        config_dict = self.config.model_dump()
        self.model = model or config_dict.get("model_name", "llama2")
        self.batch_size = config_dict.get("batch_size", 10)
        self.concurrency = config_dict.get("concurrency", 2)
        self.confidence_threshold = config_dict.get("confidence_threshold", 0.6)
        self.fallback_category = config_dict.get("fallback_section", "miscellaneous")
        self.prompt_template_name = config_dict.get("prompt_template", "article_classification")
        
        # Initialize components
        self.ollama_client = OllamaClient()
        self.prompt_templates = PromptTemplates()
        self.max_retries = 3
        
        self.logger.info(f"Initialized ArticleClassifier with model {self.model}")
    
    def classify_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a single article.
        
        Args:
            article: Article dictionary with at least 'raw_text' field
            
        Returns:
            Classification result dictionary
        """
        self.logger.debug(f"Classifying article: {article.get('title', 'Untitled')[:50]}...")
        
        try:
            # Extract text from article
            article_text = article.get("raw_text", "")
            if not article_text:
                self.logger.warning("Article has no raw_text field")
                return self._create_default_result(article)
                
            # Create a prompt for classification
            prompt = self._create_prompt(article_text)
            
            # Generate classification using Ollama
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = self.ollama_client.generate(
                        prompt=prompt,
                        model=self.model,
                        temperature=0.3,  # Lower temperature for more consistent results
                        max_tokens=1000
                    )
                    
                    # Parse the LLM response
                    result = self._parse_response(response, article)
                    
                    # Check if result has valid category with sufficient confidence
                    if self._validate_result(result):
                        self.logger.debug(f"Successfully classified article as {result.get('category')}")
                        return result
                    else:
                        self.logger.warning(f"Classification result failed validation on attempt {attempt}")
                        if attempt < self.max_retries:
                            continue
                        return self._create_default_result(article)
                        
                except StoryDredgeError as e:
                    self.logger.warning(f"Error on classification attempt {attempt}: {e}")
                    if attempt >= self.max_retries:
                        raise
            
            # If we get here, all retries failed
            return self._create_default_result(article)
                
        except Exception as e:
            self.logger.error(f"Failed to classify article: {e}")
            return self._create_default_result(article)
    
    def classify_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify a batch of articles.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            List of classification results
        """
        self.logger.info(f"Classifying batch of {len(articles)} articles")
        
        # Create progress reporter if needed
        progress = ProgressReporter("Classifying Articles", len(articles))
        
        results = []
        for i, article in enumerate(articles):
            try:
                result = self.classify_article(article)
                results.append(result)
                progress.update(i + 1)
            except Exception as e:
                self.logger.error(f"Error classifying article {i}: {e}")
                results.append(self._create_default_result(article))
                progress.update(i + 1)
        
        progress.complete()
        self.logger.info(f"Completed batch classification of {len(articles)} articles")
        return results
    
    def classify_file(self, input_file: Union[str, Path]) -> Dict[str, Any]:
        """
        Classify an article from a JSON file.
        
        Args:
            input_file: Path to the input JSON file
            
        Returns:
            Classification result
        """
        input_path = Path(input_file)
        self.logger.debug(f"Classifying article from file: {input_path}")
        
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                article = json.load(f)
                
            result = self.classify_article(article)
            return result
            
        except Exception as e:
            self.logger.error(f"Error classifying article from file {input_path}: {e}")
            raise StoryDredgeError(f"Failed to classify article from file: {e}")
    
    def classify_directory(self, 
                       input_dir: Union[str, Path], 
                       output_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        Classify all article files in a directory.
        
        Args:
            input_dir: Path to directory containing article JSON files
            output_dir: Path to directory for output files (optional)
            
        Returns:
            List of classification results
        """
        input_path = Path(input_dir)
        self.logger.info(f"Classifying articles in directory: {input_path}")
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)
        
        # Find all JSON files in the input directory
        input_files = list(input_path.glob("*.json"))
        self.logger.info(f"Found {len(input_files)} article files to classify")
        
        # Create progress reporter
        progress = ProgressReporter("Classifying Articles", len(input_files))
        
        results = []
        for i, file_path in enumerate(input_files):
            try:
                # Load article from file
                with open(file_path, "r", encoding="utf-8") as f:
                    article = json.load(f)
                
                # Classify the article
                result = self.classify_article(article)
                results.append(result)
                
                # Save the result if output directory is provided
                if output_dir:
                    output_file = output_path / file_path.name
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2)
                
                progress.update(i + 1)
                
            except Exception as e:
                self.logger.error(f"Error processing file {file_path}: {e}")
                progress.update(i + 1)
        
        progress.complete()
        self.logger.info(f"Completed classification of {len(results)} articles")
        return results
    
    def _create_prompt(self, article_text: str) -> str:
        """
        Create a prompt for article classification.
        
        Args:
            article_text: The text of the article to classify
            
        Returns:
            Classification prompt
        """
        try:
            # Use the prompt template to format the prompt
            prompt = self.prompt_templates.format_template(
                self.prompt_template_name,
                article_text=article_text
            )
            return prompt
        except Exception as e:
            self.logger.warning(f"Error creating prompt with template: {e}")
            # Fall back to basic prompt if template fails
            try:
                basic_template = self.prompt_templates.get_template("article_classification")
                return basic_template.format(article_text=article_text)
            except Exception as fallback_error:
                # Last resort fallback
                self.logger.warning(f"Error using fallback template: {fallback_error}")
                return f"""
                You are an expert newspaper article classifier.
                
                Analyze the following article and classify it into one of these categories:
                - News
                - Opinion
                - Feature
                - Sports
                - Business
                - Entertainment
                - Other
                
                Also extract the following information:
                - Main topic
                - Key people mentioned
                - Key organizations mentioned
                - Key locations mentioned
                
                Article:
                {article_text}
                
                Respond in valid JSON format with the following structure:
                {{
                    "category": "category_name",
                    "confidence": 0.95,
                    "metadata": {{
                        "topic": "main_topic",
                        "people": ["person1", "person2"],
                        "organizations": ["org1", "org2"],
                        "locations": ["location1", "location2"]
                    }}
                }}
                """
    
    def _parse_response(self, response: Dict[str, Any], original_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the response from Ollama.
        
        Args:
            response: The response from Ollama
            original_article: The original article
            
        Returns:
            Parsed classification result
        """
        try:
            # Extract the response text
            response_text = response.get("response", "")
            if not response_text:
                self.logger.warning("Empty response from LLM")
                return self._create_default_result(original_article)
            
            # Try to find JSON in the response - LLMs sometimes add commentary
            try:
                # First, see if the response is already valid JSON
                parsed_json = json.loads(response_text)
                
                # If we get here, it was valid JSON
                result = parsed_json
                
                # Ensure it has the expected fields
                if "category" not in result and "section" in result:
                    # Handle older format that might use 'section' instead of 'category'
                    result["category"] = result["section"]
                
                # Add original article content
                result.update({k: v for k, v in original_article.items() if k not in result})
                
                return result
            except json.JSONDecodeError:
                # Not valid JSON, try to extract the JSON part
                json_start = response_text.find("{")
                json_end = response_text.rfind("}")
                
                if json_start != -1 and json_end != -1:
                    # Extract the JSON part
                    json_text = response_text[json_start:json_end + 1]
                    try:
                        # Parse the JSON
                        result = json.loads(json_text)
                        
                        # Add original article content
                        result.update({k: v for k, v in original_article.items() if k not in result})
                        
                        return result
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse JSON from response: {e}")
            
            # If no valid JSON was found, try to extract structured data manually
            # This is a fallback for when the LLM doesn't output proper JSON
            result = self._extract_structured_data(response_text)
            
            # Merge with original article
            result.update({k: v for k, v in original_article.items() if k not in result})
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return self._create_default_result(original_article)
    
    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """
        Extract structured data from text when JSON parsing fails.
        
        Args:
            text: The response text from the LLM
            
        Returns:
            Dictionary with extracted data
        """
        result = {
            "category": self.fallback_category,
            "confidence": 0.0,
            "metadata": {
                "topic": "",
                "people": [],
                "organizations": [],
                "locations": []
            }
        }
        
        # Try to find category
        category_patterns = [
            r"category[\"']?\s*:+\s*[\"']?([^\"',\}]+)[\"']?",
            r"category\s*is\s*:*\s*([A-Za-z]+)"
        ]
        
        for pattern in category_patterns:
            import re
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["category"] = match.group(1).strip()
                break
        
        # Try to find confidence
        confidence_match = re.search(r"confidence[\"']?\s*:+\s*([0-9.]+)", text)
        if confidence_match:
            try:
                result["confidence"] = float(confidence_match.group(1))
            except ValueError:
                pass
        
        # Try to extract metadata
        # Topic
        topic_match = re.search(r"topic[\"']?\s*:+\s*[\"']?([^\"',\}]+)[\"']?", text, re.IGNORECASE)
        if topic_match:
            result["metadata"]["topic"] = topic_match.group(1).strip()
        
        # Look for lists using regex
        for field in ["people", "organizations", "locations"]:
            list_pattern = rf"{field}[\"']?\s*:+\s*\[(.*?)\]"
            list_match = re.search(list_pattern, text, re.IGNORECASE | re.DOTALL)
            if list_match:
                items_text = list_match.group(1)
                items = []
                for item in re.finditer(r"[\"']([^\"']+)[\"']", items_text):
                    items.append(item.group(1).strip())
                result["metadata"][field] = items
        
        return result
    
    def _validate_result(self, result: Dict[str, Any]) -> bool:
        """
        Validate a classification result.
        
        Args:
            result: The classification result to validate
            
        Returns:
            True if the result is valid, False otherwise
        """
        # Check if result has required fields
        if "category" not in result:
            return False
            
        # Check confidence threshold if provided
        if "confidence" in result:
            try:
                confidence = float(result["confidence"])
                if confidence < self.confidence_threshold:
                    return False
            except (ValueError, TypeError):
                pass
        
        return True
    
    def _create_default_result(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a default result when classification fails.
        
        Args:
            article: The original article
            
        Returns:
            Default classification result
        """
        result = {
            "category": self.fallback_category,
            "confidence": 0.0,
            "metadata": {
                "topic": "",
                "people": [],
                "organizations": [],
                "locations": []
            }
        }
        
        # Include original article content
        result.update({k: v for k, v in article.items() if k not in result})
        
        return result 