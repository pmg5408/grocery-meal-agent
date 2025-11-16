import app.crud as crud
import app.models as models
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

JSON_GENERATION_CONFIG = GenerationConfig(
    response_mime_type='application/json'
)

LLM_MODEL = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    generation_config=JSON_GENERATION_CONFIG
)

def getPrioritizedItems(combinedPantryItems):
    userPrioritizedItems = combinedPantryItems['priorityItems']
    allItems = combinedPantryItems['allItems']

    highPriority = []
    normalPriority = []

    for localItem in allItems:
        itemName = localItem.item.itemName
        brand = localItem.item.brand
        shelfLife = localItem.item.avgShelfLife
        daysOwned = (datetime.utcnow() - localItem.purchaseDate).days

        if shelfLife - daysOwned < 2:
            highPriority.append(f"{brand} {itemName} with quantity {localItem.quantity}")
        else:
            normalPriority.append(f"{brand} {itemName} with quantity {localItem.quantity}")
    
    for userItem in userPrioritizedItems:
        itemName = userItem.item.itemName
        brand = userItem.item.brand
        highPriority.append(f"{brand} {itemName} with quantity {userItem.quantity}")
    
    return {
        "normalPriority": normalPriority,
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
    prioritizedItems = getPrioritizedItems(combinedPantryItems)

    prioritizedItems['normalPriority'] = ','.join(prioritizedItems['normalPriority'])
    prioritizedItems['highPriority'] = ','.join(prioritizedItems['highPriority'])
    
    meal = getMealBasedOnTime()

    return prioritizedItems, meal

def getAndParseModelResponse(prompt):

    response = LLM_MODEL.generate_content(prompt)
    suggestions = models.RecipeSuggestions.model_validate_json(response.text)
    return suggestions

def buildPrompt(prioritizedItems, meal):
    outputFormat = models.RecipeSuggestions.model_json_schema()
    prompt = f"""
                <task>
                    You are a helpful meal planner who plans meals based on the given ingredients.
                    Your task is to give recipes for 3 meals for a user given the items in their pantry.
                </task>
                <instructions>
                    - Provided below are 2 lists of items, high_priority_ingredients and normal_priority_ingredients.
                    - The elements in the list are names of the ingredients and the quantity.  
                    - Ingredients part of high_priority_ingredients are ingredients that are close to expiry and hence need to be used before they go bad or they are ingredients that the user has specifically asked to be used in the recipe.
                    - Ingredients in normal_priority_ingredients are ingredients that are present in the user's pantry but don't necessarily need to be used.
                    - Assume the user has non-perishable generic ingredients like oil, salt, pepper, etc, that are found in most households
                    - I have also provided the meal of the day I want you to suggest recipes for.
                    - Suggest 3 recipes usign the ingredients in the user's pantry.
                    - Each recipe should contain the description, ingredients needed with their quantities and units and the steps to make the meal.
                    - Your output MUST be a single valid JSON object that matches this schema: {outputFormat}
                    - Do not include any other text, explanations, or markdown backticks. Only the JSON object.
                </instructions>

                <high_priority_ingredients>
                {prioritizedItems["highPriority"]}
                </high_priority_ingredients>

                <nomral_priority_ingredients>
                {prioritizedItems["normalPriority"]}
                </normal_priority_ingredients>

                <meal>
                {meal}
                </meal>
            """
    return prompt

def getRecipeSuggestions(session, userId, userSuggestions):

    prioritizedItems, meal = prepareDataForMealSuggestionPrompt(session, userId, userSuggestions)

    prompt = buildPrompt(prioritizedItems, meal)

    recipes = getAndParseModelResponse(prompt)

    return recipes