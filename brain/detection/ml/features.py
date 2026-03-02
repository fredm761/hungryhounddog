"""
Feature Extraction for Anomaly Detection
=========================================
Extract numerical features from network flow data for ML models.
Includes feature engineering, normalization, and importance analysis.

Author: HungryHoundDog Team
"""

import logging
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract and engineer features from network flow data."""
    
    # Feature definitions
    BASIC_FEATURES = [
        "bytes_in", "bytes_out", "packet_count", "duration_seconds",
        "src_port", "dst_port"
    ]
    
    DERIVED_FEATURES = [
        "bytes_ratio", "packet_rate", "bytes_per_packet", "bytes_ratio_inv",
        "port_entropy", "is_privileged_port_src", "is_privileged_port_dst"
    ]
    
    TEMPORAL_FEATURES = [
        "hour_of_day", "day_of_week", "is_business_hours"
    ]
    
    PROTOCOL_FEATURES = [
        "is_tcp", "is_udp", "is_icmp", "is_dns", "is_http", "is_https"
    ]
    
    ALL_FEATURES = BASIC_FEATURES + DERIVED_FEATURES + TEMPORAL_FEATURES + PROTOCOL_FEATURES
    
    def __init__(self):
        """Initialize feature extractor."""
        self.feature_stats = {}
        self.feature_importance = {}
    
    def extract(self, flow: Dict) -> Dict[str, float]:
        """
        Extract all features from a single flow.
        
        Args:
            flow: Flow record dictionary
            
        Returns:
            Dictionary with feature names and values
        """
        features = {}
        
        try:
            # Basic features
            features.update(self._extract_basic(flow))
            
            # Derived features
            features.update(self._extract_derived(flow, features))
            
            # Temporal features
            features.update(self._extract_temporal(flow))
            
            # Protocol features
            features.update(self._extract_protocol(flow))
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
        
        return features
    
    def extract_batch(self, flows: List[Dict]) -> pd.DataFrame:
        """
        Extract features from multiple flows.
        
        Args:
            flows: List of flow records
            
        Returns:
            DataFrame with features
        """
        features_list = []
        
        for flow in flows:
            features = self.extract(flow)
            features_list.append(features)
        
        df = pd.DataFrame(features_list)
        
        logger.info(f"Extracted features for {len(df)} flows")
        
        return df
    
    def _extract_basic(self, flow: Dict) -> Dict[str, float]:
        """Extract basic network features."""
        return {
            "bytes_in": float(flow.get("bytes_in", 0)),
            "bytes_out": float(flow.get("bytes_out", 0)),
            "packet_count": float(flow.get("packet_count", 0)),
            "duration_seconds": float(flow.get("duration_seconds", 0.001)),
            "src_port": float(flow.get("src_port", 0)),
            "dst_port": float(flow.get("dst_port", 0))
        }
    
    def _extract_derived(self, flow: Dict, basic_features: Dict) -> Dict[str, float]:
        """Extract derived/engineered features."""
        features = {}
        
        bytes_in = basic_features.get("bytes_in", 0)
        bytes_out = basic_features.get("bytes_out", 0)
        packet_count = basic_features.get("packet_count", 0)
        duration = basic_features.get("duration_seconds", 0.001)
        src_port = basic_features.get("src_port", 0)
        dst_port = basic_features.get("dst_port", 0)
        
        total_bytes = bytes_in + bytes_out
        
        # Ratio features
        features["bytes_ratio"] = bytes_out / (bytes_in + 1)
        features["bytes_ratio_inv"] = bytes_in / (bytes_out + 1)
        
        # Rate features
        features["packet_rate"] = packet_count / (duration + 0.001)
        features["bytes_per_packet"] = total_bytes / (packet_count + 1)
        features["bytes_per_second"] = total_bytes / (duration + 0.001)
        
        # Port features
        features["is_privileged_port_src"] = 1.0 if src_port < 1024 else 0.0
        features["is_privileged_port_dst"] = 1.0 if dst_port < 1024 else 0.0
        
        # Port entropy (rough approximation)
        features["port_entropy"] = (src_port + dst_port) / 65536.0
        
        # Flow symmetry
        if total_bytes > 0:
            features["flow_symmetry"] = min(bytes_in, bytes_out) / max(bytes_in, bytes_out, 1)
        else:
            features["flow_symmetry"] = 0.0
        
        return features
    
    def _extract_temporal(self, flow: Dict) -> Dict[str, float]:
        """Extract temporal features."""
        features = {}
        
        try:
            timestamp = flow.get("timestamp")
            if timestamp:
                dt = pd.to_datetime(timestamp)
            else:
                dt = pd.Timestamp.now()
            
            features["hour_of_day"] = float(dt.hour)
            features["day_of_week"] = float(dt.dayofweek)
            features["day_of_month"] = float(dt.day)
            
            # Business hours indicator (9am-5pm, Mon-Fri)
            is_business_day = dt.dayofweek < 5
            is_business_hour = 9 <= dt.hour < 17
            features["is_business_hours"] = 1.0 if (is_business_day and is_business_hour) else 0.0
            
        except Exception as e:
            logger.warning(f"Error extracting temporal features: {str(e)}")
            features["hour_of_day"] = 12.0
            features["day_of_week"] = 3.0
            features["day_of_month"] = 15.0
            features["is_business_hours"] = 0.5
        
        return features
    
    def _extract_protocol(self, flow: Dict) -> Dict[str, float]:
        """Extract protocol features."""
        features = {}
        
        protocol = flow.get("protocol", "").upper()
        dst_port = int(flow.get("dst_port", 0))
        
        # Protocol features
        features["is_tcp"] = 1.0 if protocol == "TCP" else 0.0
        features["is_udp"] = 1.0 if protocol == "UDP" else 0.0
        features["is_icmp"] = 1.0 if protocol == "ICMP" else 0.0
        
        # Application layer inference
        features["is_dns"] = 1.0 if dst_port == 53 else 0.0
        features["is_http"] = 1.0 if dst_port == 80 else 0.0
        features["is_https"] = 1.0 if dst_port == 443 else 0.0
        features["is_modbus"] = 1.0 if dst_port in [502, 20000] else 0.0
        features["is_mqtt"] = 1.0 if dst_port in [1883, 8883] else 0.0
        
        return features
    
    def compute_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Compute statistics for features.
        
        Args:
            df: DataFrame with features
            
        Returns:
            Dictionary with feature statistics
        """
        stats = {}
        
        for col in df.columns:
            stats[col] = {
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "median": float(df[col].median())
            }
        
        self.feature_stats = stats
        return stats
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.
        
        Returns:
            Dictionary with feature importance values
        """
        # Mock importance based on variance
        importance = {}
        
        for name, stats in self.feature_stats.items():
            # Features with high variance are more important
            variance = stats["std"] ** 2
            importance[name] = variance
        
        self.feature_importance = importance
        return importance


def extract_features_for_flow(flow: Dict) -> Dict[str, float]:
    """
    Convenience function to extract features from a flow.
    
    Args:
        flow: Flow record dictionary
        
    Returns:
        Dictionary with extracted features
    """
    extractor = FeatureExtractor()
    return extractor.extract(flow)


def extract_features_for_flows(flows: List[Dict]) -> pd.DataFrame:
    """
    Convenience function to extract features from multiple flows.
    
    Args:
        flows: List of flow records
        
    Returns:
        DataFrame with extracted features
    """
    extractor = FeatureExtractor()
    return extractor.extract_batch(flows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    sample_flow = {
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
    
    extractor = FeatureExtractor()
    features = extractor.extract(sample_flow)
    
    print("Extracted Features:")
    for name, value in sorted(features.items()):
        print(f"  {name}: {value:.4f}")
