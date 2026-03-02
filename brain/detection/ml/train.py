"""
Anomaly Detection Model Training
=================================
Trains Isolation Forest model on baseline network traffic features.
Model is saved as joblib file for later inference.

Author: HungryHoundDog Team
"""

import logging
from typing import Tuple, List
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from opensearchpy import OpenSearch

logger = logging.getLogger(__name__)


class AnomalyModelTrainer:
    """Train anomaly detection models from network flow data."""
    
    def __init__(self, opensearch_client: OpenSearch, model_path: str = "./detection/ml/models"):
        """
        Initialize the model trainer.
        
        Args:
            opensearch_client: OpenSearch client for data retrieval
            model_path: Path to save trained models
        """
        self.opensearch = opensearch_client
        self.model_path = model_path
        self.scaler = StandardScaler()
        self.model = None
        
    def fetch_training_data(self, days: int = 7, index: str = "network-flows") -> pd.DataFrame:
        """
        Fetch baseline network flow data from OpenSearch.
        
        Args:
            days: Number of days of historical data to fetch
            index: Index name to query
            
        Returns:
            DataFrame with network flow features
        """
        try:
            # Build query for last N days of data
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": f"now-{days}d",
                            "lte": "now"
                        }
                    }
                },
                "size": 10000,
                "_source": [
                    "src_ip", "dst_ip", "src_port", "dst_port",
                    "protocol", "bytes_in", "bytes_out", "packet_count",
                    "duration_seconds", "timestamp"
                ]
            }
            
            results = self.opensearch.search(index=index, body=query)
            
            # Convert to DataFrame
            data = []
            for hit in results["hits"]["hits"]:
                data.append(hit["_source"])
            
            df = pd.DataFrame(data)
            logger.info(f"Fetched {len(df)} training records from {index}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching training data: {str(e)}")
            raise
    
    def extract_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Extract numerical features from flow data.
        
        Args:
            df: DataFrame with flow records
            
        Returns:
            Tuple of (feature_matrix, feature_names)
        """
        features = []
        feature_names = [
            "bytes_in", "bytes_out", "packet_count", "duration_seconds",
            "src_port", "dst_port", "bytes_ratio", "packet_rate",
            "bytes_per_packet", "hour_of_day"
        ]
        
        df_copy = df.copy()
        
        # Numerical features
        df_copy["bytes_in"] = pd.to_numeric(df_copy["bytes_in"], errors="coerce").fillna(0)
        df_copy["bytes_out"] = pd.to_numeric(df_copy["bytes_out"], errors="coerce").fillna(0)
        df_copy["packet_count"] = pd.to_numeric(df_copy["packet_count"], errors="coerce").fillna(0)
        df_copy["duration_seconds"] = pd.to_numeric(df_copy["duration_seconds"], errors="coerce").fillna(0.001)
        
        # Port features
        df_copy["src_port"] = pd.to_numeric(df_copy["src_port"], errors="coerce").fillna(0)
        df_copy["dst_port"] = pd.to_numeric(df_copy["dst_port"], errors="coerce").fillna(0)
        
        # Derived features
        df_copy["bytes_ratio"] = (
            df_copy["bytes_out"] / (df_copy["bytes_in"] + 1)
        ).clip(0, 100)
        
        df_copy["packet_rate"] = (
            df_copy["packet_count"] / (df_copy["duration_seconds"] + 0.001)
        ).clip(0, 10000)
        
        df_copy["bytes_per_packet"] = (
            (df_copy["bytes_in"] + df_copy["bytes_out"]) / (df_copy["packet_count"] + 1)
        ).clip(0, 65535)
        
        # Temporal feature
        df_copy["timestamp"] = pd.to_datetime(df_copy["timestamp"], errors="coerce")
        df_copy["hour_of_day"] = df_copy["timestamp"].dt.hour
        
        # Build feature matrix
        feature_cols = [
            "bytes_in", "bytes_out", "packet_count", "duration_seconds",
            "src_port", "dst_port", "bytes_ratio", "packet_rate",
            "bytes_per_packet", "hour_of_day"
        ]
        
        X = df_copy[feature_cols].values
        
        # Handle NaN values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        logger.info(f"Extracted {X.shape[0]} samples with {X.shape[1]} features")
        
        return X, feature_names
    
    def train(self, X: np.ndarray, contamination: float = 0.05) -> IsolationForest:
        """
        Train Isolation Forest model.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            contamination: Expected proportion of outliers
            
        Returns:
            Trained IsolationForest model
        """
        logger.info(f"Training Isolation Forest with contamination={contamination}")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            max_samples="auto",
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1
        )
        
        self.model.fit(X_scaled)
        
        logger.info("Model training complete")
        return self.model
    
    def save_model(self, model_name: str = "isolation_forest_v1"):
        """
        Save trained model and scaler to disk.
        
        Args:
            model_name: Name for the saved model
        """
        if self.model is None:
            raise ValueError("No model trained yet")
        
        try:
            model_file = f"{self.model_path}/{model_name}.joblib"
            scaler_file = f"{self.model_path}/{model_name}_scaler.joblib"
            
            joblib.dump(self.model, model_file)
            joblib.dump(self.scaler, scaler_file)
            
            logger.info(f"Model saved to {model_file}")
            logger.info(f"Scaler saved to {scaler_file}")
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise


def train_anomaly_model(opensearch_client: OpenSearch) -> None:
    """
    Main training pipeline.
    
    Args:
        opensearch_client: OpenSearch client
    """
    try:
        trainer = AnomalyModelTrainer(opensearch_client)
        
        # Fetch data
        df = trainer.fetch_training_data(days=7)
        
        if len(df) == 0:
            logger.warning("No training data available")
            return
        
        # Extract features
        X, feature_names = trainer.extract_features(df)
        
        # Train model
        trainer.train(X, contamination=0.05)
        
        # Save model
        trainer.save_model("isolation_forest_v1")
        
        logger.info("Anomaly model training pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Training pipeline failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    from opensearchpy import OpenSearch
    
    logging.basicConfig(level=logging.INFO)
    
    # Initialize OpenSearch client
    client = OpenSearch(
        hosts=[{"host": "opensearch", "port": 9200}],
        use_ssl=False,
        verify_certs=False
    )
    
    train_anomaly_model(client)
