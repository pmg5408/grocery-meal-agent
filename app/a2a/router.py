from datetime import datetime

from fastapi import APIRouter, Depends, Header, status
from sqlmodel import Session

import app.models as models
from app.a2a import service
from app.a2a.auth import verify_a2a_agent
from app.a2a.schemas import (
    A2ATaskCreateRequest,
    A2ATaskCreateResponse,
    A2ATaskStatus,
    A2ATaskStatusResponse,
)
from app.database import getFastApiSession

router = APIRouter(prefix="/a2a", tags=["a2a"])


@router.get("/health")
def a2a_health() -> dict:
    return {
        "status": "ok",
        "module": "a2a",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/v1/tasks", response_model=A2ATaskCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_task_endpoint(
    task_request: A2ATaskCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: Session = Depends(getFastApiSession),
    caller_agent: models.TrustedAgent = Depends(verify_a2a_agent),
):
    task = service.submit_task(
        session=session,
        caller_agent=caller_agent,
        task_request=task_request,
        idempotency_key=idempotency_key,
    )
    return A2ATaskCreateResponse(
        taskId=task.taskId,
        status=A2ATaskStatus(task.status),
        receivedAt=task.createdAt,
    )


@router.get("/v1/tasks/{task_id}", response_model=A2ATaskStatusResponse)
def get_task_status_endpoint(
    task_id: str,
    session: Session = Depends(getFastApiSession),
    caller_agent: models.TrustedAgent = Depends(verify_a2a_agent),
):
    return service.get_task_status(
        session=session,
        caller_agent=caller_agent,
        task_id=task_id,
    )
