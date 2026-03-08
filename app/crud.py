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
    bucket = random.randint(0, 19)
    newUserPreferenceEntry = models.UserPreferences(
        userId=userId,
        loadBalancerOffset=offset,
        batchGenerationBucket=bucket
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
        mealWindow=mealWindow,
        generatedAt=datetime.utcnow()
    )

    session.add(newSuggestionForUser)
    session.commit()
    session.refresh(newSuggestionForUser)

    logger.info("Stored proactive meal suggestion", extra={"userId": userId, "window": mealWindow})

    return newSuggestionForUser

def getCurrentMeals(session: Session, userId: int):

    statement = (select(models.ProactiveMealSuggestions)
                .where(models.ProactiveMealSuggestions.userId == userId,
                    models.ProactiveMealSuggestions.consumed == False,
                    models.ProactiveMealSuggestions.isActive == True))

    currentMeals = session.exec(statement).all()

    newMealSuggestionResponse = models.ProactiveMealResponse()

    for meal in currentMeals:
        parsed = json.loads(meal.suggestionsJson)
        setattr(newMealSuggestionResponse, meal.mealWindow, parsed)

    return newMealSuggestionResponse

def deactivateMealsByWindowEndTime(session, now):
    """
    Deactivate meals based on window end times.
    This marks meals as inactive when their window has ended.
    """
    logger.info("Looking for meals to deactivate based on window end times")
    statement = (select(models.ProactiveMealSuggestions, models.UserMealTrigger).
                join(models.UserMealTrigger, models.ProactiveMealSuggestions.id == models.UserMealTrigger.toBeDeletedMealId).
                where((models.UserMealTrigger.currentMealWindowEndTime <= now)))

    results = session.exec(statement).all()

    affectedUsers = []
    deactivatedCount = 0
    for meal, trigger in results:
        # Mark meal as inactive instead of deleting it
        meal.isActive = False
        session.add(meal)
        affectedUsers.append(trigger.userId)
        trigger.toBeDeletedMealId = None
        session.add(trigger)
        deactivatedCount += 1

    if deactivatedCount > 0:
        logger.info("Deactivated meals based on window end times", extra={"deactivatedCount": deactivatedCount})

    return affectedUsers

def deleteOldMealsByRetentionPolicy(session, now):
    """
    Delete meals older than 48 hours based on retention policy.
    This removes old inactive meals to keep the database clean.
    """
    logger.info("Looking for meals to delete based on 48-hour retention policy")
    cutoff_time = now - timedelta(hours=48)

    # Find meals older than 48 hours that are inactive
    statement = (select(models.ProactiveMealSuggestions)
                .where(models.ProactiveMealSuggestions.generatedAt <= cutoff_time,
                      models.ProactiveMealSuggestions.isActive == False))

    old_meals = session.exec(statement).all()

    affectedUsers = []
    deletedCount = 0
    for meal in old_meals:
        # Delete the old meal
        session.delete(meal)
        deletedCount += 1
        if meal.userId not in affectedUsers:
            affectedUsers.append(meal.userId)

    if deletedCount > 0:
        logger.info("Deleted old meals based on 48-hour retention policy", extra={
            "deletedCount": deletedCount,
            "cutoff_time": cutoff_time.isoformat()
        })

def cleanOldMeals(session, now):
    """
    Main cleanup function that orchestrates both deactivation and deletion.
    """
    logger.info("Starting meal cleanup process")

    # Deactivate meals based on window end times
    affected_users_1 = deactivateMealsByWindowEndTime(session, now)

    # Delete meals based on retention policy
    deleteOldMealsByRetentionPolicy(session, now)

    logger.info("Meal cleanup process completed", extra={
        "total_affected_users": len(affected_users_1)
    })

    return affected_users_1

def markNewMealAsCurrentMeal(session, userId, newMealId):

    logger.info("Updating current active meal id for user in UserMealTrigger", extra={"userId": userId, "mealId": newMealId})
    statement = select(models.UserMealTrigger).where(models.UserMealTrigger.userId == userId)
    userTriggers = session.exec(statement).first()

    userTriggers.currentActiveMeal = newMealId
    session.add(userTriggers)
    session.commit()
    return

def getUsersByBatchBucket(session: Session, bucketId: int):
    statement = select(models.UserPreferences).where(models.UserPreferences.batchGenerationBucket == bucketId)
    return session.exec(statement).all()

def getUnconsumedMealByWindow(session: Session, userId: int, mealWindow: str):
    statement = select(models.ProactiveMealSuggestions).where(
        models.ProactiveMealSuggestions.userId == userId,
        models.ProactiveMealSuggestions.mealWindow == mealWindow,
        models.ProactiveMealSuggestions.consumed == False
    ).order_by(models.ProactiveMealSuggestions.generatedAt.desc())
    return session.exec(statement).first()

def markMealAsActive(session, mealId):
    statement = select(models.ProactiveMealSuggestions).where(models.ProactiveMealSuggestions.id == mealId)
    meal = session.exec(statement).first()

    if meal:
        meal.isActive = True
        session.add(meal)
        session.commit()
        logger.info("Marked meal as active", extra={"meal_id": mealId})
    return meal

def markMealAsInactive(session, mealId):
    statement = select(models.ProactiveMealSuggestions).where(models.ProactiveMealSuggestions.id == mealId)
    meal = session.exec(statement).first()

    if meal:
        meal.isActive = False
        session.add(meal)
        session.commit()
        logger.info("Marked meal as inactive", extra={"meal_id": mealId})
    return meal


def getTrustedAgentByAgentId(session: Session, agentId: str) -> Optional[models.TrustedAgent]:
    statement = select(models.TrustedAgent).where(models.TrustedAgent.agentId == agentId)
    return session.exec(statement).first()


def createTrustedAgent(
    session: Session,
    agentId: str,
    name: str,
    authMethod: str = "api_key",
    apiKeyHash: Optional[str] = None,
    publicKeyPem: Optional[str] = None,
    allowedTaskTypes: Optional[List[str]] = None,
    rateLimitPerMinute: int = 60,
) -> models.TrustedAgent:
    allowedTaskTypesJson = json.dumps(allowedTaskTypes or [])
    agent = models.TrustedAgent(
        agentId=agentId,
        name=name,
        authMethod=authMethod,
        apiKeyHash=apiKeyHash,
        publicKeyPem=publicKeyPem,
        allowedTaskTypesJson=allowedTaskTypesJson,
        rateLimitPerMinute=rateLimitPerMinute,
        isActive=True,
        updatedAt=datetime.utcnow(),
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    logger.info("Trusted agent created", extra={"agent_id": agentId, "auth_method": authMethod})
    return agent


def createAgentTask(
    session: Session,
    taskId: str,
    callerAgentId: str,
    taskType: str,
    inputPayload: dict,
    idempotencyKey: Optional[str] = None,
    correlationId: Optional[str] = None,
    callbackUrl: Optional[str] = None,
) -> models.AgentTask:
    task = models.AgentTask(
        taskId=taskId,
        callerAgentId=callerAgentId,
        taskType=taskType,
        status="accepted",
        inputJson=json.dumps(inputPayload),
        idempotencyKey=idempotencyKey,
        correlationId=correlationId,
        callbackUrl=callbackUrl,
        updatedAt=datetime.utcnow(),
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("A2A task created", extra={"task_id": taskId, "caller_agent_id": callerAgentId, "task_type": taskType})
    return task


def getAgentTaskByTaskId(session: Session, taskId: str) -> Optional[models.AgentTask]:
    statement = select(models.AgentTask).where(models.AgentTask.taskId == taskId)
    return session.exec(statement).first()


def getAgentTaskByIdempotencyKey(
    session: Session,
    callerAgentId: str,
    idempotencyKey: Optional[str],
) -> Optional[models.AgentTask]:
    if not idempotencyKey:
        return None

    statement = select(models.AgentTask).where(
        models.AgentTask.callerAgentId == callerAgentId,
        models.AgentTask.idempotencyKey == idempotencyKey,
    )
    return session.exec(statement).first()


def updateAgentTaskStatus(
    session: Session,
    task: models.AgentTask,
    status: str,
    startedAt: Optional[datetime] = None,
    finishedAt: Optional[datetime] = None,
) -> models.AgentTask:
    task.status = status
    task.updatedAt = datetime.utcnow()
    if startedAt:
        task.startedAt = startedAt
    if finishedAt:
        task.finishedAt = finishedAt
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("A2A task status updated", extra={"task_id": task.taskId, "status": status})
    return task


def markAgentTaskRunning(session: Session, task: models.AgentTask) -> models.AgentTask:
    now = datetime.utcnow()
    task.status = "running"
    task.attemptCount += 1
    task.startedAt = task.startedAt or now
    task.updatedAt = now
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("A2A task running", extra={"task_id": task.taskId, "attempt_count": task.attemptCount})
    return task


def completeAgentTask(session: Session, task: models.AgentTask, outputPayload: dict) -> models.AgentTask:
    task.status = "completed"
    task.outputJson = json.dumps(outputPayload)
    task.errorJson = None
    task.finishedAt = datetime.utcnow()
    task.updatedAt = task.finishedAt
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("A2A task completed", extra={"task_id": task.taskId})
    return task


def failAgentTask(session: Session, task: models.AgentTask, errorPayload: dict) -> models.AgentTask:
    task.status = "failed"
    task.errorJson = json.dumps(errorPayload)
    task.finishedAt = datetime.utcnow()
    task.updatedAt = task.finishedAt
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.warning("A2A task failed", extra={"task_id": task.taskId})
    return task
