"""
Anomaly Detection Inference
============================
Loads trained Isolation Forest model and scores incoming network flows.
Returns anomaly scores for each flow (0-1, higher = more anomalous).

Author: HungryHoundDog Team
"""

import logging
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


class AnomalyPredictor:
    """Perform anomaly detection on network flows."""
    
    def __init__(self, model_path: str = "./detection/ml/models", model_name: str = "isolation_forest_v1"):
        """
        Initialize the predictor with trained model.
        
        Args:
            model_path: Path to trained models
            model_name: Name of the model to load
        """
        self.model_path = model_path
        self.model_name = model_name
        self.model = None
        self.scaler = None
        self.threshold = 0.5
        
        self._load_model()
    
    def _load_model(self) -> None:
        """Load trained model and scaler from disk."""
        try:
            model_file = f"{self.model_path}/{self.model_name}.joblib"
            scaler_file = f"{self.model_path}/{self.model_name}_scaler.joblib"
            
            self.model = joblib.load(model_file)
            self.scaler = joblib.load(scaler_file)
            
            logger.info(f"Loaded model from {model_file}")
            
        except FileNotFoundError:
            logger.error(f"Model file not found: {model_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def predict_flow(self, flow: Dict) -> Tuple[float, bool]:
        """
        Score a single network flow for anomalies.
        
        Args:
            flow: Flow record dictionary
            
        Returns:
            Tuple of (anomaly_score, is_anomalous)
        """
        try:
            # Extract features
            X = self._extract_features_single(flow)
            
            # Scale features
            X_scaled = self.scaler.transform(X.reshape(1, -1))
            
            # Get anomaly score (negative = normal, positive = anomalous)
            score = self.model.score_samples(X_scaled)[0]
            
            # Normalize score to 0-1 range
            anomaly_score = 1.0 / (1.0 + np.exp(-score))
            
            is_anomalous = anomaly_score > self.threshold
            
            return float(anomaly_score), is_anomalous
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return 0.5, False
    
    def predict_batch(self, flows: List[Dict]) -> List[Dict]:
        """
        Score multiple flows for anomalies.
        
        Args:
            flows: List of flow records
            
        Returns:
            List of dictionaries with original flow + anomaly_score and is_anomalous
        """
        results = []
        
        try:
            # Extract features for all flows
            X_list = []
            valid_indices = []
            
            for i, flow in enumerate(flows):
                try:
                    X = self._extract_features_single(flow)
                    X_list.append(X)
                    valid_indices.append(i)
                except Exception as e:
                    logger.warning(f"Error extracting features from flow {i}: {str(e)}")
                    continue
            
            if not X_list:
                logger.warning("No valid features extracted")
                return results
            
            # Stack features
            X = np.array(X_list)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Get anomaly scores
            scores = self.model.score_samples(X_scaled)
            
            # Convert to anomaly scores (0-1)
            anomaly_scores = 1.0 / (1.0 + np.exp(-scores))
            
            # Build results
            for idx, flow_idx in enumerate(valid_indices):
                flow = flows[flow_idx].copy()
                flow["anomaly_score"] = float(anomaly_scores[idx])
                flow["is_anomalous"] = anomaly_scores[idx] > self.threshold
                results.append(flow)
            
            logger.info(f"Scored {len(results)} flows")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch prediction error: {str(e)}")
            return results
    
    def _extract_features_single(self, flow: Dict) -> np.ndarray:
        """
        Extract numerical features from a single flow.
        
        Args:
            flow: Flow record dictionary
            
        Returns:
            Feature vector as numpy array
        """
        bytes_in = float(flow.get("bytes_in", 0))
        bytes_out = float(flow.get("bytes_out", 0))
        packet_count = float(flow.get("packet_count", 0))
        duration = float(flow.get("duration_seconds", 0.001))
        src_port = float(flow.get("src_port", 0))
        dst_port = float(flow.get("dst_port", 0))
        
        # Derived features
        bytes_ratio = bytes_out / (bytes_in + 1)
        packet_rate = packet_count / (duration + 0.001)
        bytes_per_packet = (bytes_in + bytes_out) / (packet_count + 1)
        
        # Temporal feature
        hour_of_day = 12  # Default to noon if not provided
        if "timestamp" in flow:
            try:
                import pandas as pd
                ts = pd.to_datetime(flow["timestamp"])
                hour_of_day = ts.hour
            except:
                pass
        
        features = np.array([
            bytes_in, bytes_out, packet_count, duration,
            src_port, dst_port, bytes_ratio, packet_rate,
            bytes_per_packet, float(hour_of_day)
        ])
        
        # Handle NaN/Inf values
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features
    
    def set_threshold(self, threshold: float) -> None:
        """
        Set anomaly score threshold for classification.
        
        Args:
            threshold: Score threshold (0-1), higher = stricter
        """
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        
        self.threshold = threshold
        logger.info(f"Anomaly threshold set to {threshold}")


def score_flow(flow: Dict, predictor: Optional[AnomalyPredictor] = None) -> Tuple[float, bool]:
    """
    Convenience function to score a single flow.
    
    Args:
        flow: Flow record
        predictor: Optional AnomalyPredictor instance
        
    Returns:
        Tuple of (anomaly_score, is_anomalous)
    """
    if predictor is None:
        predictor = AnomalyPredictor()
    
    return predictor.predict_flow(flow)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    predictor = AnomalyPredictor()
    
    example_flow = {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.50",
        "src_port": 54321,
        "dst_port": 80,
        "protocol": "tcp",
        "bytes_in": 5000,
        "bytes_out": 1000,
        "packet_count": 50,
        "duration_seconds": 10.5,
        "timestamp": "2024-01-15T14:30:00Z"
    }
    
    score, anomalous = predictor.predict_flow(example_flow)
    print(f"Anomaly Score: {score:.4f}, Anomalous: {anomalous}")
