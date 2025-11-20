from dataclasses import field
from datetime import datetime, time
from msilib import Table
from sqlmodel import SQLModel, Field, Relationship, Index
from typing import Optional, List

'''
Different classes for user and their use cases.
UserBase - Base Class with attributes common between other user classes
User - Class representing User table. Will contain additional attr like id
UserCreate - Class representing data we will accept via a POST request
UserRead - Class representing data we will return for a GEt request
UserUpdate - Class representing data for patch requests
'''

'''
------User Models-------
'''
class UserBase(SQLModel):
    email: str
    firstName: str
    lastName: Optional[str] = None

class User(UserBase, table=True):
    '''
    User table contains all the user information
    has .pantries which links it to the pantry table
    '''
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashedPassword: str

    pantries: list["Pantry"] = Relationship(back_populates="user")
    mealSuggestions: list["ProactiveMealSuggestions"] = Relationship(back_populates="user")
    preferences: List["UserPreferences"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int

class UserLogin(SQLModel):
    email: str
    password: str

'''
-------Pantry Models--------
'''
class PantryBase(SQLModel):
    pantryNickname: str

class Pantry(PantryBase, table=True):
    '''
    Pantry table has data for all the pantries
    a user can have multiple pantries. 
    so we need to a userId field to connect a pantry to a user
    and it acts as a foreign key in the pantry table
    defines a 1-to-many relationship between user and pantry
    .user is used to link it to the user table
    '''
    pantryId: Optional[int] = Field(default=None, primary_key=True)
    userId: int = Field(foreign_key="user.id")
    pantryNickname: str = Field(index=True)

    # this is the python only attr for the relationship
    # it uses back_populates to link to the pantries attr of the User model 
    user: "User" = Relationship(back_populates="pantries")

    #pantryItems lets us get al the pantryItem objects that belong to this pantry
    pantryItems: list["PantryItem"] = Relationship(back_populates="pantry")

class PantryCreate(PantryBase):
    pass

class PantryRead(PantryBase):
    pantryId: int
    userId: int

'''
--------Item Models---------
'''
class ItemBase(SQLModel):
    itemName: Optional[str]
    brand: Optional[str]

class Item(ItemBase, table=True):
    '''
    Item class stores data about every item ever seen
    currently most useful to store shelf life
    which is an attr common to an item regardless of the pantry it belongs to
    in futuree if there are more fields native to an item, add here
    '''
    itemId: Optional[int] = Field(default=None, primary_key=True)
    itemName: Optional[str] = Field(index=True)
    avgShelfLife: Optional[int]

    # lets us get all the pantryItem objects this item is a part of 
    itemToPantries: list["PantryItem"] = Relationship(back_populates="item")

class ItemCreate(ItemBase):
    '''
    this model does not interact with the user
    it is used by backend to verify data before it adds new item to db
    '''
    avgShelfLife: Optional[int] = None

class ItemRead(ItemBase):
    itemId: int
    avgShelfLife: Optional[int] = None

'''
-------PantryItem Moodels---------
'''
class PantryItemBase(SQLModel):
    quantity: float
    unit: Optional[str]
    purchaseDate: datetime

class PantryItem(PantryItemBase, table=True):
    '''
    PantryItem class acts as the model to store every item in a pantry
    Each row will have a pantryId and an itemId
    Basically each item will be a separate row
    Defines the many-to-many relationship 
    between pantry and item
    '''
    id: Optional[int] = Field(default=None, primary_key=True)
    purchaseDate: datetime = Field(default_factory=datetime.utcnow)

    pantryId: int = Field(foreign_key="pantry.pantryId")
    itemId: int = Field(foreign_key="item.itemId")

    # pantry lets us get the Pantry obj this PantryItem belongs to
    pantry: "Pantry" = Relationship(back_populates="pantryItems")

    # item lets us get the Item obj that this row represents
    item: "Item" = Relationship(back_populates="itemToPantries")

class PantryItemCreate(PantryItemBase):
    '''
    The user will interact only with this data model
    and not the item data model
    The item data model is for us to use
    if we want to add a new item to db
    '''
    itemName: Optional[str]
    brand: Optional[str]

class PantryItemRead(PantryItemBase):
    id: int
    pantryId: int
    itemId: int

class PantryItemReadWithItem(PantryItemRead):
    '''
    this read actually returns the item details
    these item details are validated using the ItemRead class
    '''
    item: ItemRead

"""
--------------Meal Trigger---------------
"""
class MealRequestPriorityItems(SQLModel):
    priorityPantryItemIds: Optional[List[int]] = Field(default_factory=list)
    priorityPantryIds: Optional[List[int]] = Field(default_factory=list)

class LLMItemInput(SQLModel):
    pantryItemId: int
    ingredientName: str
    ingredientBrand: Optional[str]
    quantity: float
    unit: Optional[str]
    daysOwned: int

class Ingredient(SQLModel):
    pantryItemId: Optional[int] = Field(description="This is the id that was attached to the ingredient in the input")
    ingredientName: str = Field(description="The exact name of the pantry item used.")
    quantity: float = Field(description="The numerical quantity used (e.g., 2, 0.5).")
    unit: str = Field(description="The unit of measurement (e.g., 'count', 'cups', 'g').")

class Recipe(SQLModel):
    description: str = Field(description="A 1-sentence description of the meal.")
    ingredients: List[Ingredient]
    steps: List[str]
    timeRequired: str = Field(description="Approximate time required to prepare the meal e.g., '25 minutes'")

class RecipeSuggestions(SQLModel):
    recipes: List[Recipe]

class IngredientUsage(SQLModel):
    pantryItemId: int
    quantityUsed: float
    unitQtyUsed: Optional[str]
    qtyInDb: float
    unitInDb: Optional[str]

class IngredientDeduction(SQLModel):
    pantryItemId: int
    quantityRemaining: float
    unit: str

class OutputIngredientDeduction(SQLModel):
    ingredientsUsed: List[IngredientDeduction]

"""
=============================== User Meal Preference Time Model ============================== 
"""

class UserPreferences(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    userId: int = Field(foreign_key="user.id")
    
    breakfast: time = Field(default=time(8, 0))
    lunch: time = Field(default=time(12, 0))
    eveningSnack: time = Field(default=time(16, 0))
    dinner: time = Field(default=time(18, 0))

    loadBalancerOffset: int = Field(default=0)

    user: "User" = Relationship(back_populates="preferences")

class ProactiveMealSuggestions(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    userId: int = Field(foreign_key="user.id")

    mealWindow: str
    suggestionsJson: str
    generatedAt: datetime = Field(default=datetime.utcnow())

    user: "User" = Relationship(back_populates="mealSuggestions") 

class UserMealTrigger(SQLModel, table=True):
    __table_args__ = (Index("idx_nextRun", "nextRun"), )

    id: Optional[int] = Field(default=None, primary_key=True)

    userId: int = Field(foreign_key="user.id")

    #************* Might need debugging *******************
    mealWindow: int # same as above (“breakfast”, etc.)

    nextRun: datetime  # precomputed timestamp
    user: Optional["User"] = Relationship()

