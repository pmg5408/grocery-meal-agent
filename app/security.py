from base64 import decode
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Create a single, reusable CryptContext
# This is our "hashing engine"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def getHashedPassword(password: str) -> str:
    return pwd_context.hash(password)

def verifyPassword(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

import jwt
from datetime import datetime, timedelta

SECRET_KEY = "REPLACE_WITH_A_REAL_SECRET"
ALGORITHM = "HS256"

def createJwt(userId: int):
    payload = {
        "userId": userId,
        "exp": datetime.utcnow() + timedelta(days=3),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

auth_scheme = HTTPBearer()

def decodeJwt(token: str):
    try: 
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded["userId"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token."
        )

def verifyJwt(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    return decodeJwt(token)


