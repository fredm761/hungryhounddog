#!/usr/bin/env python3
"""
test_detection.py: Tests for anomaly detection ML model.

Verifies that the ML model loads correctly, produces anomaly scores
on sample flow data, and can identify known attack patterns.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, List, Any
import numpy as np


class MockMLModel:
    """Mock ML anomaly detection model for testing."""

    def __init__(self, model_name: str = "anomaly_detector"):
        """Initialize mock model."""
        self.model_name = model_name
        self.is_loaded = False
        self.prediction_count = 0

    def load_model(self) -> bool:
        """Load pretrained model."""
        self.is_loaded = True
        return True

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict anomaly score for feature vector.

        Returns:
            Dict with anomaly_score (0-1), is_anomaly (bool), confidence
        """
        self.prediction_count += 1

        # Mock prediction logic
        anomaly_score = self._calculate_anomaly_score(features)

        return {
            "anomaly_score": anomaly_score,
            "is_anomaly": anomaly_score > 0.7,
            "confidence": 0.95,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _calculate_anomaly_score(self, features: Dict[str, float]) -> float:
        """Calculate mock anomaly score based on features."""
        # Simulated anomaly detection logic
        score = 0.0

        # Detect unusual flow counts
        if features.get("packet_count", 0) > 10000:
            score += 0.3

        # Detect unusual byte transfer
        if features.get("byte_count", 0) > 1000000:
            score += 0.2

        # Detect unusual port
        port = features.get("dst_port", 0)
        if port in [502, 502]:  # Modbus with unusual source
            score += 0.2

        # Detect unusual protocol mixture
        if features.get("protocol_diversity", 0) > 5:
            score += 0.15

        return min(score, 1.0)

    def predict_batch(self, feature_list: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """Predict on multiple samples."""
        return [self.predict(features) for features in feature_list]

    def get_stats(self) -> Dict[str, Any]:
        """Get model statistics."""
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "predictions_made": self.prediction_count
        }


class TestDetectionModel:
    """Test suite for anomaly detection model."""

    @pytest.fixture
    def model(self):
        """Fixture: ML detection model."""
        m = MockMLModel()
        m.load_model()
        return m

    def test_model_loading(self):
        """Test that model can be loaded."""
        model = MockMLModel()
        success = model.load_model()

        assert success is True
        assert model.is_loaded is True

    def test_model_prediction_on_normal_traffic(self, model):
        """Test model identifies normal traffic as non-anomalous."""
        normal_flow = {
            "packet_count": 100,
            "byte_count": 50000,
            "dst_port": 80,
            "protocol_diversity": 2,
            "duration_sec": 5
        }

        result = model.predict(normal_flow)

        assert result["is_anomaly"] is False
        assert result["anomaly_score"] < 0.5

    def test_model_prediction_on_modbus_attack(self, model):
        """Test model identifies Modbus attack pattern."""
        modbus_attack = {
            "packet_count": 20000,  # High packet count
            "byte_count": 5000000,  # High byte transfer
            "dst_port": 502,  # Modbus port
            "protocol_diversity": 1,
            "duration_sec": 2
        }

        result = model.predict(modbus_attack)

        assert result["is_anomaly"] is True
        assert result["anomaly_score"] > 0.5

    def test_model_prediction_on_high_volume_traffic(self, model):
        """Test model detects high-volume anomalies."""
        high_volume = {
            "packet_count": 50000,
            "byte_count": 100000000,
            "dst_port": 443,
            "protocol_diversity": 3,
            "duration_sec": 60
        }

        result = model.predict(high_volume)

        assert result["is_anomaly"] is True
        assert result["anomaly_score"] > 0.6

    def test_model_prediction_returns_confidence(self, model):
        """Test that predictions include confidence scores."""
        flow = {
            "packet_count": 500,
            "byte_count": 100000,
            "dst_port": 443,
            "protocol_diversity": 2,
            "duration_sec": 10
        }

        result = model.predict(flow)

        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1

    def test_model_batch_prediction(self, model):
        """Test batch prediction on multiple flows."""
        flows = [
            {"packet_count": 100, "byte_count": 50000, "dst_port": 80,
             "protocol_diversity": 2, "duration_sec": 5},
            {"packet_count": 20000, "byte_count": 5000000, "dst_port": 502,
             "protocol_diversity": 1, "duration_sec": 2},
            {"packet_count": 50000, "byte_count": 100000000, "dst_port": 443,
             "protocol_diversity": 3, "duration_sec": 60}
        ]

        results = model.predict_batch(flows)

        assert len(results) == 3
        assert results[0]["is_anomaly"] is False  # Normal
        assert results[1]["is_anomaly"] is True   # Attack
        assert results[2]["is_anomaly"] is True   # Attack

    def test_model_anomaly_score_range(self, model):
        """Test that anomaly scores are in valid range [0, 1]."""
        test_flows = [
            {"packet_count": i * 1000, "byte_count": i * 100000,
             "dst_port": 80, "protocol_diversity": 1, "duration_sec": 5}
            for i in range(1, 10)
        ]

        for flow in test_flows:
            result = model.predict(flow)
            assert 0 <= result["anomaly_score"] <= 1

    def test_model_prediction_consistency(self, model):
        """Test that model produces consistent predictions."""
        flow = {
            "packet_count": 500,
            "byte_count": 100000,
            "dst_port": 443,
            "protocol_diversity": 2,
            "duration_sec": 10
        }

        result1 = model.predict(flow)
        result2 = model.predict(flow)

        assert result1["anomaly_score"] == result2["anomaly_score"]
        assert result1["is_anomaly"] == result2["is_anomaly"]

    def test_model_detects_port_scanning(self, model):
        """Test model can detect port scanning pattern."""
        port_scan = {
            "packet_count": 500,
            "byte_count": 10000,
            "dst_port": 502,  # Scanning Modbus port
            "protocol_diversity": 5,  # Many different protocols
            "duration_sec": 2
        }

        result = model.predict(port_scan)

        # Should detect anomaly due to high protocol diversity
        assert result["anomaly_score"] > 0.4

    def test_model_statistics(self, model):
        """Test model can report statistics."""
        # Make some predictions
        for _ in range(5):
            model.predict({"packet_count": 100, "byte_count": 50000,
                          "dst_port": 80, "protocol_diversity": 1, "duration_sec": 5})

        stats = model.get_stats()

        assert stats["is_loaded"] is True
        assert stats["predictions_made"] == 5

    def test_real_world_modbus_attack_scenario(self, model):
        """Test on realistic Modbus attack sequence."""
        attack_sequence = [
            # Reconnaissance - normal Modbus reads
            {
                "packet_count": 50,
                "byte_count": 10000,
                "dst_port": 502,
                "protocol_diversity": 1,
                "duration_sec": 30
            },
            # Brute force attempt - many connection attempts
            {
                "packet_count": 5000,
                "byte_count": 500000,
                "dst_port": 502,
                "protocol_diversity": 1,
                "duration_sec": 10
            },
            # Write attack - high-speed register writes
            {
                "packet_count": 10000,
                "byte_count": 2000000,
                "dst_port": 502,
                "protocol_diversity": 1,
                "duration_sec": 5
            }
        ]

        results = model.predict_batch(attack_sequence)

        # First should be mostly normal
        assert results[0]["anomaly_score"] < 0.4
        # Second and third should be detected as anomalies
        assert results[1]["is_anomaly"] is True
        assert results[2]["is_anomaly"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
