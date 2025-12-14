from worker.celery import celery
from datetime import datetime
from app.database import getSession
from app import crud, services, models
from typing import List
import redis
import json
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
redisClient = redis.Redis(host=REDIS_HOST, port=6379, db=0)

MEAL_WINDOWS = {
    0: 'breakfast',
    1: 'lunch',
    2: 'eveningSnack',
    3: 'dinner'
}

@celery.task
def scanMealTriggersAndQueueUsers():
    with next(getSession()) as session:
        now = datetime.utcnow()
        crud.cleanOldMeals(session, now)
        dueUsers: List[models.UserMealTrigger] = crud.getDueUsersByMealTriggers(session, now)

        for user in dueUsers:
            userId = user.userId
            toBeGeneratedWindowKey = user.nextMealWindowToCompute
            userPreferences = crud.getUserPreferences(session, userId)

            currentWindowEndTime = services.computeCurrentWindowEndTime(userPreferences, toBeGeneratedWindowKey)
            crud.updateCurrentWindowEndTime(user, currentWindowEndTime)

            getMealsFromLlm.delay(userId, toBeGeneratedWindowKey)
            justGeneratedWindowKey = toBeGeneratedWindowKey

            
            nextRun, nextToBeGeneratedWindowKey = services.computeNextMealGenerationTime(userPreferences, justGeneratedWindowKey)
            # computeNextRunForUser and updating interact with different tables, hence are separate crud calls
            crud.updateNextRunForUser(user, nextRun, nextToBeGeneratedWindowKey)
            
        session.commit()
        return len(dueUsers)
    
@celery.task
def getMealsFromLlm(userId, mealWindowKey):

    with next(getSession()) as session:

        mealWindow = MEAL_WINDOWS[mealWindowKey]
        recipes: models.RecipeSuggestions = services.getRecipeSuggestions(session, userId, mealWindow=mealWindow)

        # Store in DB
        suggestionsJson = recipes.model_dump_json()

        mealSuggestionForUser = crud.storeProactiveMealSuggestions(
            session=session,
            userId=userId,
            mealWindow=mealWindow,
            suggestionsJson=suggestionsJson
        )

        redisClient.publish(
            "mealGenerated",
            json.dumps({
                "userId": userId,
            })
        )


        return {"status": "success", "userId": userId, "mealWindow": mealWindow}

