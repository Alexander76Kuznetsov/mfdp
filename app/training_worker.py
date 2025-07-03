import pika
import json
import traceback
from database.database import get_session
from services.crud import training as TrainingService
from models.all_models import TrainingJob
from sqlmodel import Session

RABBITMQ_HOST = "rabbitmq"
TRAINING_QUEUE_NAME = "training_tasks"

def callback(ch, method, properties, body):
    """Обработчик сообщений из RabbitMQ для обучения моделей"""
    try:
        task = json.loads(body)
        print(f"Received training task: {task}")
        
        job_id = task.get("job_id")
        model_type = task.get("model_type")
        data_path = task.get("data_path")
        hyperparams = task.get("hyperparams")
        
        # Get database session
        session = next(get_session())
        
        # Get training service
        training_service = TrainingService.TrainingService()
        
        # Train model
        result = training_service.train_model(
            job_id=job_id,
            session=session,
            model_type=model_type,
            data_path=data_path,
            hyperparams=hyperparams
        )
        
        print(f"Training completed for job {job_id}: {result}")
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"Error processing training task: {e}")
        print(traceback.format_exc())
        
        # Update job status to failed
        try:
            session = next(get_session())
            training_service = TrainingService.TrainingService()
            training_service.update_training_job(job_id, "failed", session)
        except:
            pass
        
        # Acknowledge message to remove from queue
        ch.basic_ack(delivery_tag=method.delivery_tag)


def start_training_worker():
    """Start the training worker"""
    connection_params = pika.ConnectionParameters(
        host='rabbitmq',
        port=5672,
        virtual_host='/',
        credentials=pika.PlainCredentials(
            username='rmuser',
            password='rmpassword'
        ),
        heartbeat=30,
        blocked_connection_timeout=2
    )
    
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    
    # Declare training queue
    channel.queue_declare(queue=TRAINING_QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=TRAINING_QUEUE_NAME, on_message_callback=callback)

    print("Training worker started. Waiting for training tasks...")
    channel.start_consuming()


if __name__ == "__main__":
    start_training_worker() 