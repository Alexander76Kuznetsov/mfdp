import time
from datetime import datetime
from fastapi import HTTPException, status 
from jose import jwt, JWTError
from database.database import get_settings

settings = get_settings()
SECRET_KEY = settings.SECRET_KEY

def create_access_token(user: str) -> str: 
    payload = {
    "user": user,
    "expires": time.time() + 3600
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def verify_access_token(token: str) -> dict: 
    try:
        data = jwt.decode(token, SECRET_KEY, 
        algorithms=["HS256"])
        expire = data.get("expires")
        if expire is None:
            raise HTTPException( 
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No access token supplied"
            )
        if datetime.utcnow() > datetime.utcfromtimestamp(expire):
            raise HTTPException( 
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Token expired!"
            )
        return data
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
