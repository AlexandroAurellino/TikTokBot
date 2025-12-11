import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class AIProcessor:
    """Handles communication with the DeepSeek AI API."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key must be provided.")
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Generic trigger words
        self.trigger_words = [
            "show", "see", "look", "display", "view", "preview", 
            "buy", "get", "price", "cost", "how much", "can i", "open", 
            "interested", "demo", "close up"
        ]

    def _passes_cheap_filter(self, comment: str, products_data: list[dict]) -> bool:
        """
        Returns True if the comment contains:
        1. Exact Product Name
        2. Any word from the Product Keywords (Description)
        3. Generic trigger words (e.g. "show me")
        """
        comment_lower = comment.lower()

        # 1. Check Generic Intent Words (e.g., "Show me...")
        for trigger in self.trigger_words:
            if trigger in comment_lower:
                return True

        for prod in products_data:
            # 2. Check Product Name
            if prod['name'].lower() in comment_lower:
                return True
            
            # 3. Check Keywords from Description
            # Expecting description like: "lamp, light, rgb, glowing"
            keywords = prod.get('description', '').lower().split(',')
            for k in keywords:
                k = k.strip()
                if k and k in comment_lower:
                    return True
                
        return False

    def analyze_comment(self, comment: str, products_data: list[dict]) -> dict:
        """Analyzes a user's comment to find product intent."""
        
        # Pass the full list of dicts to the filter
        if not self._passes_cheap_filter(comment, products_data):
            logging.info(f"Skipping AI for: '{comment}' (Cheap Filter)")
            return {"intent": "other", "product_name": None}

        # Build a rich prompt with descriptions
        product_context = ""
        for p in products_data:
            desc = p.get('description', 'No keywords')
            product_context += f"- Product: '{p['name']}' (Keywords/Context: {desc})\n"

        system_prompt = (
            "You are a TikTok Live shopping assistant. "
            "Determine if the user wants to SEE or is ASKING about a specific product.\n\n"
            f"Available Products:\n{product_context}\n"
            "If the user mentions a product name OR its keywords/description, return that product name.\n"
            "Return JSON: {'intent': 'product_request'|'other', 'product_name': 'Exact Name From List'|null}."
        )

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": comment}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            logging.info(f"Invoking AI for: '{comment}'")
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=5)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return {"intent": "error", "product_name": None}