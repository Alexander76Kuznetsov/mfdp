from models.all_models import MLModel, MLTask, Prediction, RabbitmqResult, User


def create_model(new_model: MLModel, session) -> None:
    session.add(new_model) 
    session.commit() 
    session.refresh(new_model)


def create_task(new_task: MLTask, session) -> None:
    session.add(new_task) 
    session.commit() 
    session.refresh(new_task)
    return new_task


def create_prediction(new_prediction: Prediction, session) -> None:
    session.add(new_prediction) 
    session.commit() 
    session.refresh(new_prediction)


def create_rabbitmq_result(new_rabbitmq_result: RabbitmqResult, session) -> None:
    session.add(new_rabbitmq_result) 
    session.commit() 
    session.refresh(new_rabbitmq_result)


def get_task_history(user: User, session):
    tasks = session.query(MLTask).filter(MLTask.user_id == user.id).all()
    return [{"task_id": t.task_id, "model id": t.model_id, "timestamp": t.timestamp, "cost": t.cost} for t in tasks]


def get_prediction(request_id, session): 
    task = session.query(RabbitmqResult).filter(RabbitmqResult.request_id == request_id).first()
    if task is None:
        return "There is no this request"
    prediction = session.query(Prediction).filter(Prediction.task_id == task.task_id).first()
    if prediction is None:
        return "There is no such a prediction"
    return f"prediction_id: {prediction.prediction_id}, task_id: {prediction.task_id}, timestamp: {prediction.timestamp}, result: {prediction.output}"
