"""
RAG Vector Store Indexer
========================
Embeds security logs and alerts into ChromaDB vector store.
Uses sentence-transformers for text embeddings.

Author: HungryHoundDog Team
"""

import logging
from typing import List, Dict, Optional
import hashlib
from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch
import chromadb

logger = logging.getLogger(__name__)


class SecurityLogIndexer:
    """Index security logs and alerts into vector store for RAG."""
    
    def __init__(
        self,
        chroma_client: Optional[chromadb.Client] = None,
        opensearch_client: Optional[OpenSearch] = None,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the indexer.
        
        Args:
            chroma_client: ChromaDB client
            opensearch_client: OpenSearch client
            model_name: Sentence transformer model name
        """
        self.chroma_client = chroma_client
        self.opensearch = opensearch_client
        self.embedding_model = SentenceTransformer(model_name)
        self.collection = None
        
        # Initialize ChromaDB collection
        if self.chroma_client:
            self.collection = self.chroma_client.get_or_create_collection(
                name="security_logs",
                metadata={"hnsw:space": "cosine"}
            )
    
    def index_alerts(self, index_name: str = "suricata-alerts", batch_size: int = 100) -> int:
        """
        Index alerts from OpenSearch into vector store.
        
        Args:
            index_name: OpenSearch index to read from
            batch_size: Number of documents per batch
            
        Returns:
            Number of indexed documents
        """
        if not self.opensearch or not self.collection:
            logger.error("OpenSearch or ChromaDB client not initialized")
            return 0
        
        indexed_count = 0
        
        try:
            # Fetch alerts from OpenSearch
            query = {
                "query": {"match_all": {}},
                "size": batch_size,
                "sort": [{"timestamp": {"order": "desc"}}]
            }
            
            results = self.opensearch.search(index=index_name, body=query)
            
            documents = []
            ids = []
            metadatas = []
            
            for hit in results["hits"]["hits"]:
                doc = hit["_source"]
                
                # Create searchable text representation
                text = self._document_to_text(doc)
                
                # Generate ID
                doc_id = self._generate_doc_id(doc)
                
                documents.append(text)
                ids.append(doc_id)
                metadatas.append({
                    "source": "opensearch",
                    "index": index_name,
                    "timestamp": doc.get("timestamp", ""),
                    "severity": str(doc.get("severity", 0)),
                    "src_ip": doc.get("src_ip", ""),
                    "dst_ip": doc.get("dst_ip", "")
                })
                
                indexed_count += 1
            
            # Add to collection
            if documents:
                self.collection.add(
                    documents=documents,
                    ids=ids,
                    metadatas=metadatas
                )
                logger.info(f"Indexed {len(documents)} alerts to vector store")
            
            return indexed_count
            
        except Exception as e:
            logger.error(f"Error indexing alerts: {str(e)}", exc_info=True)
            return 0
    
    def index_flows(self, index_name: str = "network-flows", batch_size: int = 100) -> int:
        """
        Index network flows from OpenSearch into vector store.
        
        Args:
            index_name: OpenSearch index to read from
            batch_size: Number of documents per batch
            
        Returns:
            Number of indexed documents
        """
        if not self.opensearch or not self.collection:
            logger.error("OpenSearch or ChromaDB client not initialized")
            return 0
        
        indexed_count = 0
        
        try:
            # Fetch flows from OpenSearch
            query = {
                "query": {"match_all": {}},
                "size": batch_size,
                "sort": [{"timestamp": {"order": "desc"}}]
            }
            
            results = self.opensearch.search(index=index_name, body=query)
            
            documents = []
            ids = []
            metadatas = []
            
            for hit in results["hits"]["hits"]:
                doc = hit["_source"]
                
                # Create searchable text representation
                text = self._flow_to_text(doc)
                
                # Generate ID
                doc_id = self._generate_doc_id(doc)
                
                documents.append(text)
                ids.append(doc_id)
                metadatas.append({
                    "source": "opensearch",
                    "index": index_name,
                    "timestamp": doc.get("timestamp", ""),
                    "src_ip": doc.get("src_ip", ""),
                    "dst_ip": doc.get("dst_ip", ""),
                    "protocol": doc.get("protocol", "")
                })
                
                indexed_count += 1
            
            # Add to collection
            if documents:
                self.collection.add(
                    documents=documents,
                    ids=ids,
                    metadatas=metadatas
                )
                logger.info(f"Indexed {len(documents)} flows to vector store")
            
            return indexed_count
            
        except Exception as e:
            logger.error(f"Error indexing flows: {str(e)}", exc_info=True)
            return 0
    
    def index_custom_docs(self, documents: List[Dict]) -> int:
        """
        Index custom documents into vector store.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            Number of indexed documents
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return 0
        
        try:
            texts = []
            ids = []
            metadatas = []
            
            for doc in documents:
                text = doc.get("text", str(doc))
                doc_id = self._generate_doc_id(doc)
                
                texts.append(text)
                ids.append(doc_id)
                
                metadata = {
                    "source": doc.get("source", "custom"),
                    "timestamp": doc.get("timestamp", "")
                }
                metadatas.append(metadata)
            
            if texts:
                self.collection.add(
                    documents=texts,
                    ids=ids,
                    metadatas=metadatas
                )
                logger.info(f"Indexed {len(texts)} custom documents")
            
            return len(texts)
            
        except Exception as e:
            logger.error(f"Error indexing custom documents: {str(e)}")
            return 0
    
    def _document_to_text(self, doc: Dict) -> str:
        """
        Convert alert document to searchable text.
        
        Args:
            doc: Alert document
            
        Returns:
            Text representation
        """
        parts = [
            f"Alert: {doc.get('alert_message', 'Unknown')}",
            f"Severity: {doc.get('severity', 0)}",
            f"Source: {doc.get('src_ip', 'Unknown')}:{doc.get('src_port', 'N/A')}",
            f"Destination: {doc.get('dst_ip', 'Unknown')}:{doc.get('dst_port', 'N/A')}",
            f"Protocol: {doc.get('protocol', 'Unknown')}",
            f"Category: {doc.get('category', 'Unknown')}",
            f"Timestamp: {doc.get('timestamp', 'Unknown')}"
        ]
        
        return " | ".join(parts)
    
    def _flow_to_text(self, doc: Dict) -> str:
        """
        Convert flow document to searchable text.
        
        Args:
            doc: Flow document
            
        Returns:
            Text representation
        """
        parts = [
            f"Network Flow",
            f"Source: {doc.get('src_ip', 'Unknown')}:{doc.get('src_port', 'N/A')}",
            f"Destination: {doc.get('dst_ip', 'Unknown')}:{doc.get('dst_port', 'N/A')}",
            f"Protocol: {doc.get('protocol', 'Unknown')}",
            f"Bytes In: {doc.get('bytes_in', 0)}",
            f"Bytes Out: {doc.get('bytes_out', 0)}",
            f"Packets: {doc.get('packet_count', 0)}",
            f"Duration: {doc.get('duration_seconds', 0)}s",
            f"Timestamp: {doc.get('timestamp', 'Unknown')}"
        ]
        
        return " | ".join(parts)
    
    def _generate_doc_id(self, doc: Dict) -> str:
        """
        Generate unique document ID.
        
        Args:
            doc: Document dictionary
            
        Returns:
            Unique ID
        """
        key = f"{doc.get('timestamp', '')}:{doc.get('src_ip', '')}:{doc.get('dst_ip', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about indexed documents.
        
        Returns:
            Dictionary with collection statistics
        """
        if not self.collection:
            return {}
        
        try:
            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {}


def index_opensearch_alerts(opensearch_client: OpenSearch, chroma_client: chromadb.Client) -> int:
    """
    Convenience function to index OpenSearch alerts.
    
    Args:
        opensearch_client: OpenSearch client
        chroma_client: ChromaDB client
        
    Returns:
        Number of indexed documents
    """
    indexer = SecurityLogIndexer(
        chroma_client=chroma_client,
        opensearch_client=opensearch_client
    )
    return indexer.index_alerts()
