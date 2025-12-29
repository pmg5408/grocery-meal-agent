from curses import echo
import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, SQLModel
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

engine = create_engine(DATABASE_URL, echo=False)

def createDbAndTables():
    '''
    this class will be responsible to create tables
    '''
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.critical(f"Database schema creation failed: {str(e)}")
        raise e

def getSession():
    '''
    FastAPI will call this function for every API request that needs a db connection
    '''
    with Session(engine) as session:
        yield session