from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis import Redis
from app.database import getRedisClient
from app.logger import get_logger
from typing import Optional
import jwt
import os

logger = get_logger("rate_limiter")
auth_scheme = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "REPLACE_WITH_A_REAL_SECRET") 
ALGORITHM = "HS256"

# Rate limit constants
DAILY_LIMIT = 8
HOURLY_LIMIT = 2

def get_rate_limit_key(user_id: int, time_window: str) -> str:
    """Generate Redis key for rate limiting based on user and time window."""
    return f"rate_limit:{time_window}:{user_id}"

async def check_rate_limit(request: Request, call_next):
    """
    Middleware to check rate limits for manual meal generation endpoint.
    
    Implements sliding window rate limiting using Redis TTL.
    - Daily limit: 8 requests per 24 hours
    - Hourly limit: 2 requests per hour
    """
    if request.url.path != "/pantry/suggestMeal":
        return await call_next(request)
    
    # Extract JWT token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Rate limit check failed: No valid Authorization header")
        return await call_next(request)
    
    token = auth_header.split(" ")[1]
    
    # Decode JWT to get user ID
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = decoded["userId"]
    except jwt.ExpiredSignatureError:
        logger.warning("Rate limit check failed: Expired token")
        return await call_next(request)
    except jwt.InvalidTokenError:
        logger.warning("Rate limit check failed: Invalid token")
        return await call_next(request)
    
    try:
        redis_client = getRedisClient()
        
        # Check daily limit
        daily_key = get_rate_limit_key(user_id, "daily")
        daily_count = redis_client.get(daily_key)
        if daily_count and int(daily_count) >= DAILY_LIMIT:
            logger.warning(f"Daily rate limit exceeded for user {user_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Daily rate limit exceeded",
                    "message": f"Maximum {DAILY_LIMIT} manual meal requests allowed per day",
                    "retry_after": 86400 
                }
            )
        
        # Check hourly limit  
        hourly_key = get_rate_limit_key(user_id, "hourly")
        hourly_count = redis_client.get(hourly_key)
        if hourly_count and int(hourly_count) >= HOURLY_LIMIT:
            logger.warning(f"Hourly rate limit exceeded for user {user_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Hourly rate limit exceeded", 
                    "message": f"Maximum {HOURLY_LIMIT} manual meal requests allowed per hour",
                    "retry_after": 3600
                }
            )
        
        redis_client.incr(daily_key)
        redis_client.expire(daily_key, 86400)
        
        redis_client.incr(hourly_key)
        redis_client.expire(hourly_key, 3600)

        logger.info(f"Rate limit check passed for user {user_id}")

        response = await call_next(request)

        response.headers["X-RateLimit-Daily-Limit"] = str(DAILY_LIMIT)
        response.headers["X-RateLimit-Hourly-Limit"] = str(HOURLY_LIMIT)
        response.headers["X-RateLimit-Daily-Remaining"] = str(DAILY_LIMIT - (int(daily_count) + 1 if daily_count else 1))
        response.headers["X-RateLimit-Hourly-Remaining"] = str(HOURLY_LIMIT - (int(hourly_count) + 1 if hourly_count else 1))
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting error for user {user_id}: {str(e)}")
        return await call_next(request)