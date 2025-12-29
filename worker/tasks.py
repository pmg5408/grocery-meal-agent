from worker.celery import celery
from datetime import datetime
from app.database import getSession
from app import crud, services, models
from typing import List
import redis
import json
import os
from app.logger import get_logger

logger = get_logger("worker")

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
    logger.info("Scheduler tick: Scanning for due meal triggers")
    
    try:
        with next(getSession()) as session:
            now = datetime.utcnow()
            cleanedUsers = crud.cleanOldMeals(session, now)

            for uid in cleanedUsers:
                    redisClient.publish("mealGenerated", json.dumps({"userId": uid}))
                    logger.info("Notified user of meal cleanup", extra={"user_id": uid})

            dueUsers: List[models.UserMealTrigger] = crud.getDueUsersByMealTriggers(session, now)
            
            if not dueUsers:
                logger.info("No users due for meals at this time.")
                session.commit()
                return 0

            logger.info(f"Found {len(dueUsers)} users due for meal generation.")
            
            success_count = 0
            for user in dueUsers:
                try:
                    userId = user.userId
                    toBeGeneratedWindowKey = user.nextMealWindowToCompute

                    logger.info("Processing trigger for user", extra={"user_id": userId, "window_key": toBeGeneratedWindowKey})

                    userPreferences = crud.getUserPreferences(session, userId)

                    currentWindowEndTime = services.computeCurrentWindowEndTime(userPreferences, toBeGeneratedWindowKey)
                    crud.updateCurrentWindowEndTime(user, currentWindowEndTime)

                    getMealsFromLlm.delay(userId, toBeGeneratedWindowKey)
                    
                    justGeneratedWindowKey = toBeGeneratedWindowKey
                    nextRun, nextToBeGeneratedWindowKey = services.computeNextMealGenerationTime(userPreferences, justGeneratedWindowKey)

                    crud.updateNextRunForUser(user, nextRun, nextToBeGeneratedWindowKey)
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process trigger for User {user.userId}: {str(e)}")
                    continue
            
            session.commit()
            logger.info(f"Batch complete. Successfully scheduled {success_count}/{len(dueUsers)} users.")
            return success_count
            
    except Exception as e:
        logger.critical(f"Scheduler failed: {str(e)}")
        raise e
    
@celery.task(bind=True, max_retries=3)
def getMealsFromLlm(self, userId, mealWindowKey):
    logger.info("Starting LLM Meal Generation Task", extra={"user_id": userId, "window_key": mealWindowKey})

    try:
        with next(getSession()) as session:

            mealWindow = MEAL_WINDOWS.get(mealWindowKey, "dinner")

            recipes: models.RecipeSuggestions = services.getRecipeSuggestions(session, userId, mealWindow=mealWindow)

            suggestionsJson = recipes.model_dump_json()

            storedProactiveMealSuggestion = crud.storeProactiveMealSuggestions(
                session=session,
                userId=userId,
                mealWindow=mealWindow,
                suggestionsJson=suggestionsJson
            )

            crud.markNewMealAsCurrentMeal(session, userId, storedProactiveMealSuggestion.id)

            message = json.dumps({"userId": userId})
            redisClient.publish("mealGenerated", message)

            logger.info("Meal generation successful & published to Redis", extra={"user_id": userId, "channel": "mealGenerated"})

            return {"status": "success", "userId": userId, "mealWindow": mealWindow}
            
    except Exception as e:
        logger.error(f"Meal generation task failed: {str(e)}", extra={"user_id": userId})
        raise e

