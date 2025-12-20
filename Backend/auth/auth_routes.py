from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from bson import ObjectId
from datetime import datetime
from google.auth.transport import requests
from google.oauth2 import id_token
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from auth.auth_utils import verify_password, get_password_hash, create_access_token, verify_token

# Database will be imported from main after it's initialized
database = None

def set_database(db):
    global database
    database = db

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

# Google OAuth settings - load from environment
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# Validate that GOOGLE_CLIENT_ID is set
if not GOOGLE_CLIENT_ID:
    print("⚠️  WARNING: GOOGLE_CLIENT_ID is not set in environment variables!")
    print("   Google OAuth authentication will not work until this is configured.")


# Request/Response models
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    persona: str  # "admin" or "employee"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


# Helper function to get current user from token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    user = await database.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    user["id"] = str(user["_id"])
    del user["_id"]
    # Only delete password if it exists (Google OAuth users don't have passwords)
    if "password" in user:
        del user["password"]
    return user


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """User signup"""
    # Validate persona
    if request.persona not in ["admin", "employee"]:
        raise HTTPException(status_code=400, detail="Persona must be either 'admin' or 'employee'")
    
    # Check if user already exists
    existing_user = await database.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = get_password_hash(request.password)
    
    # Create user
    user_data = {
        "name": request.name,
        "email": request.email,
        "password": hashed_password,
        "persona": request.persona,
        "created_at": datetime.utcnow(),
        "auth_provider": "email"
    }
    
    result = await database.users.insert_one(user_data)
    user_id = str(result.inserted_id)
    
    # Create token
    token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": request.name,
            "email": request.email,
            "persona": request.persona
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """User login"""
    # Find user
    user = await database.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(request.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = str(user["_id"])
    
    # Create token
    token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": user.get("name"),
            "email": user.get("email"),
            "persona": user.get("persona", "employee")  # Default to employee for existing users
        }
    }


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleAuthRequest):
    """Google OAuth authentication"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500, 
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID in environment variables."
        )
    
    try:
        # Verify Google token
        idinfo = id_token.verify_oauth2_token(
            request.token, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get("email")
        name = idinfo.get("name", email.split("@")[0])
        google_id = idinfo.get("sub")
        
        # Find or create user
        user = await database.users.find_one({"email": email})
        
        if user:
            # User exists, update if needed
            user_id = str(user["_id"])
        else:
            # Create new user - default to employee for Google OAuth
            user_data = {
                "name": name,
                "email": email,
                "google_id": google_id,
                "persona": "employee",  # Default to employee for Google signups
                "created_at": datetime.utcnow(),
                "auth_provider": "google"
            }
            result = await database.users.insert_one(user_data)
            user_id = str(result.inserted_id)
            user = await database.users.find_one({"_id": result.inserted_id})
        
        # Create token
        token = create_access_token(data={"sub": user_id})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "name": user.get("name"),
                "email": user.get("email"),
                "persona": user.get("persona", "employee")
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return current_user

