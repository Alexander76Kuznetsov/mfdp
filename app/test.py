from fastapi.testclient import TestClient
from auth.authenticate import authenticate_cookie
from database.database import get_session
from main import app
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from services.crud import user as UserService
from services.crud import transaction as TransactionService
from services.crud import ml as MlService


client = TestClient(app)

mock_user = MagicMock()
mock_user.id = 1
mock_user.email = "test@example.com"


def mock_authenticate_cookie():
    return "test@example.com"

def mock_get_session():
    return MagicMock()

app.dependency_overrides[authenticate_cookie] = mock_authenticate_cookie
app.dependency_overrides[get_session] = mock_get_session

UserService.get_user_by_email = MagicMock(return_value=mock_user)
MlService.get_task_history = MagicMock(return_value=[{"task": "Task 1"}, {"task": "Task 2"}])
TransactionService.get_transaction_history = MagicMock(return_value=[{"amount": 100}, {"amount": 200}])

def test_create_user():
    response = client.post("/sign_new_user/", json={"username": "test_user1", "password": "123", "email": "test1@example.com"})
    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["username"] == "test_user1"
    assert response.json()["password"] != "123"


def test_deposit():
    amount = 100.0
    response = client.post("/deposit/", data={"amount": amount})
    assert response.status_code == 200
    assert "balance.html" in response.text


def test_get_task_history():
    response = client.get("/get_task_history/")
    
    assert response.status_code == 200
    assert "task_history.html" in response.text


def test_get_transaction_history():
    response = client.get("/get_transaction_history/")
    
    assert response.status_code == 200
    assert "transaction_history.html" in response.text
    assert "100" in response.text
    assert "200" in response.text