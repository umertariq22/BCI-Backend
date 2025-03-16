from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import users
from routes import model_training
from routes import model_prediction
from database import db_instance

app = FastAPI()
origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    
@app.on_event("shutdown")
async def shutdown():
    db_instance.close()    

app.include_router(users.router,prefix="/users",tags=["users"])
app.include_router(model_training.router,prefix="/model-training",tags=["model-training"])
app.include_router(model_prediction.router,prefix="/model-prediction",tags=["model-prediction"])

