import asyncio
import json
import os
import redis.asyncio as redis
from app.websocketManager import manager
from app.logger import get_logger

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_URL=f"redis://{REDIS_HOST}:6379/0"

logger = get_logger("events")

async def redisListener():
    logger.info("Connecting to Redis", extra={"url": REDIS_URL})
    try: 

        r = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("mealGenerated")

        logger.info("Successfully subscribed to mealGenerated channel")

        async for message in pubsub.listen():
            if message["type"] == "message":
                print(f"[REDIS-LISTENER] Received message: {message['data']}")
                try:
                    data = json.loads(message["data"])
                    userId = data["userId"]

                    logger.info("Meal Ready Event Received", extra={"user_id": userId})
                    await manager.sendToUser(userId)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
    
    except Exception as e:
        logger.critical(f"Redis Connection Failed: {str(e)}")

