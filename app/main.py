from urllib import response
from app.database import createDbAndTables, getSession
from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel #used for data validation
from sqlmodel import Session
import app.models as models
import app.crud as crud
import app.services as services

#app is the main object that will handle everything
app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.0.18:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

@app.on_event("startup")
def startup():
    createDbAndTables()

def getUserId():
    return 2

@app.post("/user/register/", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
def createUserEndpoint(userData: models.UserCreate, session: Session = Depends(getSession)):
    existingUser = crud.getUserByEmail(session, userData.email)

    if existingUser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    newUser = crud.createUser(session, userData)
    return newUser

@app.post("/user/login/", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
def loginUserEndpoint(userCredentials: models.UserLogin, session: Session = Depends(getSession)):
    loggedUser = crud.authenticateUser(session, userCredentials)

    if not loggedUser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    return loggedUser
    

@app.get("/user/me", response_model=models.UserRead)
def getUserEndpoint(session: Session = Depends(getSession), userId = Depends(getUserId)):

    existingUser = crud.getUser(session, userId)

    if not existingUser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    return existingUser

@app.post("/pantry/", response_model=models.PantryRead, status_code=status.HTTP_201_CREATED)
def createPantryEndpoint(pantryData: models.PantryCreate, session: Session = Depends(getSession), userId: int = Depends(getUserId)):

    pantryForUser = crud.getPantryByNameAndUser(session, userId, pantryData.pantryNickname)

    if pantryForUser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry with name already exists for user"
        )
    
    newPantry = crud.createPantryForUser(session, userId, pantryData)

    return newPantry

@app.get("/pantries/", response_model=list[models.PantryRead])
def getPantriesEndpoint(session: Session = Depends(getSession), userId: int = Depends(getUserId)):

    pantriesForUser = crud.getPantriesForUser(session, userId)
    return pantriesForUser

@app.post("/pantry/{pantryId}/item", response_model=models.PantryItemReadWithItem, status_code=status.HTTP_201_CREATED)
def addPantryItemEndpoint(pantryId: int, pantryItemData: models.PantryItemCreate, session: Session = Depends(getSession), userId: int = Depends(getUserId)):
    if not crud.getSecurePantry(session, pantryId, userId):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry does not belong to current user"
        )

    pantryItem = crud.addItemToPantry(session, pantryItemData, pantryId)
    return pantryItem

@app.get("/{pantryId}/items", response_model=list[models.PantryItemReadWithItem])
def getItemsForPantryEndpoint(pantryId: int, session: Session = Depends(getSession), userId: int = Depends(getUserId)):
    
    pantry = crud.getSecurePantry(session, pantryId, userId)
    if not pantry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry does not belong to current user"
        )

    return pantry.pantryItems

@app.post("/pantry/suggestMeal", response_model=models.RecipeSuggestions, status_code=status.HTTP_200_OK)
def requestRecipeSuggestionEndpoint(userSuggestions: models.MealRequestPriorityItems, session: Session = Depends(getSession), userId: int = Depends(getUserId)):
    
    recipes = services.getRecipeSuggestions(session, userId, userSuggestions)
    return recipes









