import hashlib
from datetime import datetime
from secrets import compare_digest

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

import app.crud as crud
import app.models as models
from app.database import getFastApiSession, getRedisClient
from app.logger import get_logger

logger = get_logger("a2a_auth")

AGENT_ID_HEADER = "X-Agent-Id"
AGENT_KEY_HEADER = "X-Agent-Key"


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _enforce_agent_rate_limit(agent: models.TrustedAgent) -> None:
    """
    Per-agent fixed-window limiter.
    """
    try:
        redis_client = getRedisClient()
        now = datetime.utcnow()
        window_key = now.strftime("%Y%m%d%H%M")
        key = f"a2a:rate:{agent.agentId}:{window_key}"

        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, 60)

        if current > agent.rateLimitPerMinute:
            logger.warning(
                "A2A rate limit exceeded",
                extra={"agent_id": agent.agentId, "limit": agent.rateLimitPerMinute, "count": current},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "A2A rate limit exceeded",
                    "message": f"Maximum {agent.rateLimitPerMinute} A2A requests per minute",
                    "retry_after": 60,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to evaluate A2A rate limit", extra={"agent_id": agent.agentId, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A2A rate limiting unavailable",
        )


def verify_a2a_agent(
    request: Request,
    session: Session = Depends(getFastApiSession),
) -> models.TrustedAgent:
    """
    Authenticate and authorize caller agent for /a2a/* endpoints.
    """
    agent_id = request.headers.get(AGENT_ID_HEADER)
    agent_key = request.headers.get(AGENT_KEY_HEADER)

    if not agent_id or not agent_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required headers: {AGENT_ID_HEADER}, {AGENT_KEY_HEADER}",
        )

    trusted_agent = crud.getTrustedAgentByAgentId(session, agent_id)
    if not trusted_agent or not trusted_agent.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown or inactive agent",
        )

    if trusted_agent.authMethod != "api_key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported auth method for agent: {trusted_agent.authMethod}",
        )

    if not trusted_agent.apiKeyHash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trusted agent has no configured API key hash",
        )

    hashed_api_key = _hash_api_key(agent_key)
    if not compare_digest(hashed_api_key, trusted_agent.apiKeyHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials",
        )

    _enforce_agent_rate_limit(trusted_agent)
    return trusted_agent
