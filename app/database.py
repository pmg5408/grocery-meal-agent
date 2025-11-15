from curses import echo
import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, SQLModel

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5433"

# database connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# create a db engine. This will handle all connections to db
# echo=True prints all sql statements to terminal
engine = create_engine(DATABASE_URL, echo=True)

def createDbAndTables():
    '''
    this class will be responsible to create tables
    '''
    SQLModel.metadata.create_all(engine) 

def getSession():
    '''
    FastAPI will call this function for every API request that needs a db connection

    A "Session" is the object that you use to actually run
    queries and make changes.

    Session(engine) creates this session object
    '''
    with Session(engine) as session:
        yield session