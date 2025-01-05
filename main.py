from fastapi import FastAPI, Response,Request,BackgroundTasks
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import jwt
from signup import User,validateSignupForm,AuthResponseModel
from pymongo import MongoClient,errors
import os
from fastapi_mail import FastMail, MessageSchema,ConnectionConfig
import math,random
from dotenv import load_dotenv
from eeg_collect import SensorReader
from data_preprocessor import PreprocessEEG
from feature_selection import FeatureExtractor
from eeg_collect import SensorReader
from model_trainer import Model
import numpy as np
import time
import threading

def convert_numpy_types(data):
    if isinstance(data, np.generic):  # Check if it's a NumPy scalar
        return data.item()  # Convert to native Python type
    elif isinstance(data, np.ndarray):  # Check if it's a NumPy array
        return data.tolist()  # Convert array to list
    return data  # If it's already a Python type, return as is

TOTAL_TIME = 20
FREQ = 512

stop_event = threading.Event()

state_to_label = {
    "Relaxing":0,
    "Focused":1
}

state_to_database = {
    "Focused":"focused_data_collected",
    "Relaxing":"relaxed_data_collected",
}

current_data_state = {
    "isRunning":False,
    "state":None,
    "time":None,
}


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
eeg_collection = db["eegdata"]

sensor_reader = SensorReader(port='COM3')
preprocessor = PreprocessEEG()
feature_extractor = FeatureExtractor()
model = Model()


load_dotenv()

SECRET_KEY = os.environ.get("JWT_SECRET")
ALGORITHM = "HS256"

EMAIL: str = os.environ.get("MAIL_EMAIL")
PASSWORD: str = os.environ.get("MAIL_PASSWORD")

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
        return {"status":"success","message":"Token is valid","email":payload["email"]}
    except jwt.JWTError:
        return {"status":"error","message":"Invalid token"}
        
def generate_otp(length=6):
    digits = "0123456789"
    OTP = ""
    for i in range(length):
        OTP += digits[math.floor(random.random() * 10)]
    return OTP
 
connection_conf = ConnectionConfig(
    MAIL_USERNAME=EMAIL,
    MAIL_PASSWORD=PASSWORD,
    MAIL_FROM=EMAIL,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

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

@app.post("/send-email")
async def send_email(request:Request):
    data = await request.json()
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    
    otp = generate_otp()
    collection.update_one({"email":data["email"]},{"$set":{"otp":otp}})
    
    template = f"""
    <h1>OTP for password reset</h1>
    <p>Your OTP is {otp}</p>
    """
    message = MessageSchema(
        subject="OTP for password reset",
        recipients=[data["email"]],
        body=template,
        subtype="html"
    )
    
    fm = FastMail(connection_conf)
    try:
        await fm.send_message(message)
    except Exception as e:
        print(str(e))
        return {"status":"error","message":"Failed to send OTP"}
    
    return {"status":"success","message":"OTP sent successfully"}

@app.post("/validate-otp")
async def validate_otp(request:Request):
    data = await request.json()
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if not user.get("otp"):
        return {"status":"error","message":"OTP not found"}
    if user["otp"] != data["otp"]:
        return {"status":"error","message":"Invalid OTP"}
    return {"status":"success","message":"OTP is valid"}
    
@app.post("/reset-password")
async def reset_password(request:Request):
    data = await request.json()
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    collection.update_one({"email":data["email"]},{"$set":{"password":pwd_context.hash(data["password"]),"otp":""}})
    return {"status":"success","message":"Password reset successfully"}


async def model_training_pipeline(email):
    global model

    user_data = collection.find_one({"email":email})
    if not user_data:
        return {"status":"error","message":"User not found"}
    if user_data.get("model_trained"):
        return {"status":"error","message":"Model already trained"}
    if not user_data.get("focused_data_collected") or not user_data.get("relaxed_data_collected"):
        return {"status":"error","message":"Data not collected"}
    
    data = eeg_collection.find({"email":email})
    
    X = []
    y = []
    for record in data:
        X.append(record["features"])
        y.append(record["label"])
    model.train_with_split(X,y)
    return {"status":"success","message":"Model trained successfully"}
    
def start_eeg_pipeline(email: str):
    global current_data_state
    sensor_reader.connect()
    sensor_reader.start_reading()
    
    while current_data_state["isRunning"]:
        data = sensor_reader.read_one_second_data()
        preprocessed_data = preprocessor.preprocess(data)
        feature = feature_extractor.calculate_features(preprocessed_data)
        feature = {key: convert_numpy_types(value) for key, value in feature.items()}
        data = [convert_numpy_types(d) for d in data]
           
        data_to_store = {
            "email": email,
            "features": feature,
            "label": state_to_label[current_data_state["state"]],
        }
        eeg_collection.insert_one(data_to_store)
        time.sleep(1)
        
    sensor_reader.stop_reading()
    sensor_reader.disconnect()
    
    return {"status": "success", "message": "Data collection Stopped"}

def start_eeg_pipeline_with_thread(email: str):
    stop_event.clear()  # Clear the stop event to allow the thread to start
    thread = threading.Thread(target=start_eeg_pipeline, args=(email,))
    thread.start()
    return thread

def stop_eeg_pipeline():
    global stop_event
    stop_event.set()  # Set the stop event to stop the thread
    return {"status": "success", "message": "Data collection Stopped"}

@app.post("/check-model-status")
async def check_model_status(request:Request):
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    user = collection.find_one({"email":token_status["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if user.get("model_trained"):
        return {"status":"success","message":"Model trained"}
    return {"status":"error","message":"Model not trained"}

@app.post("/check-data-status")
async def check_data_status(request:Request):
    token_status = verify_token(request.cookies.get("access_token"))
    data = await request.json()
    state = data["state"]
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    user = collection.find_one({"email":token_status["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if user.get(state_to_database[state]):
        return {"status":"success","message":"Data collected"}
    return {"status":"error","message":"Data not collected"}

@app.post("/start-collection")
async def start_eeg_collection(request:Request,background_tasks:BackgroundTasks):
    data = await request.json()
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    if not data.get("time") or not data.get("state"):
        return {"status":"error","message":"Invalid request"}
    current_state = data.get("state")
    time = data.get("time")  
    current_data_state["state"] = current_state
    current_data_state["time"] = time
    current_data_state["isRunning"] = True
    
    thread = start_eeg_pipeline_with_thread(token_status["email"])
    return {"status":"success","message":"Data collection started"}
    
@app.post("/stop-collection")
async def stop_eeg_collection(request:Request):
    data = await request.json()
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    if not current_data_state["isRunning"]:
        return {"status":"error","message":"Data collection not started"}   
    stop_eeg_pipeline()
    current_data_state["isRunning"] = False
    return {"status":"success","message":"Data collection stopped"}

@app.post("/data-collected")
async def data_collected(request:Request):
    data = await request.json()
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    if not data.get("state"):
        return {"status":"error","message":"Invalid request"}
    
    current_state = data.get("state")
    
    if current_state not in ["Relaxing","Focused"]:
        return {"status":"error","message":"Invalid state"}
    
    collection.update_one({"email":token_status["email"]},{"$set":{state_to_database[current_state]:True}})
    return {"status":"success","message":"Data collected successfully"}

@app.post("/train-model")
async def train_model(request:Request,background_tasks:BackgroundTasks):
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    background_tasks.add_task(model_training_pipeline,token_status["email"])
    return {"status":"success","message":"Model trained successfully"}

