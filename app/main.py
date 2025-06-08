from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from services.auth.loginform import LoginForm
import uvicorn
from auth.authenticate import authenticate_cookie
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from database.config import get_settings
from database.database import init_db, get_session, engine
from services.crud import user as UserService
from services.crud import transaction as TransactionService
from services.crud import ml as MlService
from sqlmodel import Session
from models.all_models import TokenResponse, User, MLModel, MLTask, RabbitmqResult
import pika
import json
import uuid


app = FastAPI()
origins = ["*"] 
app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.on_event("startup") 
def on_startup():
    init_db()
    with Session(engine) as session:
        user = User(username='test_user', password="123", email="test@example.com")
        hashed_password = hash_password.create_hash(user.password)
        user.password = hashed_password 
        UserService.create_user(user, session)
        print('Test user created')

        model = MLModel(model_path='./ml_models/model.pkl')
        MlService.create_model(model, session)
        print('Test model created')

settings = get_settings()
hash_password = HashPassword()
templates = Jinja2Templates(directory="view")

RABBITMQ_HOST = "rabbitmq"
QUEUE_NAME = "ml_tasks"
DB_NAME = "ml_results.db"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    context = {
        "user": user,
        "request": request
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm=Depends(), session=Depends(get_session)) -> dict[str, str]:    
    user_exist = UserService.get_user_by_email(form_data.username, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    if hash_password.verify_hash(form_data.password, user_exist.password):
        access_token = create_access_token(user_exist.email)
        response.set_cookie(
            key=settings.COOKIE_NAME, 
            value=f"Bearer {access_token}", 
            httponly=True
        )
        
        # return {"access_token": access_token, "token_type": "Bearer"}
        return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )


@app.get("/auth/login", response_class=HTMLResponse)
async def login_get(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("login.html", context)


@app.post("/auth/login", response_class=HTMLResponse)
async def login_post(request: Request, session=Depends(get_session)):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            response = RedirectResponse("/", status.HTTP_302_FOUND)
            await login_for_access_token(response=response, form_data=form, session=session)
            form.__dict__.update(msg="Login Successful!")
            print("[green]Login successful!!!!")
            return response
        except HTTPException:
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or Password")
            return templates.TemplateResponse("login.html", form.__dict__)
    return templates.TemplateResponse("login.html", form.__dict__)


@app.get("/auth/logout", response_class=HTMLResponse)
async def login_get():
    response = RedirectResponse(url="/")
    response.delete_cookie(settings.COOKIE_NAME)
    return response


@app.get("/signup/")
def signup(request: Request):
    context = {
        "request": request
    }
    return templates.TemplateResponse("signup.html", context)


@app.post("/sign_new_user")
async def sign_new_user(request: Request, 
                        username=Form(...),
                        email=Form(...),
                        password=Form(...),
                        session=Depends(get_session)) -> dict:
    
    user = User(username=username, password=password, email=email)
    user_exist = UserService.get_user_by_email(user.email, session)
    
    if user_exist:
        raise HTTPException( 
        status_code=status.HTTP_409_CONFLICT, 
        detail="User with email provided exists already.")
    
    hashed_password = hash_password.create_hash(user.password)
    user.password = hashed_password 
    UserService.create_user(user, session)

    context = {
        "request": request
    }
    return templates.TemplateResponse("signup.html", context)


@app.post("/signin", response_model=TokenResponse)
async def sign_user_in(user: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)) -> dict: 
    user_exist = UserService.get_user_by_email(user.username, session)
    
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    if hash_password.verify_hash(user.password, user_exist.password):
        access_token = create_access_token(user_exist.email)
        return {"access_token": access_token, "token_type": "Bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )


@app.get("/get_balance/")
def get_balance(request: Request, user_email: str = Depends(authenticate_cookie), session=Depends(get_session)):
    user = UserService.get_user_by_email(user_email, session)
    context = {
        "user": user,
        "request": request
    }
    return templates.TemplateResponse("balance.html", context)


@app.post("/deposit/")
def deposit(request: Request, amount: float = Form(...), user_email: str = Depends(authenticate_cookie), session=Depends(get_session)):
    user = UserService.get_user_by_email(user_email, session)
    context = {
        "user": user,
        "request": request
    }
    if user:
        TransactionService.add_balance(user, amount, session)
    return templates.TemplateResponse("balance.html", context)


@app.get("/get_task_history/")
def get_task_history(request: Request, user_email: str = Depends(authenticate_cookie), session=Depends(get_session)):
    user = UserService.get_user_by_email(user_email, session)
    context = {
        "history": MlService.get_task_history(user, session),
        "request": request
    }
    return templates.TemplateResponse("task_history.html", context)


@app.get("/get_transaction_history/")
def get_transaction_history(request: Request, user_email: str = Depends(authenticate_cookie), session=Depends(get_session)):
    user = UserService.get_user_by_email(user_email, session)
    context = {
        "history": TransactionService.get_transaction_history(user, session),
        "request": request
    }
    return templates.TemplateResponse("transaction_history.html", context)


def send_to_queue(task: dict):
    connection_params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
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
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    
    request_id = str(uuid.uuid4())
    task["request_id"] = request_id
    print(f'сгенерирован request_id: {request_id}')
    
    channel.basic_publish(
        exchange='', 
        routing_key=QUEUE_NAME, 
        body=json.dumps(task), 
        properties=pika.BasicProperties(delivery_mode=2)
    )
    
    connection.close()
    return request_id


@app.get("/make_prediction/")
def make_prediction(request: Request, user_email: str = Depends(authenticate_cookie), session=Depends(get_session)):
    user = UserService.get_user_by_email(user_email, session)
    context = {
        "user": user,
        "request": request
    }
    return templates.TemplateResponse("prediction.html", context)


@app.post("/predict/")
def predict(request: Request, 
            model_id = Form(...),
            user_email: str = Depends(authenticate_cookie), 
            session: Session = Depends(get_session)):
    
    user = UserService.get_user_by_email(user_email, session)
    task = MLTask(
        user_id=user.id,
        model_id=model_id,
    )
    task = MlService.create_task(task, session)
    request_id = send_to_queue(task.model_dump())
    MlService.create_rabbitmq_result(RabbitmqResult(task_id=task.task_id, request_id=request_id), session)

    context = {
        "user": user,
        "request": request,
        "request_id": request_id
    }
    TransactionService.withdraw_balance(user, 20, session)
    return templates.TemplateResponse("prediction.html", context)


@app.post("/get_prediction/")
def get_prediction(request: Request, request_id: str = Form(...), user_email: str = Depends(authenticate_cookie), session=Depends(get_session)):
    user = UserService.get_user_by_email(user_email, session)
    prediction = MlService.get_prediction(request_id, session)
    
    context = {
        "user": user,
        "request": request,
        "request_id": request_id,
        "prediction_res": prediction
    }

    return templates.TemplateResponse("prediction.html", context)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port="8080")
