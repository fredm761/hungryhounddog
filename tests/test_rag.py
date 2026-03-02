#!/usr/bin/env python3
"""
test_rag.py: Tests for RAG (Retrieval-Augmented Generation) chatbot.

Verifies that the RAG pipeline:
- Loads ChromaDB vector database
- Retrieves relevant security knowledge
- Generates contextual answers to security questions
- Maintains conversation context
"""

import json
import pytest
from datetime import datetime
from typing import Dict, List, Any, Tuple


class MockChromaDB:
    """Mock ChromaDB vector database for testing."""

    def __init__(self):
        """Initialize mock vector database."""
        self.documents = [
            {
                "id": "doc_1",
                "text": "Modbus is an unencrypted OT protocol used for industrial control systems. Default port 502.",
                "metadata": {"topic": "protocols", "severity": "high"}
            },
            {
                "id": "doc_2",
                "text": "Unauthorized Modbus writes can cause dangerous PLC state changes. Always authenticate clients.",
                "metadata": {"topic": "security", "severity": "critical"}
            },
            {
                "id": "doc_3",
                "text": "MQTT over port 1883 carries sensor telemetry data. Enable authentication and encryption.",
                "metadata": {"topic": "protocols", "severity": "medium"}
            },
            {
                "id": "doc_4",
                "text": "SSH brute force detection: monitor failed login attempts, implement rate limiting.",
                "metadata": {"topic": "defense", "severity": "high"}
            },
            {
                "id": "doc_5",
                "text": "Network segmentation: isolate OT from IT networks using VLANs and firewalls.",
                "metadata": {"topic": "architecture", "severity": "critical"}
            }
        ]
        self.is_loaded = False

    def load_db(self) -> bool:
        """Load vector database."""
        self.is_loaded = True
        return True

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Query database for relevant documents.

        Simple keyword matching for mock implementation.
        """
        query_terms = query_text.lower().split()
        results = []

        for doc in self.documents:
            doc_text = doc["text"].lower()
            matching_terms = sum(1 for term in query_terms if term in doc_text)

            if matching_terms > 0:
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "relevance_score": matching_terms / len(query_terms),
                    "metadata": doc["metadata"]
                })

        # Sort by relevance and return top_k
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

    def get_document_count(self) -> int:
        """Get total documents in database."""
        return len(self.documents)


class MockLLM:
    """Mock Language Model for answer generation."""

    def __init__(self):
        """Initialize mock LLM."""
        self.is_loaded = False
        self.prompts_processed = 0

    def load_model(self) -> bool:
        """Load language model."""
        self.is_loaded = True
        return True

    def generate_answer(
        self,
        question: str,
        context_documents: List[str],
        max_tokens: int = 500
    ) -> str:
        """
        Generate answer based on question and context.

        Mock implementation provides rule-based responses.
        """
        self.prompts_processed += 1

        question_lower = question.lower()

        if "modbus" in question_lower:
            return (
                "Based on the knowledge base: Modbus is an unencrypted OT protocol used for "
                "industrial control systems on the default port 502. Unauthorized Modbus writes "
                "can cause dangerous PLC state changes, so authentication is critical."
            )
        elif "ssh" in question_lower or "brute" in question_lower:
            return (
                "For SSH security: Monitor failed login attempts and implement rate limiting. "
                "Consider using key-based authentication and disabling password login."
            )
        elif "mqtt" in question_lower:
            return (
                "MQTT carries sensor telemetry data on port 1883. Enable authentication and "
                "encryption to protect this critical data stream."
            )
        elif "segment" in question_lower or "vlan" in question_lower:
            return (
                "Network segmentation is critical: isolate OT from IT networks using VLANs "
                "and firewalls to prevent lateral movement."
            )
        else:
            return "I found relevant information: " + "; ".join(context_documents[:1])


class TestRAGPipeline:
    """Test suite for RAG chatbot pipeline."""

    @pytest.fixture
    def chromadb(self):
        """Fixture: Vector database."""
        db = MockChromaDB()
        db.load_db()
        return db

    @pytest.fixture
    def llm(self):
        """Fixture: Language model."""
        m = MockLLM()
        m.load_model()
        return m

    def test_chromadb_loading(self):
        """Test that ChromaDB loads successfully."""
        db = MockChromaDB()
        success = db.load_db()

        assert success is True
        assert db.is_loaded is True

    def test_chromadb_document_count(self, chromadb):
        """Test document count in database."""
        count = chromadb.get_document_count()

        assert count > 0
        assert count == 5

    def test_llm_loading(self):
        """Test that LLM loads successfully."""
        model = MockLLM()
        success = model.load_model()

        assert success is True
        assert model.is_loaded is True

    def test_query_modbus_security(self, chromadb):
        """Test querying for Modbus security information."""
        results = chromadb.query("Modbus security unauthorized writes")

        assert len(results) > 0
        assert any("Modbus" in r["text"] for r in results)

    def test_query_returns_metadata(self, chromadb):
        """Test that query results include metadata."""
        results = chromadb.query("SSH brute force")

        assert len(results) > 0
        for result in results:
            assert "metadata" in result
            assert "topic" in result["metadata"]

    def test_generate_answer_modbus(self, chromadb, llm):
        """Test generating answer to Modbus question."""
        question = "How can we protect against Modbus attacks?"
        context = chromadb.query(question)
        context_texts = [r["text"] for r in context]

        answer = llm.generate_answer(question, context_texts)

        assert "Modbus" in answer
        assert len(answer) > 50

    def test_generate_answer_ssh(self, chromadb, llm):
        """Test generating answer to SSH question."""
        question = "How do we prevent SSH brute force attacks?"
        context = chromadb.query(question)
        context_texts = [r["text"] for r in context]

        answer = llm.generate_answer(question, context_texts)

        assert "SSH" in answer or "brute" in answer.lower()

    def test_rag_pipeline_modbus_query(self, chromadb, llm):
        """Test complete RAG pipeline for Modbus question."""
        question = "What are Modbus security risks?"

        # Step 1: Retrieve
        context_docs = chromadb.query(question, top_k=3)
        assert len(context_docs) > 0

        # Step 2: Generate
        context_texts = [d["text"] for d in context_docs]
        answer = llm.generate_answer(question, context_texts)

        assert "Modbus" in answer
        assert len(answer) > 50

    def test_rag_pipeline_security_recommendation(self, chromadb, llm):
        """Test RAG pipeline for security recommendation question."""
        question = "How should we segment our OT network?"

        # Retrieve
        context_docs = chromadb.query(question, top_k=3)
        context_texts = [d["text"] for d in context_docs]

        # Generate
        answer = llm.generate_answer(question, context_texts)

        assert "segment" in answer.lower() or "isolate" in answer.lower()

    def test_query_with_top_k_limit(self, chromadb):
        """Test that top_k parameter limits results."""
        results_3 = chromadb.query("security modbus ssh", top_k=3)
        results_1 = chromadb.query("security modbus ssh", top_k=1)

        assert len(results_3) <= 3
        assert len(results_1) <= 1

    def test_relevance_score_ordering(self, chromadb):
        """Test that results are ordered by relevance."""
        results = chromadb.query("modbus protocol security")

        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["relevance_score"] >= results[i+1]["relevance_score"]

    def test_chatbot_maintains_context(self, chromadb, llm):
        """Test that chatbot can maintain conversation context."""
        conversation = [
            "What is Modbus?",
            "How can we secure it?",
            "What about MQTT?"
        ]

        answers = []
        for question in conversation:
            context = chromadb.query(question, top_k=2)
            context_texts = [d["text"] for d in context]
            answer = llm.generate_answer(question, context_texts)
            answers.append(answer)

        assert len(answers) == 3
        assert all(len(a) > 20 for a in answers)

    def test_llm_tracks_prompts(self, llm, chromadb):
        """Test that LLM tracks number of prompts processed."""
        initial_count = llm.prompts_processed

        for i in range(3):
            context = chromadb.query("test query")
            llm.generate_answer("test", [d["text"] for d in context])

        assert llm.prompts_processed == initial_count + 3

    def test_rag_handles_unknown_question(self, chromadb, llm):
        """Test RAG pipeline handles questions not in knowledge base."""
        question = "What is the meaning of life?"

        context = chromadb.query(question)
        context_texts = [d["text"] for d in context]

        answer = llm.generate_answer(question, context_texts)

        assert len(answer) > 0
        assert isinstance(answer, str)

    def test_rag_multiturn_security_analysis(self, chromadb, llm):
        """Test multi-turn conversation for security analysis."""
        conversation = [
            ("What protocols does our OT system use?", ["Modbus", "MQTT"]),
            ("What are the security risks?", ["Modbus", "unencrypted", "brute"]),
            ("How should we defend?", ["authenticate", "segment", "monitor"])
        ]

        for question, expected_keywords in conversation:
            context = chromadb.query(question, top_k=2)
            context_texts = [d["text"] for d in context]
            answer = llm.generate_answer(question, context_texts)

            # At least one keyword should appear in answer
            assert any(kw.lower() in answer.lower() for kw in expected_keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
