from fastapi import APIRouter,Request
import threading
from services.model_trainer import Model
from services.data_preprocessor import PreprocessEEG
from services.feature_selection import FeatureExtractor
from services.eeg_collect import SensorReader
from utils.hash_helper import decode_token
from utils.constants import state_to_label,state_to_database
from database import db_instance

collection = db_instance.get_collection("users")
eeg_collection = db_instance.get_collection("eeg_data")


current_data_state = {
    "state": "",
    "time": 0,
    "isRunning": False
}

stop_event = threading.Event()
thread = None


router = APIRouter()

@router.get("/")
async def test_model_training():
    return {"message": "Model Training Route is working!"}

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
    sensor_reader = SensorReader()
    preprocessor = PreprocessEEG()
    feature_extractor = FeatureExtractor()

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

@router.post("/check-model-status")
async def check_model_status(request:Request):
    token_status = decode_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    
    user = collection.find_one({"email":token_status["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if user.get("model_trained"):
        return {"status":"success","message":"Model trained"}
    return {"status":"error","message":"Model not trained"}

@router.post("/check-data-status")
async def check_data_status(request:Request):
    token_status = decode_token(request.cookies.get("access_token"))
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

@router.post("/start-collection")
async def start_eeg_collection(request:Request):
    data = await request.json()
    token_status = decode_token(request.cookies.get("access_token"))
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
    
@router.post("/stop-collection")
async def stop_eeg_collection(request:Request):
    data = await request.json()
    token_status = decode_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    if not current_data_state["isRunning"]:
        return {"status":"error","message":"Data collection not started"}   
    stop_eeg_pipeline()
    current_data_state["isRunning"] = False
    return {"status":"success","message":"Data collection stopped"}

@router.post("/data-collected")
async def data_collected(request:Request):
    data = await request.json()
    token_status = decode_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    if not data.get("state"):
        return {"status":"error","message":"Invalid request"}
    
    current_state = data.get("state")
    
    if current_state not in ["Relaxing","Focused"]:
        return {"status":"error","message":"Invalid state"}
    
    collection.update_one({"email":token_status["email"]},{"$set":{state_to_database[current_state]:True}})
    return {"status":"success","message":"Data collected successfully"}

@router.post("/train-model")
async def train_model(request:Request):
    token_status = decode_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    stop_event.clear()
    thread = threading.Thread(target=model_training_pipeline, args=(token_status["email"],))
    thread.start()
    return {"status":"success","message":"Model trained successfully"}

