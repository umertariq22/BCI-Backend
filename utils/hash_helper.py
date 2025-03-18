import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import math
import random

load_dotenv()

SECRET_KEY = os.environ.get("JWT_SECRET")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta:timedelta = timedelta(days=1)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"status":"success","message":"Token is Valid","email":payload.get("email")}
    except jwt.ExpiredSignatureError:
        return {"status":"error","message":"Token has expired"}
    except jwt.InvalidTokenError:
        return {"status":"error","message":"Invalid token"}
