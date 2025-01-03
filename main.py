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
from model_trainer import Model


TOTAL_TIME = 20
FREQ = 512


state_to_label = {
    "Relaxing":0,
    "Focused":1
}


current_data_state = {
    "isRunning":False,
    "state":None,
    "time":None,
    "data":[],
    "label":[]
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

sensor_reader = SensorReader(port="COM7")
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
    

async def start_eeg_pipeline():
    global current_data_state
    sensor_reader.connect()
    while current_data_state["isRunning"]:
        data = sensor_reader.read_one_second_data()
        preprocessed_data = preprocessor.preprocess(data)
        feature = feature_extractor.calculate_features(preprocessed_data)
        current_data_state["data"].append(feature)
        current_data_state["label"].append(state_to_label[current_data_state["state"]])
    
    sensor_reader.disconnect()
    return {"status":"success","message":"Data collection Stopped"}
        
        

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
    
    background_tasks.add_task(start_eeg_pipeline)
    return {"status":"success","message":"Data collection started"}
    

@app.post("/stop-collection")
async def stop_eeg_collection(request:Request):
    if not current_data_state["isRunning"]:
        return {"status":"error","message":"Data collection not started"}
    if len(current_data_state["data"]) >= TOTAL_TIME * 60 * FREQ * 2:
        model.train_with_split(current_data_state["data"],current_data_state["label"])
        return {"status":"success","message":"Data collection stopped and model trained"}        
    current_data_state["isRunning"] = False
    return {"status":"success","message":"Data collection stopped"}


    
    
