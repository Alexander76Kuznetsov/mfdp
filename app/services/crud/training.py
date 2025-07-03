from sqlmodel import Session
from models.all_models import MLModel, MLTask, TrainingJob
import polars as pl
# import implicit
from scipy.sparse import csr_matrix
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json


class TrainingService:
    def __init__(self):
        self.models_dir = "./ml_models"
        os.makedirs(self.models_dir, exist_ok=True)
    
    def create_training_job(self, job: TrainingJob, session: Session) -> TrainingJob:
        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    
    def get_training_job(self, job_id: int, session: Session) -> Optional[TrainingJob]:
        return session.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
    
    def update_training_job(self, job_id: int, status: str, session: Session, 
                           metrics: Optional[Dict] = None, model_path: Optional[str] = None) -> TrainingJob:
        job = self.get_training_job(job_id, session)
        if job:
            job.status = status
            if metrics:
                job.metrics = json.dumps(metrics)
            if model_path:
                job.model_path = model_path
            job.updated_at = datetime.utcnow().isoformat()
            session.commit()
            session.refresh(job)
        return job
    
    def load_data(self, data_path: str) -> Dict[str, pl.DataFrame]:
        """Load training data from parquet files"""
        try:
            clickstream = pl.read_parquet(f'{data_path}/clickstream.pq')
            events = pl.read_parquet(f'{data_path}/events.pq')
            
            return {
                'clickstream': clickstream,
                'events': events
            }
        except Exception as e:
            raise Exception(f"Error loading data: {e}")
    
    def preprocess_data(self, data: Dict[str, pl.DataFrame], eval_days: int = 14) -> Dict[str, pl.DataFrame]:
        """Preprocess data for training"""
        clickstream = data['clickstream']
        events = data['events']
        
        # Split into train/eval
        threshold = clickstream['event_date'].max() - timedelta(days=eval_days)
        
        df_train = clickstream.filter(clickstream['event_date'] <= threshold)
        df_eval = clickstream.filter(clickstream['event_date'] > threshold)[['cookie', 'node', 'event']]
        df_eval = df_eval.join(df_train, on=['cookie', 'node'], how='anti')
        
        # Filter evaluation data
        contact_events = events.filter(pl.col('is_contact') == 1)['event'].unique()
        df_eval = df_eval.filter(pl.col('event').is_in(contact_events))
        df_eval = df_eval.filter(pl.col('cookie').is_in(df_train['cookie'].unique()))
        df_eval = df_eval.filter(pl.col('node').is_in(df_train['node'].unique()))
        df_eval = df_eval.unique(['cookie', 'node'])
        
        return {
            'train': df_train,
            'eval': df_eval
        }
    
    def train_popular_model(self, df_train: pl.DataFrame, df_eval: pl.DataFrame) -> Dict[str, float]:
        """Train simple popular items model"""
        popular_nodes = df_train.group_by('node').agg(pl.col('cookie').count()).sort('cookie').tail(40)['node'].to_list()
        eval_users = df_eval['cookie'].unique().to_list()
        
        df_pred_pop = pl.DataFrame({
            'node': [popular_nodes for _ in range(len(eval_users))], 
            'cookie': eval_users
        })
        df_pred_pop = df_pred_pop.explode('node')
        
        metrics = self.calculate_metrics(df_eval, df_pred_pop, k=40)
        return metrics
    
    def train_als_model(self, df_train: pl.DataFrame, df_eval: pl.DataFrame, 
                       iterations: int = 10, factors: int = 60) -> Dict[str, Any]:
        """Train ALS collaborative filtering model"""
        users = df_train["cookie"]
        nodes = df_train["node"]
        eval_users = df_eval['cookie'].unique().to_list()
        
        # Create mappings
        user_ids = users.unique().to_list()
        item_ids = nodes.unique().to_list()
        
        user_id_to_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
        item_id_to_index = {item_id: idx for idx, item_id in enumerate(item_ids)}
        index_to_item_id = {v: k for k, v in item_id_to_index.items()}
        
        # Create sparse matrix
        rows = users.replace_strict(user_id_to_index).to_list()
        cols = nodes.replace_strict(item_id_to_index).to_list()
        values = [1] * len(users)
        
        sparse_matrix = csr_matrix((values, (rows, cols)), shape=(len(user_ids), len(item_ids)))
        
        # Train model
        model = implicit.als.AlternatingLeastSquares(iterations=iterations, factors=factors)
        model.fit(sparse_matrix)
        
        # Generate predictions
        user4pred = np.array([user_id_to_index[i] for i in eval_users])
        recommendations, scores = model.recommend(user4pred, sparse_matrix[user4pred], N=40, filter_already_liked_items=True)
        
        df_pred = pl.DataFrame({
            'node': [[index_to_item_id[i] for i in rec] for rec in recommendations.tolist()],
            'cookie': list(eval_users),
            'scores': scores.tolist()
        })
        df_pred = df_pred.explode(['node', 'scores'])
        
        # Calculate metrics
        metrics = self.calculate_metrics(df_eval, df_pred, k=40)
        
        # Save model
        model_data = {
            'model': model,
            'user_id_to_index': user_id_to_index,
            'item_id_to_index': item_id_to_index,
            'index_to_item_id': index_to_item_id,
            'sparse_matrix': sparse_matrix
        }
        
        return {
            'metrics': metrics,
            'model_data': model_data
        }
    
    def calculate_metrics(self, df_true: pl.DataFrame, df_pred: pl.DataFrame, k: int = 40) -> Dict[str, float]:
        """Calculate Recall@K, Precision@K, and F1@K metrics"""
        # Recall@K
        recall_at_k = df_true[['node', 'cookie']].join(
            df_pred.group_by('cookie').head(k).with_columns(value=1)[['node', 'cookie', 'value']],
            how='left',
            on=['cookie', 'node']
        ).select([
            pl.col('value').fill_null(0), 'cookie'
        ]).group_by('cookie').agg([
            pl.col('value').sum() / pl.col('value').count()
        ])['value'].mean()
        
        # Precision@K
        precision_at_k = df_true[['node', 'cookie']].join(
            df_pred.group_by('cookie').head(k).with_columns(value=1)[['node', 'cookie', 'value']],
            how='left',
            on=['cookie', 'node']
        ).select([
            pl.col('value').fill_null(0), 'cookie'
        ]).group_by('cookie').agg([
            pl.col('value').sum() / k
        ])['value'].mean()
        
        # F1@K
        f1_at_k = 2 * (precision_at_k * recall_at_k) / (precision_at_k + recall_at_k)
        
        return {
            'recall_at_k': float(recall_at_k),
            'precision_at_k': float(precision_at_k),
            'f1_at_k': float(f1_at_k)
        }
    
    def save_model(self, model_data: Dict[str, Any], model_name: str) -> str:
        """Save trained model to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"{self.models_dir}/{model_name}_{timestamp}.pkl"
        
        joblib.dump(model_data, model_path)
        return model_path
    
    def train_model(self, job_id: int, session: Session, 
                   model_type: str, data_path: str, 
                   hyperparams: Optional[Dict] = None) -> Dict[str, Any]:
        """Main training function"""
        try:
            # Update job status
            self.update_training_job(job_id, "loading_data", session)
            
            # Load data
            data = self.load_data(data_path)
            
            # Update job status
            self.update_training_job(job_id, "preprocessing", session)
            
            # Preprocess data
            processed_data = self.preprocess_data(data)
            
            # Update job status
            self.update_training_job(job_id, "training", session)
            
            # Train model based on type
            if model_type == "popular":
                metrics = self.train_popular_model(processed_data['train'], processed_data['eval'])
                model_path = None  # Popular model doesn't need saving
            elif model_type == "als":
                hyperparams = hyperparams or {}
                result = self.train_als_model(
                    processed_data['train'], 
                    processed_data['eval'],
                    iterations=hyperparams.get('iterations', 10),
                    factors=hyperparams.get('factors', 60)
                )
                metrics = result['metrics']
                model_path = self.save_model(result['model_data'], f"als_model_{job_id}")
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Update job status
            self.update_training_job(job_id, "completed", session, metrics, model_path)
            
            return {
                'status': 'success',
                'metrics': metrics,
                'model_path': model_path
            }
            
        except Exception as e:
            self.update_training_job(job_id, "failed", session)
            raise Exception(f"Training failed: {e}") 