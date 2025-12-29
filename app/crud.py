from typing import Literal
from xxlimited import new
import app.models as models
import app.security as security
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from sqlmodel import Session, select
from sqlalchemy.sql import literal
from enum import IntEnum
from datetime import date, datetime, timedelta
from typing import Optional, List
import random
import json
from app.logger import get_logger

logger = get_logger("crud")

MEAL_WINDOWS = {
    0: 'breakfast',
    1: 'lunch',
    2: 'eveningSnack',
    3: 'dinner'
}

WINDOW_TO_INT = {v: k for k, v in MEAL_WINDOWS.items()}

def getUser(session: Session, id: int):

    statement = select(models.User).where(models.User.id == id)
    user = session.exec(statement).first()
    return user

def getUserByEmail(session: Session, email: str):

    statement = select(models.User).where(models.User.email == email)
    user = session.exec(statement).first()
    return user

def authenticateUser(session: Session, userCredentials: models.UserLogin):
    user = getUserByEmail(session, userCredentials.email)
<<<<<<< HEAD
=======
    
>>>>>>> 88c7569 (-Added logging -Fixed bugs related to meal triggers and old meal cleanups -Other code cleanup)
    if user and security.verifyPassword(userCredentials.password, user.hashedPassword):
        logger.info("User authentication successful", extra={"user_id": user.id})
        return user
    
    logger.warning("User authentication failed", extra={"email": userCredentials.email})
    return None

def createUser(session: Session, userData: models.UserCreate):
    hashedPassword = security.getHashedPassword(userData.password)

    newUser = models.User(
        email=userData.email,
        firstName=userData.firstName,
        lastName=userData.lastName,
        hashedPassword=hashedPassword
    )

    session.add(newUser)
    session.commit()
    session.refresh(newUser)
    
    logger.info("New user created", extra={"user_id": newUser.id, "email": newUser.email})

    return newUser

def getPantryByNameAndUser(session: Session, userId: int, name: str):

    statement = select(models.Pantry).where(models.Pantry.userId == userId).where(models.Pantry.pantryNickname == name)
    pantryForUser = session.exec(statement).first()

    return pantryForUser

def createPantryForUser(session: Session, userId: int, pantryData: models.PantryCreate):

    newPantry = models.Pantry(
        userId=userId,
        pantryNickname=pantryData.pantryNickname
    )

    session.add(newPantry)
    session.commit()
    session.refresh(newPantry)

    logger.info("Pantry created", extra={"user_id": userId, "pantry_id": newPantry.pantryId})

    return newPantry

def getPantriesForUser(session: Session, userId: int):

    statement = select(models.Pantry).where(models.Pantry.userId == userId)
    pantries = session.exec(statement).all()
    return pantries

def checkAndAddItem(session: Session, itemName: str, brand: str):
    statement = select(models.Item).where(models.Item.itemName == itemName).where(models.Item.brand == brand)
    item = session.exec(statement).first()

    if item:
        return item
    
    newItem = models.Item(
        brand=brand,
        itemName=itemName,
        avgShelfLife=5 #@changeNeeded - get the average shelf life or have user input it
    )

    session.add(newItem)
    session.commit()
    session.refresh(newItem)

    logger.info("New Item added to Global Catalog", extra={"item_name": itemName, "item_id": newItem.itemId})

    return newItem

def getSecurePantry(session: Session, pantryId: int, userId: int):
    statement = select(models.Pantry).where(models.Pantry.pantryId == pantryId).where(models.Pantry.userId == userId)
    pantryFound = session.exec(statement).first()

    if pantryFound:
        return pantryFound
    return None

def addItemToPantry(session: Session, pantryItemData: models.PantryItemCreate, pantryId: int):

    item = checkAndAddItem(session, pantryItemData.itemName, pantryItemData.brand)
    
    newPantryItem = models.PantryItem(
        purchaseDate=pantryItemData.purchaseDate, #changeNeeded - curr assuming user provides date
        pantryId=pantryId,
        itemId=item.itemId,
        quantity=pantryItemData.quantity,
        unit=pantryItemData.unit
    )
    session.add(newPantryItem)
    session.commit()
    session.refresh(newPantryItem)

    return newPantryItem

def getItemsToUseForMeals(session: Session, userId: int, userSuggestions: Optional[models.MealRequestPriorityItems]):
    """
    This is the "textbook" efficient data-fetching function.
    It builds a *single* SQL query that does three jobs at once:

    1. .select(models.PantryItem):
       Specifies the main table we want to get (our inventory).

    2. .join(models.Pantry).where(models.Pantry.userId == userId):
       This is the "SECURITY/AUTHORIZATION" step.
       It joins the Pantry table *only* to filter by the
       logged-in user's ID, ensuring a user can
       *only* ever see their own items.

    3. .options(selectinload(models.PantryItem.item)):
       This is the "PERFORMANCE/N+1 FIX" step.
       It "eagerly loads" the related 'Item' (catalog) data
       in the *same* query. This prevents our app from
       running N+1 separate queries in a loop later.
    """
    
    statementForAllItems = (
        select(models.PantryItem)
        .join(models.Pantry)
        .where(models.Pantry.userId == userId)
        .options(selectinload(models.PantryItem.item)))

    allUserItems = session.exec(statementForAllItems).all()

    priorityItems = []
    if userSuggestions:
        pantryIds = userSuggestions.priorityPantryIds
        pantryItemIds = userSuggestions.priorityPantryItemIds

        """
        A different way this can be achieved is by using a hash map on allItems.
        In services, we iterate through all items once to form their names which is when we can map pantryItemId to name
        Later we can iterate through pantryItemIds from user and can add these names to the high priority list
        """
        if pantryIds or pantryItemIds:

            priorityPantryCond = models.Pantry.pantryId.in_(pantryIds) if pantryIds else literal(False)
            priorityItemCond = models.PantryItem.id.in_(pantryItemIds) if pantryItemIds else literal(False)

            statementForPriorityItems = (
                select(models.PantryItem)
                .join(models.Pantry)
                .where(
                    models.Pantry.userId == userId,
                    or_(priorityPantryCond, priorityItemCond))
                .options(selectinload(models.PantryItem.item)))
            '''
            Explanation for the where clause: 
            WHERE pantry.userId = :userId
            AND (FALSE OR FALSE)
            '''

            priorityItems = session.exec(statementForPriorityItems).all()
            logger.info("Retrieved priority items", extra={"user_id": userId, "count": len(priorityItems)})
    
    return {
            'allItems': allUserItems, 
            'priorityItems': priorityItems
            }

def getIngredientQtyFromDb(session, userId, ingredientsIds: list[int]):

    statement = select(models.PantryItem.id, models.PantryItem.quantity, models.PantryItem.unit).join(models.Pantry).where(models.Pantry.userId==userId,models.PantryItem.id.in_(ingredientsIds))
    ingredientQtyInDb = session.exec(statement).all()
    return ingredientQtyInDb

def updateQuantitiesAfterMeal(session, userId, remainingQuantityMap):

    statement = (
        select(models.PantryItem)
        .join(models.Pantry)
        .where(models.Pantry.userId == userId,
            models.PantryItem.id.in_(remainingQuantityMap.keys())))
    
    ingredients = session.exec(statement).all()

    count = 0
    for ingredient in ingredients:
        count += 1
        ingredient.quantity = remainingQuantityMap[ingredient.id][0]
        ingredient.unit = remainingQuantityMap[ingredient.id][1]
    
    session.commit()
    logger.info("Updated inventory quantities", extra={"user_id": userId, "items_updated": count})

def createUserPreferences(session, userId):

    offset = random.randint(0, 30)
    newUserPreferenceEntry = models.UserPreferences(
        userId=userId,
        loadBalancerOffset=offset
    )
    session.add(newUserPreferenceEntry)
    session.commit()
    session.refresh(newUserPreferenceEntry)

    return newUserPreferenceEntry 

def getDueUsersByMealTriggers(session, now):
    statement = select(models.UserMealTrigger).where(models.UserMealTrigger.nextRun <= now)
    usersForMealCompute = session.exec(statement).all()

    if len(usersForMealCompute) > 0:
        logger.info("Found users due for meal generation", extra={"count": len(usersForMealCompute), "trigger_time": now.isoformat()})

    return usersForMealCompute

def getUserPreferences(session, userId):
    statement = select(models.UserPreferences).where(models.UserPreferences.userId == userId)
    userPreferences = session.exec(statement).first()
    return userPreferences

def updateNextRunForUser(userMealTriggerDbObject: models.UserMealTrigger, nextRun, nextMealWindowKey):

    userMealTriggerDbObject.nextRun = nextRun
    userMealTriggerDbObject.nextMealWindowToCompute = nextMealWindowKey
    return

def updateCurrentWindowEndTime(userMealTriggerObject: models.UserMealTrigger, currentWindowEndTime):
    userMealTriggerObject.toBeDeletedMealId = userMealTriggerObject.currentActiveMeal
    userMealTriggerObject.currentMealWindowEndTime = currentWindowEndTime
    return

def createNextTriggerEntryForUser(session, userMealTriggerEntry):
    session.add(userMealTriggerEntry)
    return 

def storeProactiveMealSuggestions(session, userId, suggestionsJson, mealWindow):

    newSuggestionForUser = models.ProactiveMealSuggestions(
        userId=userId,
        suggestionsJson=suggestionsJson,
        mealWindow=mealWindow
    )

    session.add(newSuggestionForUser)
    session.commit()
    session.refresh(newSuggestionForUser)

    logger.info("Stored proactive meal suggestion", extra={"userId": userId, "window": mealWindow})

    statement = select(models.UserMealTrigger).where(newSuggestionForUser.userId == models.UserMealTrigger.userId)
    userTrigger = session.exec(statement).first()

    if userTrigger:
        userTrigger.currentActiveMeal = newSuggestionForUser.id
        session.add(userTrigger)
        session.commit()

    return newSuggestionForUser

def getCurrentMeals(session: Session, userId: int):

    statement = (select(models.ProactiveMealSuggestions)
                .where(models.ProactiveMealSuggestions.userId == userId,
                    models.ProactiveMealSuggestions.consumed == False))
    
    currentMeals = session.exec(statement).all()

    newMealSuggestionResponse = models.ProactiveMealResponse()

    for meal in currentMeals:
        parsed = json.loads(meal.suggestionsJson)
        setattr(newMealSuggestionResponse, meal.mealWindow, parsed)

    return newMealSuggestionResponse

def cleanOldMeals(session, now):
    logger.info("Looking for meals to delete")
    statement = (select(models.ProactiveMealSuggestions, models.UserMealTrigger).
                join(models.UserMealTrigger, models.ProactiveMealSuggestions.id == models.UserMealTrigger.toBeDeletedMealId).
                where(( models.UserMealTrigger.currentMealWindowEndTime <= now)))

    results = session.exec(statement).all()
    
    affectedUsers = []
    deletedCount = 0
    for meal, trigger in results:
        session.delete(meal)
        affectedUsers.append(trigger.userId)
        trigger.toBeDeletedMealId = None
        session.add(trigger)
        deletedCount += 1
        
    if deletedCount > 0:
        logger.info("Cleaned up old meals", extra={"deletedCount":deletedCount})
    
    return affectedUsers

def markNewMealAsCurrentMeal(session, userId, newMealId):

    logger.info("Updating current active meal id for user in UserMealTrigger", extra={"userId": userId, "mealId": newMealId})
    statement = select(models.UserMealTrigger).where(models.UserMealTrigger.userId == userId)
    userTriggers = session.exec(statement).first()

    userTriggers.currentActiveMeal = newMealId
    session.add(userTriggers)
    session.commit()
    return
