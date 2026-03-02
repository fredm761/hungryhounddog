"""
LangChain-Based RAG Query Engine
================================
Natural language query engine with context retrieval from ChromaDB.
Sends queries to Ollama for LLM-based analysis.

Author: HungryHoundDog Team
"""

import logging
from typing import List, Dict, Optional, Tuple
import chromadb
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA

logger = logging.getLogger(__name__)


class SecurityQueryEngine:
    """Query engine for security log analysis using RAG."""
    
    def __init__(
        self,
        chroma_client: chromadb.Client,
        ollama_base_url: str = "http://ollama:11434",
        collection_name: str = "security_logs"
    ):
        """
        Initialize the query engine.
        
        Args:
            chroma_client: ChromaDB client
            ollama_base_url: Ollama server URL
            collection_name: ChromaDB collection name
        """
        self.chroma_client = chroma_client
        self.ollama_base_url = ollama_base_url
        self.collection = chroma_client.get_or_create_collection(
            name=collection_name
        )
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt for security analyst."""
        try:
            with open("ai/rag/prompts/security_analyst.txt", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "You are an OT security analyst. Analyze the provided logs and provide insights."
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        use_ollama: bool = True
    ) -> Dict:
        """
        Query the security logs with natural language.
        
        Args:
            question: User question
            top_k: Number of relevant documents to retrieve
            use_ollama: Whether to use Ollama for LLM analysis
            
        Returns:
            Dictionary with context and answer
        """
        try:
            # Retrieve relevant context from vector store
            context_docs = self._retrieve_context(question, top_k)
            
            # Format context
            context_text = self._format_context(context_docs)
            
            # Generate answer
            if use_ollama:
                answer = self._query_ollama(question, context_text)
            else:
                answer = self._generate_local_answer(question, context_docs)
            
            return {
                "question": question,
                "context_documents": context_docs,
                "formatted_context": context_text,
                "answer": answer,
                "confidence": self._calculate_confidence(context_docs)
            }
            
        except Exception as e:
            logger.error(f"Query error: {str(e)}", exc_info=True)
            return {
                "question": question,
                "error": str(e),
                "answer": "Unable to process query at this time."
            }
    
    def _retrieve_context(self, query: str, top_k: int) -> List[Dict]:
        """
        Retrieve relevant context from vector store.
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of context documents
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            documents = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if i < len(results["metadatas"][0]) else {},
                        "distance": results["distances"][0][i] if results["distances"] and i < len(results["distances"][0]) else 0
                    })
            
            logger.info(f"Retrieved {len(documents)} context documents")
            return documents
            
        except Exception as e:
            logger.error(f"Context retrieval error: {str(e)}")
            return []
    
    def _format_context(self, context_docs: List[Dict]) -> str:
        """
        Format context documents for LLM.
        
        Args:
            context_docs: List of context documents
            
        Returns:
            Formatted context string
        """
        if not context_docs:
            return "No relevant context found."
        
        formatted = "Relevant Security Context:\n"
        formatted += "=" * 50 + "\n"
        
        for i, doc in enumerate(context_docs, 1):
            formatted += f"\n[Document {i}]\n"
            formatted += f"Content: {doc['text']}\n"
            
            metadata = doc.get("metadata", {})
            if metadata:
                formatted += f"Metadata: {metadata}\n"
        
        return formatted
    
    def _query_ollama(self, question: str, context: str) -> str:
        """
        Query Ollama LLM with context.
        
        Args:
            question: User question
            context: Formatted context
            
        Returns:
            LLM response
        """
        try:
            import requests
            import json
            
            prompt = f"""{self.system_prompt}

{context}

Question: {question}

Provide a detailed analysis based on the context above. Include:
1. Summary of relevant events
2. Key indicators of concern
3. Recommended actions
4. Timestamp references when applicable"""
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": "llama2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Unable to generate response")
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return "Error communicating with LLM service"
                
        except Exception as e:
            logger.error(f"Ollama query error: {str(e)}")
            return "Unable to reach LLM service"
    
    def _generate_local_answer(self, question: str, context_docs: List[Dict]) -> str:
        """
        Generate answer from context without LLM.
        
        Args:
            question: User question
            context_docs: Context documents
            
        Returns:
            Generated answer
        """
        if not context_docs:
            return "No relevant information found in the security logs."
        
        answer = f"Based on {len(context_docs)} relevant security events:\n\n"
        
        # Extract key information
        for doc in context_docs:
            answer += f"- {doc['text']}\n"
        
        return answer
    
    def _calculate_confidence(self, context_docs: List[Dict]) -> float:
        """
        Calculate confidence in answer based on context.
        
        Args:
            context_docs: Context documents
            
        Returns:
            Confidence score (0-1)
        """
        if not context_docs:
            return 0.0
        
        # More documents = higher confidence
        doc_factor = min(len(context_docs) / 5.0, 1.0)
        
        # Better relevance = higher confidence
        avg_distance = sum(d.get("distance", 1.0) for d in context_docs) / len(context_docs)
        relevance_factor = max(1.0 - avg_distance, 0.0)
        
        confidence = (doc_factor + relevance_factor) / 2.0
        return min(confidence, 1.0)
    
    def search_alerts(self, src_ip: Optional[str] = None, severity: Optional[int] = None) -> List[Dict]:
        """
        Search alerts by criteria.
        
        Args:
            src_ip: Source IP to filter
            severity: Minimum severity level
            
        Returns:
            List of matching alerts
        """
        try:
            # Build filter if provided
            where_filter = None
            if src_ip or severity is not None:
                where_filter = {}
                if src_ip:
                    where_filter["src_ip"] = {"$eq": src_ip}
                if severity is not None:
                    where_filter["severity"] = {"$gte": severity}
            
            # Query collection
            results = self.collection.get(
                where=where_filter,
                limit=100
            )
            
            documents = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    documents.append({
                        "text": doc,
                        "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {}
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []


def create_query_engine(chroma_client: chromadb.Client) -> SecurityQueryEngine:
    """
    Create a security query engine.
    
    Args:
        chroma_client: ChromaDB client
        
    Returns:
        Configured SecurityQueryEngine
    """
    return SecurityQueryEngine(chroma_client)
