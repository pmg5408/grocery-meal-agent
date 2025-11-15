from typing import Literal
import app.models as models
import app.security as security
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from sqlmodel import Session, select
from sqlalchemy.sql import literal

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
    print(userCredentials.password)
    if user and security.verifyPassword(userCredentials.password, user.hashedPassword):
        return user

    return None

def createUser(session: Session, userData: models.UserCreate):
    print(userData.password)
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
        quantity=pantryItemData.quantity
    )
    session.add(newPantryItem)
    session.commit()
    session.refresh(newPantryItem)

    return newPantryItem

def getItemsToUseForMeals(session: Session, userId: int, userSuggestions: models.MealRequestPriorityItems):
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

    pantryIds = userSuggestions.priorityPantryIds
    pantryItemIds = userSuggestions.priorityPantryItemIds

    priorityItems = []
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
    
    return {
            'allItems': allUserItems, 
            'priorityItems': priorityItems
            }

    
