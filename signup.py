from pydantic import BaseModel
import re


class User(BaseModel):
    email: str
    password: str
    age:int
    gender:str
    
def validateSignupForm(user: User):
    
    for key in user:
        if user[key] == "":
            return f"All fields must be filled out."

    if user["age"] < 18:
        return f"User must be 18 years or older."
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", user["email"]):
        return f"Invalid email format."
    
    if len(user["password"]) < 8:
        return f"Password must be at least 8 characters long."
    
    if not any(char.isdigit() for char in user["password"]):
        return f"Password must contain at least one number."
    
    if not any(char.isupper() for char in user["password"]):
        return f"Password must contain at least one uppercase letter."

    return None
    
    
    
    
    