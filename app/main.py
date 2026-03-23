import asyncio
from app.database import createDbAndTables, getFastApiSession
from fastapi import FastAPI, Depends, status, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import List
import app.models as models
import app.crud as crud
import app.services as services
import app.security as security
from app.rate_limiter import check_rate_limit
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import get_logger, requestIdContext
import uuid
from app.sse_manager import create_sse_response, redis_listener as sse_redis_listener
from app.security import verifyJwtSSE
from app.a2a.router import router as a2aRouter

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        requestId = str(uuid.uuid4())
        
        token = requestIdContext.set(requestId)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = requestId
            return response
        finally:
            requestIdContext.reset(token)

app = FastAPI()
app.include_router(a2aRouter)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.0.18:3000",
    "smart-pantry-liard.vercel.app",
    "https://smart-pantry-liard.vercel.app",
]

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# Add rate limiting middleware
app.middleware("http")(check_rate_limit)

logger = get_logger("main")

backgroundTasks = set()

@app.on_event("startup")
def startup():
    logger.info("Application starting up...")
    createDbAndTables()
    logger.info("Database schema initialized.")


@app.on_event("startup")
async def startSSERedisListener():
    logger.info("Starting SSE Redis Listener background task...")
    task = asyncio.create_task(sse_redis_listener())
    backgroundTasks.add(task)
    task.add_done_callback(backgroundTasks.discard)
    logger.info("SSE Redis Listener attached to background tasks.")

@app.post("/user/register/", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
def createUserEndpoint(userData: models.UserCreate, session: Session = Depends(getFastApiSession)):
    try:
        newUser = services.registerNewUser(session, userData)
        logger.info("User registered successfully", extra={"user_id": newUser.id})
        return newUser
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", extra={"email": userData.email})
        raise e

@app.post("/user/login/", response_model=models.LoginResponse)
def loginUserEndpoint(userCredentials: models.UserLogin, session: Session = Depends(getFastApiSession)):
    loggedUser = crud.authenticateUser(session, userCredentials)

    if not loggedUser:
        logger.warning("Failed login attempt", extra={"email": userCredentials.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    
    token = security.createJwt(loggedUser.id)
    logger.info("User logged in successfully", extra={"user_id": loggedUser.id})
    newLoginResponse = models.LoginResponse(
        email=loggedUser.email,
        firstName=loggedUser.firstName,
        lastName=loggedUser.lastName,
        id=loggedUser.id,
        accessToken=token
    )

    return newLoginResponse
    

@app.get("/user/me", response_model=models.UserRead)
def getUserEndpoint(session: Session = Depends(getFastApiSession), userId = Depends(security.verifyJwt)):

    existingUser = crud.getUser(session, userId)

    if not existingUser:
        logger.warning("User/me requested for non-existent user", extra={"user_id": userId})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    return existingUser

@app.post("/pantry", response_model=models.PantryRead, status_code=status.HTTP_201_CREATED)
def createPantryEndpoint(pantryData: models.PantryCreate, session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):
    logger.info("Creating new pantry", extra={"user_id": userId, "pantry_name": pantryData.pantryNickname})
    pantryForUser = crud.getPantryByNameAndUser(session, userId, pantryData.pantryNickname)

    if pantryForUser:
        logger.warning("Pantry creation failed: Name collision", extra={"user_id": userId, "pantry_name": pantryData.pantryNickname})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry with name already exists for user"
        )
    
    newPantry = crud.createPantryForUser(session, userId, pantryData)

    return newPantry

@app.get("/pantries", response_model=list[models.PantryRead])
def getPantriesEndpoint(session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):

    pantriesForUser = crud.getPantriesForUser(session, userId)
    return pantriesForUser

@app.post("/pantry/{pantryId}/item", response_model=models.PantryItemReadWithItem, status_code=status.HTTP_201_CREATED)
def addPantryItemEndpoint(pantryId: int, pantryItemData: models.PantryItemCreate, session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):
    if not crud.getSecurePantry(session, pantryId, userId):
        logger.warning("Unauthorized pantry access attempt", extra={"user_id": userId, "pantry_id": pantryId})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry does not belong to current user"
        )

    pantryItem = crud.addItemToPantry(session, pantryItemData, pantryId)
    logger.info("Item added to pantry", extra={"user_id": userId, "pantry_id": pantryId, "item_id": pantryItem.itemId})
    return pantryItem

@app.get("/{pantryId}/items", response_model=list[models.PantryItemReadWithItem])
def getItemsForPantryEndpoint(pantryId: int, session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):
    
    pantry = crud.getSecurePantry(session, pantryId, userId)
    if not pantry:
        logger.warning("Unauthorized pantry view attempt", extra={"user_id": userId, "pantry_id": pantryId})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pantry does not belong to current user"
        )

    return pantry.pantryItems

@app.post("/pantry/suggestMeal", response_model=models.RecipeSuggestions, status_code=status.HTTP_200_OK)
def requestRecipeSuggestionEndpoint(userSuggestions: models.MealRequestPriorityItems, session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):
    logger.info("Manual meal suggestion requested", extra={"user_id": userId})
    recipes = services.getRecipeSuggestions(session, userId, userSuggestions=userSuggestions)
    return recipes

@app.post("/selectedMeal", status_code=status.HTTP_200_OK)
def deductIngredientsFromDb(ingredients: List[models.Ingredient], session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):
    logger.info("Processing meal selection (Inventory Deduction)", extra={"user_id": userId, "ingredient_count": len(ingredients)})
    remainingQuantities = services.getQuantityToDeduct(session, userId, ingredients)
    remainingQtyMap = {}
    for quantity in remainingQuantities.ingredientsUsed:
        remainingQtyMap[quantity.pantryItemId] = (quantity.quantityRemaining, quantity.unit)
    crud.updateQuantitiesAfterMeal(session, userId, remainingQtyMap)
    logger.info("Inventory deduction completed", extra={"user_id": userId})
    return 

@app.get("/proactiveMeals/", response_model=models.ProactiveMealResponse)
def getCurrentMealSuggestions(session: Session = Depends(getFastApiSession), userId: int = Depends(security.verifyJwt)):
    proactiveMealResponse = crud.getCurrentMeals(session, userId)
    return proactiveMealResponse.model_dump(exclude_none=False)

@app.get("/events")
async def eventsEndpoint(
    request: Request,
    userId: int = Depends(verifyJwtSSE)
):
    """
    Server-Sent Events endpoint for real-time meal notifications.
    
    This replaces WebSocket-based notifications with SSE, which is:
    - Simpler (one-way communication only)
    - HTTP-based (firewall/proxy friendly)
    - Auto-reconnecting with EventSource API
    
    Events:
    - connected: Initial connection established
    - meal_ready: A new meal has been generated for the user
    """
    logger.info("SSE connection requested", extra={"user_id": userId})
    return create_sse_response(userId, request)





