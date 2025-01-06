from fastapi import FastAPI, Response,Request, WebSocket,WebSocketDisconnect
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
from model_predict import ModelPredict
import numpy as np
import threading



TOTAL_TIME = 20
FREQ = 512

prediction_thread = None
is_prediction = False

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

sensor_reader = SensorReader(port='COM7')
preprocessor = PreprocessEEG()
feature_extractor = FeatureExtractor()


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
    except Exception as e:
        return {"status":"error","message":"Invalid token","email":""}
        
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
        return {"status":"error","message":"User not found","access_token":""}
    if not pwd_context.verify(data["password"],user["password"]):
        return {"status":"error","message":"Invalid credentials","access_token":""}
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


def model_training_pipeline(email):
    model = Model()
    print("Model training started")
    
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
    print(len(X))
    print(y)    
    model.train_with_split(X,y)
    print("Model trained")
    print(model.evaluate(X,y))
    model.save_model(email=email)
    print("Model saved")
    collection.update_one({"email":email},{"$set":{"model_trained":True}})
    return {"status":"success","message":"Model trained successfully"}
    
def start_eeg_pipeline(email: str):
    global current_data_state
    sensor_reader.connect()
    sensor_reader.start_reading()
    
    while current_data_state["isRunning"]:
        generator_data = sensor_reader.read_one_second_data()
        data = list(next(generator_data, []))
        print(data)
        if not data:
            continue
        preprocessed_data = preprocessor.preprocess(data)
        feature,_ = feature_extractor.calculate_features(preprocessed_data)
        
        
        data_to_store = {
            "email": email,
            "features": feature,
            "label": state_to_label[current_data_state["state"]],
        }
        
        eeg_collection.insert_one(data_to_store)
        print(data)
        print(feature)
                
    sensor_reader.stop_reading()
    sensor_reader.disconnect()
    
    return {"status": "success", "message": "Data collection Stopped"}

def start_eeg_pipeline_with_thread(email: str):
    stop_event.clear()
    thread = threading.Thread(target=start_eeg_pipeline, args=(email,))
    thread.start()
    return thread

def stop_eeg_pipeline():
    global stop_event
    stop_event.set()
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
async def start_eeg_collection(request:Request):
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
async def train_model(request:Request):
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    stop_event.clear()
    thread = threading.Thread(target=model_training_pipeline, args=(token_status["email"],))
    thread.start()
    return {"status":"success","message":"Model trained successfully"}
model = ModelPredict()
@app.post("/connect-egg")
async def connect_eeg(request:Request):
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    user = collection.find_one({"email":token_status["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if not user.get("model_trained"):
        return {"status":"error","message":"Model not trained"}
    sensor_connected = sensor_reader.connect()
    if not sensor_connected:
        return {"status":"error","message":"Failed to connect to EEG"}
    
    model.load_model(email=token_status["email"])
    sensor_reader.start_reading()
    return {"status":"success","message":"Connected to EEG"}

@app.post("/disconnect-egg")
async def disconnect_eeg(request:Request):
    token_status = verify_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    user = collection.find_one({"email":token_status["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    sensor_reader.disconnect()
    sensor_reader.stop_reading()
    return {"status":"success","message":"Disconnected from EEG"}


async def start_prediction_pipeline(websocket: WebSocket):
    global is_predicting

    async def send_predictions():
        global is_predicting
        while is_predicting:
            try:
                generator_data = sensor_reader.read_one_second_data()
                data = list(next(generator_data, []))
                data = preprocessor.preprocess(data)
                feature, _ = feature_extractor.calculate_features(data)
                prediction = model.predict([feature]) 
                prediction_text = "Relaxing" if prediction == 0 else "Focused"
                
                await websocket.send_json({"prediction": prediction_text})
            except Exception as e:
                print(f"Error in prediction pipeline: {e}")
                break

        is_predicting = False
        print("Stopped prediction pipeline")
        
    await send_predictions()


@app.websocket("/ws/predict")
async def websocket_endpoint(websocket: WebSocket):
    global prediction_thread, is_predicting
    await websocket.accept()
    try:
        if not is_predicting:
            is_predicting = True
            prediction_thread = threading.Thread(target=start_prediction_pipeline, args=(websocket,))
            prediction_thread.start()
        else:
            await websocket.send_json({"message": "Prediction pipeline already running."})
        
    except WebSocketDisconnect:
        print("WebSocket disconnected")
        is_predicting = False
    except Exception as e:
        print(f"WebSocket error: {e}")
        is_predicting = False
    finally:
        sensor_reader.stop_reading()
        sensor_reader.disconnect()
        await websocket.close()