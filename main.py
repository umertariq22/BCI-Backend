from fastapi import Request,FastAPI
from pymongo import MongoClient,errors
from fastapi.middleware.cors import CORSMiddleware
from signup import User,validateSignupForm

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb://192.168.1.8:27017/")
db = client["bci"]
collection = db["users"]

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/signup")
async def signup(request:Request):
    data = await request.json()
    user = User(**data).model_dump()
    validation_error = validateSignupForm(user)
    if validation_error:
        return {"status":"error","message":validation_error}
    if collection.find_one({"email":user["email"]}):
        return {"status":"error","message":"User already exists"}
    # insert user
    try:
        collection.insert_one(user)
        return {"status":"success","message":"User created successfully"}
    except errors.PyMongoError as e:
        return {"status":"error","message":str(e)}
