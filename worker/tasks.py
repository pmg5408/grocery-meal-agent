from worker.celery import celery
from datetime import datetime
from app.database import getSession
from app import crud, services, models
import redis
import json

redisClient = redis.Redis(host="localhost", port=6379, db=0)

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
    
        dueUsers = crud.getDueUsersByMealTriggers(session, now)

        for user in dueUsers:
            userId = user.userId
            mealWindowKey = user.mealWindow

            getMealsFromLlm.delay(userId, mealWindowKey)

            nextRun, nextMealWindowKey = crud.computeNextRunForUser(session, userId, mealWindowKey)

            crud.updateNextRunForUSer(user, nextRun, nextMealWindowKey)
        
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
            "mealUpdates",
            json.dumps({
                "userId": userId,
                "mealWindow": mealWindow,
            })
        )


        return {"status": "success", "userId": userId, "mealWindow": mealWindow}

