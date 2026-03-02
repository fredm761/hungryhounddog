"""
Ollama LLM Client
=================
Wrapper for Ollama REST API interactions.
Handles model management, text generation, and health checks.

Author: HungryHoundDog Team
"""

import logging
from typing import List, Dict, Optional
import requests
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama LLM service."""
    
    def __init__(self, base_url: str = "http://ollama:11434"):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama server URL
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = 60
        self.default_model = "llama2"
        
        logger.info(f"Initialized Ollama client: {self.base_url}")
    
    def health_check(self) -> bool:
        """
        Check if Ollama service is healthy.
        
        Returns:
            True if service is available
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {str(e)}")
            return False
    
    def list_models(self) -> List[Dict]:
        """
        List available models.
        
        Returns:
            List of available model information
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            logger.info(f"Found {len(models)} available models")
            return models
            
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            return []
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9
    ) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            model: Model name (defaults to llama2)
            stream: Whether to stream response
            temperature: Sampling temperature
            top_k: Top K sampling parameter
            top_p: Top P sampling parameter
            
        Returns:
            Generated text
        """
        model = model or self.default_model
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                # Handle streaming response
                text = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        text += data.get("response", "")
                return text
            else:
                # Handle non-streaming response
                data = response.json()
                return data.get("response", "")
            
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            raise
    
    def generate_with_context(
        self,
        question: str,
        context: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate response with provided context.
        
        Args:
            question: User question
            context: Relevant context/examples
            model: Model name
            system_prompt: System prompt
            
        Returns:
            Generated response
        """
        system = system_prompt or (
            "You are a helpful security analyst. Answer questions about "
            "network security logs based on the provided context."
        )
        
        prompt = f"""{system}

Context:
{context}

Question: {question}

Answer:"""
        
        return self.generate(prompt, model=model)
    
    def summarize(
        self,
        text: str,
        model: Optional[str] = None,
        max_length: int = 200
    ) -> str:
        """
        Summarize text.
        
        Args:
            text: Text to summarize
            model: Model name
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        prompt = f"""Summarize the following text in at most {max_length} words:

{text}

Summary:"""
        
        return self.generate(prompt, model=model)
    
    def classify(
        self,
        text: str,
        categories: List[str],
        model: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Classify text into categories.
        
        Args:
            text: Text to classify
            categories: List of category names
            model: Model name
            
        Returns:
            Dictionary with category scores
        """
        categories_str = ", ".join(categories)
        
        prompt = f"""Classify the following text into one of these categories: {categories_str}

Text: {text}

Classification:"""
        
        response = self.generate(prompt, model=model)
        
        # Parse response (simplified)
        result = {cat: 0.0 for cat in categories}
        
        for cat in categories:
            if cat.lower() in response.lower():
                result[cat] = 1.0
        
        # Normalize
        total = sum(result.values())
        if total > 0:
            for cat in result:
                result[cat] /= total
        
        return result
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Chat with the model, maintaining conversation context.
        
        Args:
            message: User message
            conversation_history: Previous messages
            model: Model name
            
        Returns:
            Model response
        """
        # Build conversation context
        context = ""
        if conversation_history:
            for turn in conversation_history:
                role = turn.get("role", "user").upper()
                content = turn.get("content", "")
                context += f"{role}: {content}\n"
        
        prompt = f"{context}USER: {message}\nASSISTANT:"
        
        return self.generate(prompt, model=model)
    
    def pull_model(self, model_name: str) -> bool:
        """
        Pull (download) a model from Ollama library.
        
        Args:
            model_name: Model name to pull
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling model: {model_name}")
            
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=300  # Long timeout for download
            )
            response.raise_for_status()
            
            logger.info(f"Successfully pulled model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull model: {str(e)}")
            return False
    
    def get_model_info(self, model_name: str) -> Dict:
        """
        Get detailed information about a model.
        
        Args:
            model_name: Model name
            
        Returns:
            Model information dictionary
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {}


def get_ollama_client(base_url: str = "http://ollama:11434") -> OllamaClient:
    """
    Get or create an Ollama client.
    
    Args:
        base_url: Ollama server URL
        
    Returns:
        OllamaClient instance
    """
    return OllamaClient(base_url)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    client = OllamaClient()
    
    # Check health
    if client.health_check():
        print("Ollama service is healthy")
        
        # List models
        models = client.list_models()
        print(f"Available models: {len(models)}")
        for model in models:
            print(f"  - {model.get('name')}")
        
        # Example generation
        try:
            response = client.generate(
                "Explain network security in one sentence.",
                model="llama2"
            )
            print(f"\nGenerated response:\n{response}")
        except Exception as e:
            print(f"Generation error: {e}")
    else:
        print("Ollama service is not available")
