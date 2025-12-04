import asyncio
import json
import redis.asyncio as aioredis
from app.websocketManager import manager

REDIS_URL="redis://localhost:6379/0"

async def redisListener():
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe("mealUpdates")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
            
        data = json.loads(message["data"])
        userId  = data["userId"]
    
        manager.sendToUser(userId, data)

