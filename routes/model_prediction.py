from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from database import db_instance
from utils.hash_helper import decode_token
from services.eeg_collect import SensorReader
from services.model_predict import ModelPredict
from services.feature_selection import FeatureExtractor
from services.data_preprocessor import PreprocessEEG
import time
import threading 
from queue import Queue
import asyncio
from threading import Event

prediction_queue = Queue()
is_predicting = False
stop_event = Event()
thread = None



router = APIRouter()
collection = db_instance.get_collection("users")

sensor_reader = SensorReader()
model = ModelPredict()


@router.post("/connect-egg")
async def connect_eeg(request:Request):
    token_status = decode_token(request.cookies.get("access_token"))
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

@router.post("/disconnect-egg")
async def disconnect_eeg(request:Request):
    token_status = decode_token(request.cookies.get("access_token"))
    if token_status["status"] == "error":
        return {"status":"error","message":"Invalid token"}
    user = collection.find_one({"email":token_status["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    sensor_reader.stop_reading()
    sensor_reader.disconnect()

    return {"status":"success","message":"Disconnected from EEG"}

    
def prediction_worker():
    global is_predicting
    
    preprocessor = PreprocessEEG()
    feature_extractor = FeatureExtractor()
    
    while is_predicting:
        try:
            predictions = []
            for _ in range(5):
                generator_data = sensor_reader.read_one_second_data()
                data = list(next(generator_data, []))
                data = preprocessor.preprocess(data)
                feature, _ = feature_extractor.calculate_features(data)
                prediction = model.predict([feature])
                predictions.append(prediction)
                time.sleep(1)
            
            prediction = None
            if predictions.count(0) > predictions.count(1):
                prediction = 0
            else:
               prediction = 1
                
            prediction_text = "Relaxing" if prediction == 0 else "Focused"

            # Add prediction to the queue
            prediction_queue.put(prediction_text)
        except Exception as e:
            print(f"Error in prediction pipeline: {e}")
            break

    is_predicting = False
    print("Stopped prediction pipeline")


@router.websocket("/ws/predict")
async def websocket_endpoint(websocket: WebSocket):
    global is_predicting
    stop_event.clear()
    await websocket.accept()
    try:
        is_predicting = True
        thread = threading.Thread(target=prediction_worker).start()

        while is_predicting:
            await asyncio.sleep(0.1)  # Check queue periodically
            if not prediction_queue.empty():
                prediction_text = prediction_queue.get()
                await websocket.send_text(prediction_text)

    except WebSocketDisconnect:
        print("WebSocket disconnected")
        is_predicting = False
    except Exception as e:
        print(f"WebSocket error: {e}")
        is_predicting = False
    finally:
        stop_event.set()
        sensor_reader.stop_reading()
        sensor_reader.disconnect()
        await websocket.close()        