# controllers/auth_controller.py
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from passlib.context import CryptContext
from jose import jwt, JWTError
from dotenv import load_dotenv
from bson import ObjectId

from email_helper import send_reset_email
from models.password_request_email import PasswordResetRequest
from models.user_model import UserRegister, UserLogin, UserResponse
from database import users_collection

load_dotenv()

# --------------------------------------------------------------------
# Environment configuration
# --------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

router = APIRouter(prefix="/auth", tags=["Auth"])

# --------------------------------------------------------------------
# Use Argon2 (stronger and avoids bcrypt issues)
# pip install passlib[argon2]
# --------------------------------------------------------------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --------------------------------------------------------------------
# Password utilities
# --------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash password using Argon2 algorithm."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

# --------------------------------------------------------------------
# JWT token creation
# --------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@router.post("/register", response_model=UserResponse)
async def register(user: UserRegister):
    """Register a new user."""
    # Ensure unique email
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password and save user
    hashed_pw = hash_password(user.password)
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password_hash": hashed_pw,
        "role": "EndUser",
        "profile_info": None,
        "created_at": datetime.utcnow(),
    }
    result = await users_collection.insert_one(user_doc)

    return UserResponse(
        user_id=str(result.inserted_id),
        username=user.username,
        email=user.email,
        role=user_doc["role"],
        profile_info=user_doc["profile_info"],
    )

@router.post("/login")
async def login(user: UserLogin):
    """Authenticate user and return JWT token."""
    db_user = await users_collection.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(
        {"sub": str(db_user["_id"]), "email": db_user["email"], "role": db_user.get("role", "EndUser")}
    )
    user_data = {
        "user_id": str(db_user["_id"]),
        "email": db_user["email"],
        "username": db_user.get("username"),
        "role": db_user.get("role", "EndUser")
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }

@router.post("/reset_password")
async def reset_password(request: PasswordResetRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    token_data = {
        "sub": user["email"],
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    reset_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Create reset link (example: frontend route)
    reset_link = f"http://localhost:5173/reset-password?token={reset_token}"
    await send_reset_email(request.email, reset_link)
    return {"message": "Password reset link sent to your email"}


@router.post("/update_password")
async def update_password(data: dict):
    token = data.get("token")
    new_password = data.get("new_password")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")

        hashed_password = pwd_context.hash(new_password)
        await users_collection.update_one({"email": email}, {"$set": {"password_hash": hashed_password}})
        return {"message": "Password updated successfully"}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
