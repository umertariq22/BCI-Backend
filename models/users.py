from pydantic import BaseModel

class User(BaseModel):
    email: str
    password: str
    age:int
    gender:str
    relaxed_data_collected:bool = False
    focused_data_collected:bool = False
    model_trained:bool = False
    