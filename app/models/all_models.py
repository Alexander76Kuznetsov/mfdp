import bcrypt
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Relationship
import datetime
from typing import List, Optional
import joblib


def get_current_date():
    return str(datetime.datetime.now(datetime.timezone.utc))


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    email: str
    balance: float = Field(default=0.0)
    is_admin: bool = Field(default=False)
    tasks: List["MLTask"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")

    def deposit(self, deposit_amount: float) -> None:
        self.balance += deposit_amount

    def withdraw(self, withdrawal_amount: float) -> None:
        if self.balance >= withdrawal_amount:
            self.balance -= withdrawal_amount
            return "success"
        else:
            print("Insufficient funds")
            return "fail"
        
    # def check_password(self, password: str) -> bool:
    #     return bcrypt.checkpw(password.encode('utf-8'), self.password_hash)


class TokenResponse(BaseModel): 
    access_token: str 
    token_type: str
    
class UserSignIn(SQLModel): 
    email: str 
    password: str


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount: float
    transaction_type: str
    transaction_status: str
    created_at: str = Field(default_factory=get_current_date)

    user: User = Relationship(back_populates="transactions")


class Prediction(SQLModel, table=True):
    prediction_id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="mltask.task_id")
    output: Optional[int] = Field(default=None)
    timestamp: str = Field(default_factory=get_current_date)

    task: "MLTask" = Relationship(back_populates="predictions")


class MLTask(SQLModel, table=True):
    task_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    model_id: int = Field(foreign_key="mlmodel.model_id")
    timestamp: str = Field(default_factory=get_current_date)
    cost: float = 20
    user: User = Relationship(back_populates="tasks")
    model: "MLModel" = Relationship(back_populates="tasks")
    predictions: List["Prediction"] = Relationship(back_populates="task")
    rabbitmqresults: List["RabbitmqResult"] = Relationship(back_populates="task")


class MLModel(SQLModel, table=True):
    model_id: Optional[int] = Field(default=None, primary_key=True)
    model_path: str
    __model = None
    tasks: List[MLTask] = Relationship(back_populates="model")

    def load_model(self):
        try:
            self.__model = joblib.load(open(self.model_path, 'rb'))
        except Exception as e:
            print(f"Ошибка при загрузке модели: {e}")
            self.__model = None

    def predict(self, input_data: List) -> "Prediction":
        if self.__model is None:
            self.load_model()
        prediction = self.__model.predict(input_data)

        return prediction


class RabbitmqResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="mltask.task_id")
    request_id: str

    task: "MLTask" = Relationship(back_populates="rabbitmqresults")
