from passlib.context import CryptContext

# Create a single, reusable CryptContext
# This is our "hashing engine"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def getHashedPassword(password: str) -> str:
    return pwd_context.hash(password)

def verifyPassword(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)