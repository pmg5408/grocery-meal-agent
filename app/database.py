from curses import echo
import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, SQLModel
import redis
from app.logger import get_logger

logger = get_logger("database")

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432") # Default to standard 5432
DB_USER = os.getenv("DB_USER", "pantry")
DB_PASSWORD = os.getenv("DB_PASSWORD", "pantry")
DB_NAME = os.getenv("DB_NAME", "pantry")

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

safe_url = DATABASE_URL.split("@")[-1]
logger.info(f"Connecting to database at {safe_url}")

fastapi_engine = create_engine(DATABASE_URL, echo=False)
celery_engine = create_engine(DATABASE_URL, echo=False)

def createDbAndTables():
    '''
    this class will be responsible to create tables
    '''
    try:
        SQLModel.metadata.create_all(fastapi_engine)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.critical(f"Database schema creation failed: {str(e)}")
        raise e

def getFastApiSession():
    '''
    FastAPI will call this function for every API request that needs a db connection.
    Uses the FastAPI-specific engine.
    '''
    with Session(fastapi_engine) as session:
        yield session

def getCelerySession():
    '''
    Celery tasks will use this function for database operations.
    Uses the Celery-specific engine.
    '''
    with Session(celery_engine) as session:
        yield session

def getRedisClient():
    '''
    Returns a Redis client instance for rate limiting and other operations.
    Uses the REDIS_URL from environment variables.
    '''
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        redis_client = redis.from_url(REDIS_URL)
        # Test the connection
        redis_client.ping()
        logger.info(f"Redis client connected successfully to {REDIS_URL}")
        return redis_client
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {str(e)}")
        raise e
