from worker.celery import celery
from datetime import datetime
from app.database import getCelerySession
from app import crud, services, models
from app.a2a import handlers as a2a_handlers
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
def generateDailyMealsBatch():
    """
    Runs every 15 minutes. Identifies the current 15-min bucket (0-19) 
    between 00:00 and 05:00 UTC and triggers batch generation for assigned users.
    """
    now = datetime.utcnow()
    # Only run between 00:00 and 05:00 UTC
    if now.hour >= 5:
        logger.info("Outside of batch generation window (00:00 - 05:00 UTC). Skipping.")
        return

    # 5 hours * 4 buckets per hour = 20 buckets total
    current_bucket = (now.hour * 4) + (now.minute // 15)
    logger.info(f"Starting daily batch meal generation for bucket {current_bucket}")

    try:
        with next(getCelerySession()) as session:
            users_in_bucket = crud.getUsersByBatchBucket(session, current_bucket)
            if not users_in_bucket:
                logger.info(f"No users found for bucket {current_bucket}")
                return

            for pref in users_in_bucket:
                generateAllMealsForUser.delay(pref.userId)
            
            logger.info(f"Queued batch generation for {len(users_in_bucket)} users in bucket {current_bucket}")
    except Exception as e:
        logger.error(f"Batch generation task failed: {str(e)}")

@celery.task(bind=True, max_retries=3)
def generateAllMealsForUser(self, userId):
    logger.info(f"Generating all meals for the day for user {userId}")
    try:
        with next(getCelerySession()) as session:
            batch_suggestions = services.getBatchRecipeSuggestions(session, userId)
            
            for window_name in MEAL_WINDOWS.values():
                suggestions = getattr(batch_suggestions, window_name)
                if suggestions:
                    crud.storeProactiveMealSuggestions(
                        session=session,
                        userId=userId,
                        mealWindow=window_name,
                        suggestionsJson=suggestions.model_dump_json()
                    )
            
            logger.info(f"Successfully pre-generated all meals for user {userId}")
    except Exception as e:
        logger.error(f"Failed to generate batch meals for user {userId}: {str(e)}")
        raise self.retry(exc=e)

@celery.task
def scanMealTriggersAndQueueUsers():
    logger.info("Scheduler tick: Scanning for due meal triggers")
    
    try:
        with next(getCelerySession()) as session:
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
                    mealWindow = MEAL_WINDOWS.get(toBeGeneratedWindowKey, "dinner")

                    logger.info("Processing trigger for user", extra={"user_id": userId, "window_key": toBeGeneratedWindowKey})

                    userPreferences = crud.getUserPreferences(session, userId)

                    currentWindowEndTime = services.computeCurrentWindowEndTime(userPreferences, toBeGeneratedWindowKey)
                    crud.updateCurrentWindowEndTime(user, currentWindowEndTime)

                    # Check if meal was already pre-generated
                    existing_meal = crud.getUnconsumedMealByWindow(session, userId, mealWindow)
                    if existing_meal:
                        logger.info(f"Found pre-generated meal for user {userId}, window {mealWindow}. Pushing...")

                        # Mark the new meal as active (this creates the overlap period)
                        crud.markMealAsActive(session, existing_meal.id)

                        # Update current active meal in trigger
                        crud.markNewMealAsCurrentMeal(session, userId, existing_meal.id)

                        message = json.dumps({"userId": userId})
                        redisClient.publish("mealGenerated", message)
                    else:
                        logger.info(f"No pre-generated meal for user {userId}, window {mealWindow}. Falling back to JIT generation.")
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
        with next(getCelerySession()) as session:

            mealWindow = MEAL_WINDOWS.get(mealWindowKey, "dinner")

            recipes: models.RecipeSuggestions = services.getRecipeSuggestions(session, userId, mealWindow=mealWindow)

            suggestionsJson = recipes.model_dump_json()

            storedProactiveMealSuggestion = crud.storeProactiveMealSuggestions(
                session=session,
                userId=userId,
                mealWindow=mealWindow,
                suggestionsJson=suggestionsJson
            )

            # Mark the newly generated meal as active
            crud.markMealAsActive(session, storedProactiveMealSuggestion.id)

            crud.markNewMealAsCurrentMeal(session, userId, storedProactiveMealSuggestion.id)

            message = json.dumps({"userId": userId})
            redisClient.publish("mealGenerated", message)

            logger.info("Meal generation successful & published to Redis", extra={"user_id": userId, "channel": "mealGenerated"})

            return {"status": "success", "userId": userId, "mealWindow": mealWindow}
            
    except Exception as e:
        logger.error(f"Meal generation task failed: {str(e)}", extra={"user_id": userId})
        raise e


@celery.task
def executeAgentTask(taskId: str):
    """
    Execute an inbound delegated A2A task.
    """
    logger.info("Starting A2A task execution", extra={"task_id": taskId})

    try:
        with next(getCelerySession()) as session:
            task = crud.getAgentTaskByTaskId(session, taskId)
            if not task:
                logger.error("A2A task not found for execution", extra={"task_id": taskId})
                return {"status": "missing", "taskId": taskId}

            if task.status in {"completed", "failed", "cancelled"}:
                logger.info("A2A task already terminal; skipping execution", extra={"task_id": taskId, "status": task.status})
                return {"status": "skipped", "taskId": taskId, "taskStatus": task.status}

            crud.markAgentTaskRunning(session, task)

            input_payload = json.loads(task.inputJson) if task.inputJson else {}
            output_payload = a2a_handlers.execute_task_type(task.taskType, input_payload, session)
            crud.completeAgentTask(session, task, output_payload)

            logger.info("A2A task executed successfully", extra={"task_id": taskId, "task_type": task.taskType})
            return {"status": "success", "taskId": taskId}

    except Exception as e:
        logger.error("A2A task execution failed", extra={"task_id": taskId, "error": str(e)})
        try:
            with next(getCelerySession()) as session:
                task = crud.getAgentTaskByTaskId(session, taskId)
                if task and task.status not in {"completed", "cancelled"}:
                    crud.failAgentTask(
                        session,
                        task,
                        {
                            "code": "TASK_EXECUTION_ERROR",
                            "message": str(e),
                            "retryable": False,
                        },
                    )
        except Exception as inner_error:
            logger.error("Failed to persist A2A task failure state", extra={"task_id": taskId, "error": str(inner_error)})

        return {"status": "failed", "taskId": taskId, "error": str(e)}
