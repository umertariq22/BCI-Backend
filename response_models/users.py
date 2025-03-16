from pydantic import BaseModel,EmailStr
from typing import Optional

class AuthResponseModel(BaseModel):
    status: str
    message: str
    access_token: Optional[str] = None

class TokenResponseModel(BaseModel):
    email: Optional[str] = None
    status: str
    message: str