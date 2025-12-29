import bcrypt
from base64 import decode
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
<<<<<<< HEAD

def getHashedPassword(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")

def verifyPassword(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

=======
>>>>>>> 88c7569 (-Added logging -Fixed bugs related to meal triggers and old meal cleanups -Other code cleanup)
import jwt
from datetime import datetime, timedelta
import os
from app.logger import get_logger

logger = get_logger("security")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "REPLACE_WITH_A_REAL_SECRET") 
ALGORITHM = "HS256"

def getHashedPassword(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")

def verifyPassword(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

def createJwt(userId: int):
    payload = {
        "userId": userId,
        "exp": datetime.utcnow() + timedelta(days=3),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    logger.info("JWT Access Token issued", extra={"user_id": userId})
    return token

auth_scheme = HTTPBearer()

def decodeJwt(token: str):
    try: 
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded["userId"]
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: Expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        logger.warning("Token verification failed: Invalid signature/token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token."
        )

def verifyJwt(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    return decodeJwt(token)


