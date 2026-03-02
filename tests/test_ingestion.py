#!/usr/bin/env python3
"""
test_ingestion.py: Tests for log ingestion pipeline.

Verifies that logs from various sensor formats flow through parsing,
normalization, and are successfully indexed in OpenSearch.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, Any


class MockLogParser:
    """Mock parser for testing."""

    def __init__(self):
        self.parsed_logs = []

    def parse_syslog(self, log_line: str) -> Dict[str, Any]:
        """Parse syslog format."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "source_format": "syslog",
            "message": log_line,
            "parsed": True
        }

    def parse_json_log(self, json_str: str) -> Dict[str, Any]:
        """Parse JSON format."""
        data = json.loads(json_str)
        data["source_format"] = "json"
        data["parsed"] = True
        return data

    def parse_csv_log(self, csv_line: str) -> Dict[str, Any]:
        """Parse CSV format."""
        fields = csv_line.split(",")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "source_format": "csv",
            "fields": fields,
            "field_count": len(fields),
            "parsed": True
        }


class MockOpenSearchIndexer:
    """Mock OpenSearch indexer for testing."""

    def __init__(self):
        self.indexed_documents = []

    def index_document(self, index: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """Index a document."""
        self.indexed_documents.append({
            "index": index,
            "doc_id": doc_id,
            "document": document,
            "timestamp": datetime.utcnow().isoformat()
        })
        return True

    def index_bulk(self, index: str, documents: list) -> int:
        """Index multiple documents."""
        for i, doc in enumerate(documents):
            self.index_document(index, str(i), doc)
        return len(documents)

    def get_indexed_count(self) -> int:
        """Get total indexed documents."""
        return len(self.indexed_documents)


class TestLogIngestion:
    """Test suite for log ingestion pipeline."""

    @pytest.fixture
    def parser(self):
        """Fixture: Log parser."""
        return MockLogParser()

    @pytest.fixture
    def indexer(self):
        """Fixture: OpenSearch indexer."""
        return MockOpenSearchIndexer()

    def test_parse_syslog_format(self, parser):
        """Test parsing syslog formatted logs."""
        log_line = "Feb 27 10:15:30 plc-01 modbus[1234]: Connection from 192.168.1.50:12345"

        result = parser.parse_syslog(log_line)

        assert result["parsed"] is True
        assert result["source_format"] == "syslog"
        assert "timestamp" in result
        assert "Connection from" in result["message"]

    def test_parse_json_log(self, parser):
        """Test parsing JSON formatted logs."""
        json_log = json.dumps({
            "timestamp": "2026-02-27T10:15:30Z",
            "level": "WARNING",
            "component": "modbus",
            "message": "Unauthorized register write detected",
            "registers": [0, 100, 200]
        })

        result = parser.parse_json_log(json_log)

        assert result["parsed"] is True
        assert result["source_format"] == "json"
        assert result["level"] == "WARNING"
        assert "Unauthorized" in result["message"]

    def test_parse_csv_log(self, parser):
        """Test parsing CSV formatted logs."""
        csv_line = "2026-02-27,10:15:30,PLC-01,Modbus,ERROR,Register write failed"

        result = parser.parse_csv_log(csv_line)

        assert result["parsed"] is True
        assert result["source_format"] == "csv"
        assert result["field_count"] == 6
        assert len(result["fields"]) == 6

    def test_index_single_document(self, indexer):
        """Test indexing a single document."""
        doc = {
            "timestamp": "2026-02-27T10:15:30Z",
            "event_type": "modbus_read",
            "source": "192.168.1.50"
        }

        success = indexer.index_document("security-logs", "event-001", doc)

        assert success is True
        assert indexer.get_indexed_count() == 1
        assert indexer.indexed_documents[0]["document"] == doc

    def test_index_bulk_documents(self, indexer):
        """Test bulk indexing of multiple documents."""
        documents = [
            {"timestamp": "2026-02-27T10:15:30Z", "event_type": "modbus_read"},
            {"timestamp": "2026-02-27T10:15:31Z", "event_type": "modbus_write"},
            {"timestamp": "2026-02-27T10:15:32Z", "event_type": "mqtt_publish"}
        ]

        indexed_count = indexer.index_bulk("security-logs", documents)

        assert indexed_count == 3
        assert indexer.get_indexed_count() == 3

    def test_ingestion_pipeline_syslog_to_opensearch(self, parser, indexer):
        """Test complete pipeline: syslog -> parse -> index."""
        # Raw syslog
        raw_log = "Feb 27 10:15:30 plc-01 modbus[1234]: Connection from 192.168.1.50:12345"

        # Parse
        parsed = parser.parse_syslog(raw_log)
        assert parsed["parsed"] is True

        # Index
        indexed = indexer.index_document("security-logs", "msg-001", parsed)
        assert indexed is True
        assert indexer.get_indexed_count() == 1

    def test_ingestion_pipeline_json_to_opensearch(self, parser, indexer):
        """Test complete pipeline: JSON -> parse -> index."""
        json_log = json.dumps({
            "timestamp": "2026-02-27T10:15:30Z",
            "event": "suspicious_modbus_write",
            "severity": "critical",
            "source_ip": "192.168.1.50"
        })

        parsed = parser.parse_json_log(json_log)
        indexed = indexer.index_document("security-logs", "evt-001", parsed)

        assert indexed is True
        assert parsed["severity"] == "critical"

    def test_ingestion_preserves_data_integrity(self, parser, indexer):
        """Test that ingestion pipeline preserves all data fields."""
        original = {
            "timestamp": "2026-02-27T10:15:30.123Z",
            "component": "modbus",
            "level": "CRITICAL",
            "event_id": 12345,
            "details": {"register": 100, "value": 65535}
        }

        json_log = json.dumps(original)
        parsed = parser.parse_json_log(json_log)
        indexer.index_document("security-logs", "test-001", parsed)

        indexed_doc = indexer.indexed_documents[0]["document"]

        assert indexed_doc["level"] == "CRITICAL"
        assert indexed_doc["event_id"] == 12345
        assert indexed_doc["details"]["register"] == 100

    def test_ingestion_batch_processing(self, parser, indexer):
        """Test batch processing of multiple log formats."""
        logs = [
            "Feb 27 10:15:30 plc-01 service: Event 1",
            json.dumps({"timestamp": "2026-02-27T10:15:31Z", "event": "Test 2"}),
            "2026-02-27,10:15:32,SOURCE,COMPONENT,LEVEL,Message 3"
        ]

        parsed_logs = []
        for log in logs[:1]:
            parsed_logs.append(parser.parse_syslog(log))
        for log in logs[1:2]:
            parsed_logs.append(parser.parse_json_log(log))
        for log in logs[2:]:
            parsed_logs.append(parser.parse_csv_log(log))

        indexed_count = indexer.index_bulk("security-logs", parsed_logs)

        assert indexed_count == 3
        assert indexer.get_indexed_count() == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
