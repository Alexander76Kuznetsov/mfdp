from models.all_models import Transaction, User
from typing import List, Optional


def get_all_transactions(session) -> List[Transaction]:
    return session.query(Transaction).all()

def get_transaction_by_id(id: int, session) -> Optional[Transaction]:
    transaction = session.get(Transaction, id) 
    if transaction:
        return transaction 
    return None

def create_transaction(new_transaction: Transaction, session) -> None:
    session.add(new_transaction) 
    session.commit() 
    session.refresh(new_transaction)

def delete_all_transaction(session) -> None:
    session.query(Transaction).delete()
    session.commit()
    
def delete_transaction_by_id(id: int, session) -> None:
    transaction = session.get(Transaction, id)
    if transaction:
        session.delete(transaction)
        session.commit()
        return
        
    raise Exception("Transaction with supplied ID does not exist")

def add_balance(user: User, amount: float, session):
    user.deposit(amount)
    session.add(user) 
    session.commit() 
    session.refresh(user)

    transaction = Transaction(user_id=user.id, amount=amount, transaction_type='deposit', transaction_status='success')
    create_transaction(transaction, session)

def withdraw_balance(user: User, amount: float, session):
    transaction_status = user.withdraw(amount)
    session.add(user) 
    session.commit() 
    session.refresh(user)

    transaction = Transaction(user_id=user.id, amount=amount, transaction_type='withdraw', transaction_status=transaction_status)
    create_transaction(transaction, session)

def get_transaction_history(user: User, session):
    transactions = session.query(Transaction).filter(Transaction.user_id == user.id).all()
    return [{"transaction_type": t.transaction_type, "amount": t.amount, "timestamp": t.created_at} for t in transactions]
