import pika
import json
import pandas as pd

from database.database import get_session
from services.crud import ml as MlService
from models.all_models import Prediction, MLModel
from sqlalchemy import create_engine


session = next(get_session())
model = MLModel(model_path='./ml_models/decision_forest_model.pkl')
engine = create_engine(
    "postgresql://robot-startml-ro:pheiph0hahj1Vaif@"
    "postgres.lab.karpov.courses:6432/startml"
)

RABBITMQ_HOST = "rabbitmq"
QUEUE_NAME = "ml_tasks"

def mock_predict(task, model):
    input_data = pd.read_sql(f'SELECT * FROM public.mfdp_user_features where user_id == {task["user_id"]};', con=engine)
    output = float(model.predict(input_data))
    prediction = Prediction(user_id=task["user_id"], task_id=task["task_id"], output=output)
    return prediction


def callback(ch, method, properties, body):
    """Обработчик сообщений из RabbitMQ"""
    task = json.loads(body)
    print(f"Received task: {task}")

    request_id = task.get("request_id")

    result = mock_predict(task, model)
    print(f"Predicted result for {request_id}: {result}")
    
    MlService.create_prediction(result, session)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_worker():
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
    # channel.queue_declare(queue=QUEUE_NAME, durable=True)
    # channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Worker started. Waiting for tasks...")
    channel.start_consuming()

if __name__ == "__main__":
    start_worker()
