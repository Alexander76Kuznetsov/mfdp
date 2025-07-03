# Track 5. Personalized Recommendation Engine for Retail

This is a FastAPI web application for building and training personalized product category recommendation models for retail (Avito-style).

## 🚀 Project Launch

### 1️⃣ Clone the Repository
First, clone the repository:

```sh
git clone https://github.com/Alexander76Kuznetsov/mfdp/tree/main
```

### 2️⃣ Build the Containers
Build the Docker containers using `docker-compose`:

```sh
docker-compose build
```

### 3️⃣ Start the Services
Start all services:

```sh
docker-compose up
```

After a successful launch, the API and web interface will be available at: [http://localhost:80](http://localhost:80)

## 📊 About the Platform
This platform allows you to:
- Train new recommendation models (Popular Items, ALS Collaborative Filtering)
- Monitor training jobs and view metrics (Recall@40, Precision@40, F1@40)
- Manage and version trained models
- Get product recommendations for users
- View task and transaction history

## 🛠 Main Endpoints
- `POST /start_training/` – start a new model training job
- `GET /training/` – view and monitor training jobs
- `GET /training_status/{job_id}` – get status and metrics for a training job
- `POST /predict/` – get recommendations for a user
- `GET /get_task_history/` – view prediction task history
- `GET /get_transaction_history/` – view transaction history

## 🧑‍💻 Features
- Web interface for launching and tracking model training
- Background workers for scalable training and prediction
- User authentication and job isolation
- Modern, responsive frontend

See `TRAINING_README.md` for full training system documentation.
