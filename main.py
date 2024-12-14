from fastapi import FastAPI, HTTPException, Response, status,Request
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import jwt
from signup import User,validateSignupForm,AuthResponseModel
import csv
from pymongo import MongoClient,errors
import os

app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb://localhost:27017")
db = client["bci"]
collection = db["users"]

SECRET_KEY = os.environ.get("JWT_SECRET")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta:timedelta = timedelta(days=1)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token:str):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        print(payload)
        return {"status":"success","message":"Token is valid","email":payload["email"]}
    except jwt.JWTError:
        return {"status":"error","message":"Invalid token"}
        


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/signup",response_model=AuthResponseModel)
async def signup(request:Request,response:Response):
    data = await request.json()
    user = User(**data).model_dump()
    validation_error = validateSignupForm(user)
    if validation_error:
        return {"status":"error","message":validation_error,"access_token":""}
    if collection.find_one({"email":user["email"]}):
        return  {"status":"error","message":"User already exists","access_token":""}
        
    try:
        user["password"] = pwd_context.hash(user["password"])
        collection.insert_one(user)
        access_token = create_access_token(data={"email":user["email"]})
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # Restricts JavaScript access
            max_age=86400,  # 1 day in seconds
            expires=86400,  # Expiry time
            secure=False,   # Change to True for HTTPS
            samesite="lax"  # Adjust based on your frontend-backend interaction
        )   

        
        return {"status":"success","message":"User created successfully","access_token":access_token}
    except errors.PyMongoError as e:
        return  {"status":"error","message":str(e),"access_token":""}
    

@app.post("/login",response_model=AuthResponseModel)
async def login(request:Request,response:Response):
    data = await request.json()
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if not pwd_context.verify(data["password"],user["password"]):
        return {"status":"error","message":"Invalid credentials"}
    access_token = create_access_token(data={"email":user["email"]})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # Restricts JavaScript access
        max_age=86400,  # 1 day in seconds
        expires=86400,  # Expiry time
        secure=False,   # Change to True for HTTPS
        samesite="lax"  # Adjust based on your frontend-backend interaction
    )

    return {"status":"success","message":"User logged in successfully","access_token":access_token}    

@app.get("/validate_token")
async def validate_token(request:Request):
    access_token = request.cookies.get("access_token")
    if not access_token:
        return {"status":"error","message":"Token not found"}
    payload = verify_token(access_token)
    return {"status":"success","message":"Token is valid","email":payload["email"]}

@app.post("/logout")
async def logout(response:Response):
    response.delete_cookie("access_token")
    return {"status":"success","message":"User logged out successfully"}

@app.post("/eeg")
async def eegdata(request:Request):
    data = await request.json()
    raw_eeg_data = {
        "user_id":1,
        "timestamp":data["timestamp"],
        "eeg_data":data["values"]
    }
    
    # open csv file and write the data as follows user_id,timestamp,channel1,channel2,channel3,channel4 and do not add empty lines
    with open("eegdata.csv","a",newline='') as file:
        writer = csv.writer(file)
        writer.writerow([raw_eeg_data["user_id"],raw_eeg_data["timestamp"],*raw_eeg_data["eeg_data"]])
                
    
    collection = db["eegdata"]
    collection.insert_one(raw_eeg_data)
    return "data received"

