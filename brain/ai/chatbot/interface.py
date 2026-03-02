"""
Security Chatbot Interface
===========================
CLI and FastAPI web interface for the security analysis chatbot.
Provides natural language query interface for log analysis.

Author: HungryHoundDog Team
"""

import logging
from typing import Optional
import asyncio
import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
import chromadb

from ai.rag.query_engine import SecurityQueryEngine
from ai.chatbot.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """User query request."""
    question: str
    use_context: bool = True
    use_ollama: bool = True


class QueryResponse(BaseModel):
    """Chatbot response."""
    question: str
    answer: str
    context_count: int
    confidence: float
    timestamp: str


class ChatbotInterface:
    """CLI and web interface for security chatbot."""
    
    def __init__(
        self,
        chroma_client: chromadb.Client,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize chatbot interface.
        
        Args:
            chroma_client: ChromaDB client
            ollama_client: Ollama client for LLM
        """
        self.chroma_client = chroma_client
        self.ollama = ollama_client or OllamaClient()
        self.query_engine = SecurityQueryEngine(chroma_client)
        self.conversation_history = []
        
        logger.info("Chatbot interface initialized")
    
    async def process_query(self, question: str) -> QueryResponse:
        """
        Process a user query.
        
        Args:
            question: User question
            
        Returns:
            QueryResponse with answer
        """
        try:
            # Store in conversation history
            self.conversation_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": "user",
                "content": question
            })
            
            # Query the engine
            result = self.query_engine.query(question)
            
            answer = result.get("answer", "Unable to process query")
            confidence = result.get("confidence", 0.0)
            context_docs = result.get("context_documents", [])
            
            # Store in conversation history
            self.conversation_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": "assistant",
                "content": answer
            })
            
            return QueryResponse(
                question=question,
                answer=answer,
                context_count=len(context_docs),
                confidence=confidence,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Query processing error: {str(e)}", exc_info=True)
            raise
    
    def get_conversation_history(self) -> list:
        """
        Get conversation history.
        
        Returns:
            List of conversation turns
        """
        return self.conversation_history
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    async def cli_mode(self) -> None:
        """
        Run chatbot in CLI mode.
        Provides interactive terminal interface.
        """
        print("\n" + "="*60)
        print("HungryHoundDog Security Analysis Chatbot")
        print("="*60)
        print("Ask questions about security logs and alerts.")
        print("Type 'help' for available commands.")
        print("Type 'exit' to quit.\n")
        
        while True:
            try:
                question = input("You: ").strip()
                
                if not question:
                    continue
                
                if question.lower() == "exit":
                    print("Goodbye!")
                    break
                elif question.lower() == "help":
                    self._print_help()
                    continue
                elif question.lower() == "history":
                    self._print_history()
                    continue
                elif question.lower() == "clear":
                    self.clear_history()
                    print("Conversation cleared.")
                    continue
                
                # Process query
                response = await self.process_query(question)
                
                print(f"\nAssistant: {response.answer}")
                print(f"(Confidence: {response.confidence:.2%}, "
                      f"Context: {response.context_count} documents)\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again.\n")
    
    def _print_help(self) -> None:
        """Print help information."""
        help_text = """
Available Commands:
  help      - Show this help message
  history   - Display conversation history
  clear     - Clear conversation history
  exit      - Exit the chatbot

Example Queries:
  "Show me alerts from 192.168.1.100"
  "What suspicious activities occurred in the last hour?"
  "Analyze the high-severity alerts and their patterns"
  "Which hosts are showing anomalous behavior?"
  "What OT protocols are being accessed?"
        """
        print(help_text)
    
    def _print_history(self) -> None:
        """Print conversation history."""
        if not self.conversation_history:
            print("\nNo conversation history.")
            return
        
        print("\n" + "="*60)
        print("Conversation History")
        print("="*60)
        
        for turn in self.conversation_history:
            role = turn["role"].upper()
            content = turn["content"]
            timestamp = turn["timestamp"]
            
            print(f"\n[{timestamp}] {role}:")
            print(f"{content}")
        
        print("\n" + "="*60 + "\n")


# Create FastAPI app with chatbot interface
def create_chatbot_app(chroma_client: chromadb.Client) -> FastAPI:
    """
    Create FastAPI application with chatbot interface.
    
    Args:
        chroma_client: ChromaDB client
        
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="HungryHoundDog Security Chatbot",
        description="Natural language interface for security log analysis",
        version="1.0.0"
    )
    
    chatbot = ChatbotInterface(chroma_client)
    
    @app.post("/chat/query", response_model=QueryResponse)
    async def chat_query(request: QueryRequest) -> QueryResponse:
        """
        Submit a query to the chatbot.
        
        Args:
            request: Query request
            
        Returns:
            Chatbot response
        """
        return await chatbot.process_query(request.question)
    
    @app.get("/chat/history")
    async def get_history():
        """Get conversation history."""
        return chatbot.get_conversation_history()
    
    @app.post("/chat/clear")
    async def clear_chat():
        """Clear conversation history."""
        chatbot.clear_history()
        return {"message": "Conversation cleared"}
    
    @app.get("/chat/models")
    async def get_models():
        """Get available LLM models."""
        try:
            models = chatbot.ollama.list_models()
            return {"models": models}
        except Exception as e:
            raise HTTPException(status_code=503, detail="LLM service unavailable")
    
    @app.websocket("/chat/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time chat."""
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                question = data.get("question", "")
                
                if question:
                    response = await chatbot.process_query(question)
                    await websocket.send_json({
                        "question": response.question,
                        "answer": response.answer,
                        "confidence": response.confidence
                    })
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            await websocket.close()
    
    return app


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(level=logging.INFO)
    
    # Initialize ChromaDB
    chroma_client = chromadb.Client()
    
    # Create app
    app = create_chatbot_app(chroma_client)
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
