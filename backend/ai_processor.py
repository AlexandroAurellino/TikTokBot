# backend/ai_processor.py

import requests
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# --- Robustly load environment variables ---
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class AIProcessor:
    """Handles communication with the DeepSeek AI API."""

    def __init__(self, api_key: str):
        """Initializes the processor with the API key."""
        if not api_key:
            raise ValueError("API key must be provided and cannot be empty.")
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # KEYWORDS that suggest a user is interested in a product.
        # If a comment doesn't have a product name OR one of these words, we skip the AI.
        self.trigger_words = [
            "show", "see", "look", "display", "view", "preview", 
            "buy", "get", "price", "cost", "how much", "can i", "open", 
            "interested", "demo", "close up"
        ]

    def _passes_cheap_filter(self, comment: str, product_list: list[str]) -> bool:
        """
        Returns True if the comment contains product names or trigger words.
        This saves API tokens by filtering out 'hi', 'hello', 'shared', etc.
        """
        comment_lower = comment.lower()
        
        # 1. Check for direct product name mentions (fuzzy check)
        for product in product_list:
            if product.lower() in comment_lower:
                return True
                
        # 2. Check for intent trigger words
        for trigger in self.trigger_words:
            if trigger in comment_lower:
                return True
                
        return False

    def analyze_comment(self, comment: str, product_list: list[str]) -> dict:
        """Analyzes a user's comment to find product intent."""
        
        # --- COST SAVING CHECK ---
        if not self._passes_cheap_filter(comment, product_list):
            logging.info(f"Skipping AI for: '{comment}' (No product/trigger keywords found)")
            return {"intent": "other", "product_name": None}

        # --- AI REQUEST ---
        products_str = ", ".join(f'"{p}"' for p in product_list)
        system_prompt = (
            "You are an intelligent assistant for a TikTok Shop live stream. "
            f"The available products are: {products_str}. "
            "Analyze the user's comment to see if it is a request to view one of the products. "
            "Your response MUST be a single JSON object with two keys: 'intent' and 'product_name'. "
            "The 'intent' must be either 'product_request' or 'other'. "
            "The 'product_name' must be the exact name from the product list, or null if the intent is 'other'."
            "It is critical that the 'product_name' you return is an exact match to one of the names in the provided list."
        )
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": comment}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1 # Low temp = more consistent answers
        }

        try:
            logging.info(f"Sending comment to DeepSeek: '{comment}'")
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            ai_response_str = response.json()['choices'][0]['message']['content']
            ai_response_json = json.loads(ai_response_str)
            logging.info(f"Received structured response from AI: {ai_response_json}")
            return ai_response_json
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            return {"intent": "error", "product_name": None}
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logging.error(f"Failed to parse AI response: {e}")
            return {"intent": "error", "product_name": None}