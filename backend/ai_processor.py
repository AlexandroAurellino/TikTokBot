# backend/ai_processor.py

import requests
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# --- Robustly load environment variables ---
# This builds a path to the project's root directory and finds the .env file there.
# This method is reliable, regardless of where the script is run from.
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

    def analyze_comment(self, comment: str, product_list: list[str]) -> dict:
        """Analyzes a user's comment to find product intent."""
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
            "response_format": {"type": "json_object"}
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

# --- Test block for running this file directly ---
if __name__ == '__main__':
    DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

    if not DEEPSEEK_KEY:
        print("="*60)
        print("!!! DEEPSEEK_API_KEY not found. Please check your .env file. !!!")
        print("="*60)
    else:
        our_products = ["Cosmic Glow Lamp", "Stealth Gaming Mouse", "Ultra-Soft Hoodie"]
        ai_processor = AIProcessor(api_key=DEEPSEEK_KEY)
        test_comments = [
            "hey can i see the cosmic glow lamp",
            "show me the mouse",
            "hi how are you",
            "what's the price on the hoodie?",
            "that lamp looks cool"
        ]
        print("\n--- Starting AI Processor Test ---")
        for c in test_comments:
            result = ai_processor.analyze_comment(c, our_products)
            print(f"Comment: '{c}'  ==>  Intent: {result.get('intent')}, Product: {result.get('product_name')}")
            print("-" * 30)
        print("--- Test Finished ---")