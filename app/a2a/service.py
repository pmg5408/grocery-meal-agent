import json
import uuid
from typing import Optional, Type

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlmodel import Session

import app.crud as crud
import app.models as models
from app.a2a.schemas import (
    A2AError,
    A2ATaskCreateRequest,
    A2ATaskStatus,
    A2ATaskStatusResponse,
    MealGetBatchedMealsInput,
)
from app.logger import get_logger

logger = get_logger("a2a_service")

TASK_INPUT_VALIDATORS: dict[str, Type[BaseModel]] = {
    "meal.get_batched_meals": MealGetBatchedMealsInput,
}


def _get_allowed_task_types(agent: models.TrustedAgent) -> list[str]:
    try:
        parsed = json.loads(agent.allowedTaskTypesJson or "[]")
        if not isinstance(parsed, list):
            return []
        return [str(task_type) for task_type in parsed]
    except Exception:
        return []


def _parse_json_object(value: Optional[str]) -> Optional[dict]:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    except Exception:
        return {"raw": value}


def _validate_input_for_task(task_type: str, raw_input: dict) -> dict:
    validator = TASK_INPUT_VALIDATORS.get(task_type)
    if not validator:
        return raw_input

    try:
        validated = validator.model_validate(raw_input)
        return validated.model_dump(exclude_none=True)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INVALID_TASK_INPUT",
                "taskType": task_type,
                "validation": exc.errors(),
            },
        )


def submit_task(
    session: Session,
    caller_agent: models.TrustedAgent,
    task_request: A2ATaskCreateRequest,
    idempotency_key: str,
) -> models.AgentTask:
    allowed_task_types = _get_allowed_task_types(caller_agent)
    if task_request.taskType not in allowed_task_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Task type '{task_request.taskType}' is not allowed for agent '{caller_agent.agentId}'",
        )
    validated_input = _validate_input_for_task(task_request.taskType, task_request.input)

    existing_task = crud.getAgentTaskByIdempotencyKey(session, caller_agent.agentId, idempotency_key)
    if existing_task:
        return existing_task

    new_task_id = str(uuid.uuid4())
    task = crud.createAgentTask(
        session=session,
        taskId=new_task_id,
        callerAgentId=caller_agent.agentId,
        taskType=task_request.taskType,
        inputPayload=validated_input,
        idempotencyKey=idempotency_key,
        correlationId=task_request.correlationId,
        callbackUrl=str(task_request.callbackUrl) if task_request.callbackUrl else None,
    )

    from worker.tasks import executeAgentTask

    executeAgentTask.delay(task.taskId)

    logger.info(
        "A2A task submitted",
        extra={"task_id": task.taskId, "caller_agent_id": caller_agent.agentId, "task_type": task.taskType},
    )
    return task


def get_task_status(
    session: Session,
    caller_agent: models.TrustedAgent,
    task_id: str,
) -> A2ATaskStatusResponse:
    task = crud.getAgentTaskByTaskId(session, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    if task.callerAgentId != caller_agent.agentId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent is not allowed to access this task",
        )

    task_status = A2ATaskStatus(task.status)
    parsed_error = _parse_json_object(task.errorJson)
    parsed_output = _parse_json_object(task.outputJson)

    error_obj = None
    if parsed_error:
        error_obj = A2AError(
            code=str(parsed_error.get("code", "TASK_ERROR")),
            message=str(parsed_error.get("message", "Task failed")),
            retryable=bool(parsed_error.get("retryable", False)),
            details=parsed_error.get("details"),
        )

    return A2ATaskStatusResponse(
        taskId=task.taskId,
        taskType=task.taskType,
        status=task_status,
        createdAt=task.createdAt,
        updatedAt=task.updatedAt,
        correlationId=task.correlationId,
        output=parsed_output,
        error=error_obj,
    )
