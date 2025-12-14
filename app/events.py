import asyncio
import json
import os
import redis.asyncio as aioredis
from app.websocketManager import manager

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_URL=f"redis://{REDIS_HOST}:6379/0"

async def redisListener():
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe("mealGenerated")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
            
        data = json.loads(message["data"])
        userId  = data["userId"]
    
        manager.sendToUser(userId)

