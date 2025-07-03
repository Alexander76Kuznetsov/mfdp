# Model Training System

This document explains how to use the model training capabilities added to the platform, based on the baseline notebook implementation.

## Overview

The training system allows you to train recommendation models similar to those in `baseline.ipynb`:

1. **Popular Items Model** - Simple baseline that recommends the most popular categories
2. **ALS Collaborative Filtering** - Advanced matrix factorization model using Alternating Least Squares

## Features

- **Web Interface** - Start training jobs through the browser
- **Background Processing** - Training runs in background workers
- **Real-time Status** - Monitor training progress
- **Model Versioning** - Track different model versions
- **Metrics Tracking** - Recall@40, Precision@40, F1@40 metrics
- **Hyperparameter Tuning** - Customize ALS parameters

## Quick Start

### 1. Start the Platform

```bash
docker-compose up -d
```

This starts:
- Main application
- Training worker
- Prediction worker  
- RabbitMQ message queue
- PostgreSQL database

### 2. Access Training Interface

1. Go to `http://localhost`
2. Login with test credentials: `test@example.com` / `123`
3. Click "Model Training" in the navigation

### 3. Start Training

1. Select model type (Popular or ALS)
2. Enter data path (e.g., `/data` for mounted data directory)
3. For ALS models, adjust iterations and factors
4. Click "Start Training"

### 4. Monitor Progress

- View training history table
- Click "Details" to see metrics and model path
- Training status updates automatically

## Data Requirements

Your data directory should contain:
- `clickstream.pq` - User interaction data
- `events.pq` - Event definitions with `is_contact` field

Data format should match the baseline notebook structure.

## Model Types

### Popular Items Model
- **Type**: Simple baseline
- **Algorithm**: Recommends most frequently interacted categories
- **Use Case**: Baseline comparison, simple recommendations
- **Training Time**: Very fast
- **No hyperparameters needed**

### ALS Collaborative Filtering
- **Type**: Advanced matrix factorization
- **Algorithm**: Alternating Least Squares
- **Use Case**: Personalized recommendations
- **Training Time**: Moderate (depends on data size)
- **Hyperparameters**:
  - `iterations`: Number of ALS iterations (default: 10)
  - `factors`: Number of latent factors (default: 60)

## API Endpoints

### Start Training
```http
POST /start_training/
Content-Type: application/x-www-form-urlencoded

model_type=als&data_path=/data&iterations=15&factors=80
```

### Get Training Status
```http
GET /training_status/{job_id}
```

Response:
```json
{
  "job_id": 1,
  "status": "completed",
  "metrics": {
    "recall_at_k": 0.152,
    "precision_at_k": 0.0093,
    "f1_at_k": 0.0175
  },
  "model_path": "./ml_models/als_model_1_20241201_143022.pkl",
  "created_at": "2024-12-01T14:30:22",
  "updated_at": "2024-12-01T14:35:45"
}
```

## Programmatic Usage

Use the provided `training_example.py` script:

```python
from training_example import TrainingClient

client = TrainingClient()
client.login("test@example.com", "123")

# Start training
job_id = client.start_training(
    model_type="als",
    data_path="/data",
    iterations=15,
    factors=80
)

# Wait for completion
result = client.wait_for_completion(job_id)
print(f"F1@40: {result['metrics']['f1_at_k']:.4f}")
```

## Architecture

### Components

1. **Training Service** (`services/crud/training.py`)
   - Handles data loading and preprocessing
   - Implements training algorithms
   - Manages model saving and metrics calculation

2. **Training Worker** (`training_worker.py`)
   - Background worker for training jobs
   - Processes tasks from RabbitMQ queue
   - Updates job status in database

3. **Web Interface** (`view/training.html`)
   - User-friendly training interface
   - Real-time status monitoring
   - Training history display

4. **API Endpoints** (`main.py`)
   - REST endpoints for training operations
   - Authentication and authorization
   - Queue management

### Data Flow

1. User submits training request via web interface
2. Request creates `TrainingJob` record in database
3. Training task sent to RabbitMQ `training_tasks` queue
4. Training worker picks up task and starts training
5. Worker updates job status throughout process
6. Completed model saved to `ml_models/` directory
7. Metrics calculated and stored in database
8. User can view results via web interface

## Configuration

### Environment Variables
- `RABBITMQ_HOST`: RabbitMQ host (default: rabbitmq)
- `DB_NAME`: Database name (default: ml_results.db)

### Data Mounting
Mount your data directory in docker-compose.yaml:
```yaml
volumes:
  - ./your_data:/data
```

### Model Storage
Trained models are saved to `./ml_models/` with timestamps:
- `als_model_{job_id}_{timestamp}.pkl`
- Contains model object and mappings

## Monitoring

### Training Status Values
- `pending`: Job created, waiting in queue
- `loading_data`: Loading training data
- `preprocessing`: Data preprocessing
- `training`: Model training in progress
- `completed`: Training finished successfully
- `failed`: Training failed with error

### Logs
Check worker logs:
```bash
docker-compose logs training-worker
```

### RabbitMQ Management
Access RabbitMQ management at `http://localhost:15672`:
- Username: `rmuser`
- Password: `rmpassword`

## Troubleshooting

### Common Issues

1. **Data not found**
   - Ensure data path is correct
   - Check file permissions
   - Verify parquet file format

2. **Training fails**
   - Check worker logs for errors
   - Verify data format matches expected schema
   - Ensure sufficient memory for large datasets

3. **Slow training**
   - Reduce ALS iterations/factors
   - Use smaller data subset for testing
   - Check system resources

### Performance Tips

1. **For large datasets**:
   - Use smaller evaluation window
   - Reduce ALS factors
   - Consider data sampling

2. **For faster iteration**:
   - Start with popular model for baseline
   - Use smaller ALS parameters
   - Monitor memory usage

## Extending the System

### Adding New Models

1. Add model type to `TrainingService.train_model()`
2. Implement training function
3. Update web interface options
4. Add hyperparameters if needed

### Custom Metrics

1. Extend `calculate_metrics()` method
2. Update database schema for new metrics
3. Modify web interface to display metrics

### Data Sources

1. Implement new data loader in `load_data()`
2. Add data validation
3. Update preprocessing pipeline

## Security Considerations

- Training jobs are user-scoped
- Users can only access their own jobs
- Model files stored with timestamps
- Authentication required for all operations

## Performance Benchmarks

Based on baseline notebook results:

| Model | Recall@40 | Precision@40 | F1@40 | Training Time |
|-------|-----------|--------------|-------|---------------|
| Popular | 5.8% | 0.30% | 0.0057 | ~1s |
| ALS | 15.2% | 0.93% | 0.0175 | ~5-10min |

*Times vary based on data size and system resources* 