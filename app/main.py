import asyncio
from urllib import response
from app.database import createDbAndTables, getSession
from fastapi import FastAPI, Depends, status, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel #used for data validation
from sqlmodel import Session
from typing import List
from app.events import redisListener
import app.models as models
import app.crud as crud
import app.services as services
from app.websocketManager import manager
import app.security as security

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

@app.on_event("startup")
async def startRedisListener():
    asyncio.create_task(redisListener())

def getUserId():
    return 1

@app.websocket("/ws")
async def websocketEndpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")

    try:
        userId = security.decodeJwt(token)
    except:
        await websocket.close()
        return

    await manager.connect(userId, websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(userId)

@app.post("/user/register/", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
def createUserEndpoint(userData: models.UserCreate, session: Session = Depends(getSession)):
    newUser = services.registerNewUser(session, userData)

    return newUser

@app.post("/user/login/", response_model=models.LoginResponse)
def loginUserEndpoint(userCredentials: models.UserLogin, session: Session = Depends(getSession)):
    loggedUser = crud.authenticateUser(session, userCredentials)

    if not loggedUser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    
    token = security.createJwt(loggedUser.id)

    newLoginResponse = models.LoginResponse(
        email=loggedUser.email,
        firstName=loggedUser.firstName,
        lastName=loggedUser.lastName,
        id=loggedUser.id,
        accessToken=token
    )

    return newLoginResponse
    

@app.get("/user/me", response_model=models.UserRead)
def getUserEndpoint(session: Session = Depends(getSession), userId = Depends(security.verifyJwt)):

    existingUser = crud.getUser(session, userId)

    if not existingUser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    return existingUser

@app.post("/pantry", response_model=models.PantryRead, status_code=status.HTTP_201_CREATED)
def createPantryEndpoint(pantryData: models.PantryCreate, session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):

    pantryForUser = crud.getPantryByNameAndUser(session, userId, pantryData.pantryNickname)

    if pantryForUser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry with name already exists for user"
        )
    
    newPantry = crud.createPantryForUser(session, userId, pantryData)

    return newPantry

@app.get("/pantries", response_model=list[models.PantryRead])
def getPantriesEndpoint(session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):

    pantriesForUser = crud.getPantriesForUser(session, userId)
    return pantriesForUser

@app.post("/pantry/{pantryId}/item", response_model=models.PantryItemReadWithItem, status_code=status.HTTP_201_CREATED)
def addPantryItemEndpoint(pantryId: int, pantryItemData: models.PantryItemCreate, session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):
    if not crud.getSecurePantry(session, pantryId, userId):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry does not belong to current user"
        )

    pantryItem = crud.addItemToPantry(session, pantryItemData, pantryId)
    return pantryItem

@app.get("/{pantryId}/items", response_model=list[models.PantryItemReadWithItem])
def getItemsForPantryEndpoint(pantryId: int, session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):
    
    pantry = crud.getSecurePantry(session, pantryId, userId)
    if not pantry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry does not belong to current user"
        )

    return pantry.pantryItems

@app.post("/pantry/suggestMeal", response_model=models.RecipeSuggestions, status_code=status.HTTP_200_OK)
def requestRecipeSuggestionEndpoint(userSuggestions: models.MealRequestPriorityItems, session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):
    
    recipes = services.getRecipeSuggestions(session, userId, userSuggestions=userSuggestions)
    return recipes

@app.post("/selectedMeal", status_code=status.HTTP_200_OK)
def deductIngredientsFromDb(ingredients: List[models.Ingredient], session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):

    remainingQuantities = services.getQuantityToDeduct(session, userId, ingredients)
    remainingQtyMap = {}
    for quantity in remainingQuantities.ingredientsUsed:
        remainingQtyMap[quantity.pantryItemId] = (quantity.quantityRemaining, quantity.unit)
    crud.updateQuantitiesAfterMeal(session, userId, remainingQtyMap)
    return 

@app.get("/proactiveMeals/", response_model=models.ProactiveMealResponse)
def getCurrentMealSuggestions(session: Session = Depends(getSession), userId: int = Depends(security.verifyJwt)):
    proactiveMealResponse = crud.getCurrentMeals(session, userId)
    return proactiveMealResponse.model_dump(exclude_none=False)






