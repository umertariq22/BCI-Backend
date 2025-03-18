from fastapi import APIRouter,HTTPException,Request,Response
from models.users import User
from response_models.users import AuthResponseModel,TokenResponseModel
from utils.hash_helper import hash_password,create_access_token,verify_password,decode_token
from utils.validators import validateSignupForm
from utils.util_func import generate_otp
from utils.send_email import send_email
from database import db_instance

router = APIRouter()


@router.post("/signup",response_model=AuthResponseModel)
async def signup(request:Request,response:Response):
    data = await request.json()
    user = User(**data).model_dump()
    validation_error = validateSignupForm(user)
    if validation_error:
        return {"status":"error","message":validation_error}
    collection = db_instance.get_collection("users")
    if collection.find_one({"email":user["email"]}):
        return  {"status":"error","message":"User already exists"}
        
    try:
        user["password"] = hash_password(user["password"])
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
    except Exception as e:
        return  {"status":"error","message":str(e)}
    
@router.post("/login",response_model=AuthResponseModel)
async def login(request:Request,response:Response):
    data = await request.json()
    collection = db_instance.get_collection("users")
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found","access_token":""}
    if not verify_password(data["password"],user["password"]):
        return {"status":"error","message":"Invalid credentials","access_token":""}
    access_token = create_access_token(data={"email":user["email"]})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True, 
        max_age=86400,  
        expires=86400,  
        secure=False,   
        samesite="lax"  
    )

    return {"status":"success","message":"User logged in successfully","access_token":access_token}    


@router.post("/validate-token",response_model=TokenResponseModel)
async def validate_token(request:Request,response:Response):
    access_token = request.cookies.get("access_token")
    if not access_token:
        return {"status":"error","message":"Token not found"}
    payload = decode_token(access_token)
    print(payload)
    if payload["status"] == "error":
        response.delete_cookie("access_token")
        return {"status":"error","message":payload["message"]}
    return {"status":"success","message":"Token is valid","email":payload["email"]}

@router.post("/logout")
async def logout(response:Response):
    response.delete_cookie("access_token")
    return {"status":"success","message":"User logged out successfully"}

@router.post("/send-otp")
async def send_otp(request:Request):
    data = await request.json()
    collection = db_instance.get_collection("users")
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    
    otp = generate_otp()
    collection.update_one({"email":data["email"]},{"$set":{"otp":otp}})
    
    template = f"""
    <h1>OTP for password reset</h1>
    <p>Your OTP is {otp}</p>
    """
    try:
        await send_email(data["email"],"Password Reset OTP",template)
        return {"status":"success","message":"OTP sent successfully"}
    except Exception as e:
        return {"status":"error","message":"Error sending OTP! Please try again later."}
    
@router.post("/validate-otp")
async def validate_otp(request:Request):
    data = await request.json()
    collection = db_instance.get_collection("users")
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    if not user.get("otp"):
        return {"status":"error","message":"OTP not found"}
    if user["otp"] != data["otp"]:
        return {"status":"error","message":"Invalid OTP"}
    return {"status":"success","message":"OTP is valid"}
    
@router.post("/reset-password")
async def reset_password(request:Request):
    data = await request.json()
    collection = db_instance.get_collection("users")
    user = collection.find_one({"email":data["email"]})
    if not user:
        return {"status":"error","message":"User not found"}
    
    try:
        collection.update_one({"email":data["email"]},{"$set":{"password":hash_password(data["password"])}})
        collection.update_one({"email":data["email"]},{"$unset":{"otp":""}})
        return {"status":"success","message":"Password reset successfully"}
    except Exception as e:
        return {"status":"error","message":"Error resetting password! Please try again later."}

