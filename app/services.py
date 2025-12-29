import app.crud as crud
import app.models as models
import os
import json
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from pydantic import TypeAdapter, ValidationError
from typing import List
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from fastapi import HTTPException
from app.logger import get_logger

logger = get_logger("services")

mealOrder = ["breakfast", "lunch", "eveningSnack", "dinner"]

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

JSON_GENERATION_CONFIG = GenerationConfig(
    response_mime_type='application/json'
)

LLM_MODEL = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    generation_config=JSON_GENERATION_CONFIG
)

def registerNewUser(session, userData: models.UserCreate):
    from worker.tasks import getMealsFromLlm
    logger.info("Registering new user", extra={"email": userData.email})
    existingUser = crud.getUserByEmail(session, userData.email)
    if existingUser:
        logger.warning("Registration failed: Email already exists", extra={"email": userData.email})
        raise HTTPException(400, "Email already exists")
    newUser = crud.createUser(session, userData)
    logger.info("User created in DB", extra={"user_id": newUser.id})

    preferences = crud.createUserPreferences(session, newUser.id)
    currentMealWindowKey = computeCurrentWindowForNewUser(preferences)
    
    nextRun, nextMealWindowKey = computeNextMealGenerationTime(preferences, currentMealWindowKey)

    userMealTriggerEntry = models.UserMealTrigger(
        userId=newUser.id,
        nextRun=nextRun,
        nextMealWindowToCompute=nextMealWindowKey
    )
    crud.createNextTriggerEntryForUser(session, userMealTriggerEntry)

    logger.info("Initial scheduling complete", extra={"user_id": newUser.id, "next_run": nextRun.isoformat()})

    session.commit()
    getMealsFromLlm.delay(newUser.id, currentMealWindowKey)
    return newUser


def separatePrioritizedItems(combinedPantryItems):
    userPrioritizedItems = combinedPantryItems['priorityItems']
    allItems = combinedPantryItems['allItems']

    highPriority = []
    normalPriority = []

    for localItem in allItems:
        shelfLife = localItem.item.avgShelfLife
        daysOwned = (datetime.utcnow() - localItem.purchaseDate).days

        llmInputItem = models.LLMItemInput(
            pantryItemId=localItem.id,
            ingredientName=localItem.item.itemName,
            ingredientBrand=localItem.item.brand,
            quantity=localItem.quantity,
            unit=localItem.unit,
            daysOwned=daysOwned
        )

        if shelfLife - daysOwned < 2:
            highPriority.append(llmInputItem.model_dump())
        else:
            normalPriority.append(llmInputItem.model_dump())
    
    for userItem in userPrioritizedItems:
        shelfLife = localItem.item.avgShelfLife
        daysOwned = (datetime.utcnow() - userItem.purchaseDate).days

        llmInputItem = models.LLMItemInput(
            pantryItemId=userItem.id,
            ingredientName=userItem.item.itemName,
            ingredientBrand=userItem.item.brand,
            quantity=userItem.quantity,
            unit=userItem.unit,
            daysOwned=daysOwned
        )
        highPriority.append(llmInputItem.model_dump())
    
    logger.info("Items separated for LLM", extra={
        "high_priority_count": len(highPriority),
        "normal_priority_count": len(normalPriority)
    })
    
    return {
        "allItems": normalPriority,
        "highPriority": highPriority
    }

def getMealBasedOnTime():
    hour = datetime.utcnow().hour
    if hour >= 5 and hour <= 11:
        return "Breakfast"
    elif hour <= 17:
        return "Lunch"
    else:
        return "Dinner" 

def prepareDataForMealSuggestionPrompt(session, userId, userSuggestions):

    combinedPantryItems = crud.getItemsToUseForMeals(session, userId, userSuggestions)
    preparedData = separatePrioritizedItems(combinedPantryItems)

    return preparedData

def getAndParseModelResponse(prompt):
    logger.info("Sending prompt to Gemini LLM...")

    try:
        startTime = datetime.utcnow()
        response = LLM_MODEL.generate_content(prompt)
        endTime = datetime.utcnow()
        duration = (endTime - startTime).total_seconds()
        
        logger.info("Gemini response received", extra={"duration_seconds": duration})
        
        suggestions = models.RecipeSuggestions.model_validate_json(response.text)
        return suggestions
        
    except Exception as e:
        logger.error(f"LLM Generation/Parsing Failed: {str(e)}", extra={"prompt_preview": prompt[:100] + "..."})
        raise e

def buildPrompt(prioritizedItems, meal):
    outputFormat = json.dumps(models.RecipeSuggestions.model_json_schema(), indent=2)
    prompt= f"""
    <task>
    You are a meal-planning assistant. Your goals are:
    1. Reduce food waste by prioritizing expiring items.
    2. Suggest meals that taste normal and are easy to cook.
    3. Respect realistic ingredient pairings and quantities.
    </task>

    <rules>
    - You will receive two ingredient lists:
        • high_priority_ingredients (close to expiry OR user-selected)
        • normal_priority_ingredients (everything else)
    - Some ingredients may appear in BOTH lists — treat them as high priority.
    - You must suggest EXACTLY 3 meal ideas.
    - A “meal” may be:
        • A normal cooked recipe using raw ingredients
        • A ready-to-eat item (e.g., frozen pizza)
        • A main dish + a simple side
    - Do NOT force ingredients together if they don’t fit. Taste > using everything.
    - Pantry staples like oil, salt, pepper, garlic powder can be assumed available.
    - You should maximize:
        1. Use of high-priority items  
        2. Meal quality  
        3. Efficient pantry usage across the day
    - When referencing pantry ingredients (anything from the input lists), you MUST include the exact pantryItemId.
    - When referencing pantry staples (oil, salt, pepper, common spices), you MUST list them as ingredients, but they DO NOT have a pantryItemId.
    - Units of measurement in the recipe MUST use common kitchen-friendly units.
        • Examples: cups, tablespoons, teaspoons, pieces, slices, grams, ounces.
        • Avoid units that humans cannot easily measure while cooking (e.g., “0.13 gallons”, “0.02 liters”, “0.3 pounds”).
        • When the pantry item quantity is stored in a larger unit (e.g., "1 gallon of milk"), you are allowed to convert to smaller, more usable cooking units (e.g., “½ cup milk”).
    - Put '-1' as the pantryItemId for staples.
    </rules>

    <input_format>
    Each ingredient object looks like:
    {{
    "pantryItemId": 24,
    "ingredientName": "Chicken Breast",
    "ingredientBrand": "Kroger",
    "quantity": 2,
    "unit": lbs,
    "purchaseDate": "2024-11-12T14:11:00.000Z"
    }}
    </input_format>

    <output_requirements>
    Your answer MUST be a single valid JSON object.
    It MUST strictly follow this schema:

    {outputFormat}

    Do NOT explain anything.  
    Do NOT add notes.  
    Return ONLY the JSON object.
    </output_requirements>

    <high_priority_ingredients>
    {json.dumps(prioritizedItems["highPriority"], indent=2)}
    </high_priority_ingredients>

    <normal_priority_ingredients>
    {json.dumps(prioritizedItems["allItems"], indent=2)}
    </normal_priority_ingredients>

    <meal_time>
    {meal}
    </meal_time>
    """

    return prompt

def getRecipeSuggestions(session, userId, userSuggestions=None, mealWindow=None):
    logger.info("Generating recipe suggestions", extra={"user_id": userId, "meal_window": mealWindow})

    preparedData = prepareDataForMealSuggestionPrompt(session, userId, userSuggestions)

    if not mealWindow:
        mealWindow = getMealBasedOnTime()

    prompt = buildPrompt(preparedData, mealWindow)

    recipes = getAndParseModelResponse(prompt)

    logger.info("Recipes generated successfully", extra={"count": len(recipes.recipes)})

    return recipes

def getQuantityToDeduct(session, userId, ingredients: List[models.Ingredient]):
    logger.info("Calculating inventory deductions", extra={"user_id": userId})
    ingredientMap = {}
    for ingredient in ingredients:
        if ingredient.pantryItemId != -1:
            ingredientMap[ingredient.pantryItemId] = (ingredient.quantity, ingredient.unit)

    ingredientQtyInDb = crud.getIngredientQtyFromDb(session, userId, list(ingredientMap.keys()))

    ingredientInput = []

    for ingredient in ingredientQtyInDb:
        newIngredientUsage = models.IngredientUsage(
            pantryItemId=ingredient.id,
            quantityUsed=ingredientMap[ingredient.id][0],
            unitQtyUsed=ingredientMap[ingredient.id][1],
            qtyInDb=ingredient.quantity,
            unitInDb=ingredient.unit
        )
        ingredientInput.append(newIngredientUsage.model_dump())

    outputFormat = json.dumps(models.OutputIngredientDeduction.model_json_schema(), indent=2)

    prompt = f"""
    You are an ingredient-deduction assistant for a pantry inventory system.

    Your job is to take recipe usage measurements (human-friendly units) and convert them into the standardized units used by the database. Then calculate the *new remaining quantity and the unit* for each pantry item.

    <rules>
    - Convert only using real culinary unit conversions.
    - NEVER change the intended amount (e.g., “½ cup milk” must convert correctly to mL).
    - ALWAYS convert into the database unit EXACTLY as provided in the input (unitInDb).
    - NEVER hallucinate units or pantry items.
    - If a pantryItemId is missing or the unit is not convertible, return an error object using the output schema.
    - If a pantry item is a staple with no pantryItemId, IGNORE it entirely — return no output for that item.
    - If conversion requires density assumptions, use:
        • Water-like liquids: 1 cup = 240 mL  
        • Milk: 1 cup = 240 mL  
        • Oil: 1 cup = 240 mL  
        • Flour: 1 cup = 120 g  
        • Sugar: 1 cup = 200 g  
        • Rice (uncooked): 1 cup = 185 g  
        • Butter: 1 tablespoon = 14 g  
    - If the input unit is vague (“pinch”, “dash”, “handful”), use common culinary assumptions:
        • pinch = 0.36 g  
        • dash = 0.6 g  
        • handful = 30 g  
    - Always round numerical values to at most **2 decimals**.
    - NEVER output negative remaining quantities — if usage exceeds available, set remainingQty = 0.
    - The final output must be a SINGLE JSON array following the provided schema.

    </rules>

    <inputs>
    You will receive a JSON array of IngredientUsage objects.

    Each IngredientUsage object has the following fields:

    {{
    "pantryItemId": number,
    "quantityUsed": number,
    "unitQtyUsed": string,
    "qtyInDb": number,
    "unitInDb": string
    }}

    Meaning:
    - quantityUsed + unitQtyUsed → user-friendly measurement from recipe.
    - qtyInDb + unitInDb → standardized DB storage for that item.

    Below is the input JSON array:
    {json.dumps(ingredientInput, indent=2)}

    </inputs>

    <task>
    For each ingredient:
    1. Convert (quantityUsed, unitQtyUsed) into the unitInDb using correct cooking conversions.
    2. Compute:
        remainingQty = qtyInDb - convertedUsedQty
    3. Ensure remainingQty ≥ 0.
    4. Produce an output object that matches EXACTLY the schema provided to you:
    {outputFormat}

    Return ONLY a single JSON array following the given output schema.
    Do NOT include explanations.
    Do NOT add text outside JSON.
    </task>

    """

    logger.info("Sending deduction prompt to Gemini...")
    try:
        response = LLM_MODEL.generate_content(prompt)
        responseText = response.text.strip()
        
        try:
            adapter = TypeAdapter(List[models.IngredientDeduction])
            items_list = adapter.validate_json(responseText)

            remainingQuantities = models.OutputIngredientDeduction(ingredientsUsed=items_list)
            
        except ValidationError:
            remainingQuantities = models.OutputIngredientDeduction.model_validate_json(responseText)

        logger.info("Deduction calculation complete")
        return remainingQuantities
    except Exception as e:
        logger.error(f"Deduction LLM Failed: {str(e)}")
        raise e

def computeCurrentWindowForNewUser(preferenceObject: models.UserPreferences):
    now = datetime.utcnow()
    boundaries = [preferenceObject.breakfast, preferenceObject.lunch,
                  preferenceObject.eveningSnack, preferenceObject.dinner]
    offset = timedelta(minutes=preferenceObject.loadBalancerOffset)
    adjustedBoundaries = []
    for boundary in boundaries:
        datetimeBoundary = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=boundary.hour,
            minute=boundary.minute,
            second=0,
            tzinfo=None
        )        
        datetimeBoundary -= offset
        adjustedBoundaries.append(datetimeBoundary)

    currentMealWindowKey = 3  # fallback = dinner
    for i in range(len(boundaries)):
        start = adjustedBoundaries[i] 
        end = adjustedBoundaries[(i + 1) % 4]

        if end < start:
            end += timedelta(days=1)
            if now < start:
                start -= timedelta(days=1)
                end -= timedelta(days=1)

        if start <= now < end:
            currentMealWindowKey = i 
            break 

    
    logger.info("Computed current window", extra={"window_key": currentMealWindowKey})
    return currentMealWindowKey

def computeNextMealGenerationTime(userPreferences: models.UserPreferences, currentNextMealWindowKey: int):
    nextMealWindowKey = (currentNextMealWindowKey + 1) % 4
    nextMealWindowName = crud.MEAL_WINDOWS[nextMealWindowKey]

    nextMealTime = getattr(userPreferences, nextMealWindowName)
    userOffset = userPreferences.loadBalancerOffset

    now = datetime.utcnow()

    nextRunDatetimeObject = datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=nextMealTime.hour,
        minute=nextMealTime.minute,
        second=0,
        tzinfo=None
    )

    nextRunDatetimeObject = nextRunDatetimeObject - timedelta(minutes=userOffset)
    if nextRunDatetimeObject <= now:
        if nextMealWindowKey == 0:
            nextRunDatetimeObject = nextRunDatetimeObject + timedelta(days=1)
        else:
            logger.info("Next trigger passed, skipping to following meal", extra={"skipped_window": nextMealWindowKey})
            computeNextMealGenerationTime(userPreferences, nextMealWindowKey)

    logger.info("Next meal generation scheduled", extra={
        "next_run": nextRunDatetimeObject.isoformat(),
        "window_key": nextMealWindowKey
    })
    return nextRunDatetimeObject, nextMealWindowKey

def computeCurrentWindowEndTime(userPreferences: models.UserPreferences, nextMealWindowKey: int):
    # TODO need to have a default for dinner
    # Currently dinner's end time will only be calculated when it's time for breakfast generation for next day
    # Ideally want to delete dinner around midnight too
    nextMealWindowName = crud.MEAL_WINDOWS[nextMealWindowKey]
    nextWindowStartTime = getattr(userPreferences, nextMealWindowName)

    now = datetime.utcnow()
    currentWindowEndTime = datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=nextWindowStartTime.hour,
        minute=nextWindowStartTime.minute,
        second=0,
        tzinfo=None
    )

    return currentWindowEndTime