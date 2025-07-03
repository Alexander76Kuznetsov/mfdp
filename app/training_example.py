#!/usr/bin/env python3
"""
Example script showing how to use the model training system.

This script demonstrates how to:
1. Start a training job
2. Monitor training progress
3. Use trained models for predictions
"""

import requests
import json
import time
from typing import Dict, Any


class TrainingClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def login(self, email: str, password: str) -> bool:
        """Login to get authentication cookie"""
        login_data = {
            "username": email,
            "password": password
        }
        response = self.session.post(f"{self.base_url}/token", data=login_data)
        if response.status_code == 200:
            print("Login successful")
            return True
        else:
            print(f"Login failed: {response.text}")
            return False
    
    def start_training(self, model_type: str, data_path: str, 
                      iterations: int = 10, factors: int = 60) -> int:
        """Start a new training job"""
        training_data = {
            "model_type": model_type,
            "data_path": data_path,
            "iterations": iterations,
            "factors": factors
        }
        
        response = self.session.post(f"{self.base_url}/start_training/", data=training_data)
        if response.status_code == 200:
            print("Training job started successfully")
            # Extract job ID from response (you might need to parse the HTML response)
            # For now, we'll return a placeholder
            return 1
        else:
            print(f"Failed to start training: {response.text}")
            return None
    
    def get_training_status(self, job_id: int) -> Dict[str, Any]:
        """Get training job status and metrics"""
        response = self.session.get(f"{self.base_url}/training_status/{job_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get status: {response.text}")
            return None
    
    def wait_for_completion(self, job_id: int, timeout: int = 3600) -> Dict[str, Any]:
        """Wait for training job to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_training_status(job_id)
            if status:
                print(f"Job {job_id} status: {status['status']}")
                
                if status['status'] == 'completed':
                    print("Training completed successfully!")
                    return status
                elif status['status'] == 'failed':
                    print("Training failed!")
                    return status
                
                time.sleep(30)  # Check every 30 seconds
            else:
                time.sleep(10)
        
        print("Timeout waiting for training completion")
        return None


def main():
    """Example usage of the training system"""
    
    # Initialize client
    client = TrainingClient()
    
    # Login (replace with your credentials)
    if not client.login("test@example.com", "123"):
        return
    
    # Example 1: Train a simple popular items model
    print("\n=== Training Popular Items Model ===")
    job_id = client.start_training(
        model_type="popular",
        data_path="/data"  # Path to your data directory
    )
    
    if job_id:
        result = client.wait_for_completion(job_id)
        if result and result.get('metrics'):
            metrics = result['metrics']
            print(f"Popular model metrics:")
            print(f"  Recall@40: {metrics['recall_at_k']:.4f}")
            print(f"  Precision@40: {metrics['precision_at_k']:.4f}")
            print(f"  F1@40: {metrics['f1_at_k']:.4f}")
    
    # Example 2: Train an ALS model with custom parameters
    print("\n=== Training ALS Model ===")
    job_id = client.start_training(
        model_type="als",
        data_path="/data",
        iterations=15,
        factors=80
    )
    
    if job_id:
        result = client.wait_for_completion(job_id)
        if result and result.get('metrics'):
            metrics = result['metrics']
            print(f"ALS model metrics:")
            print(f"  Recall@40: {metrics['recall_at_k']:.4f}")
            print(f"  Precision@40: {metrics['precision_at_k']:.4f}")
            print(f"  F1@40: {metrics['f1_at_k']:.4f}")
            print(f"  Model saved to: {result.get('model_path', 'N/A')}")


if __name__ == "__main__":
    main() 