"""Task-type handlers for delegated A2A jobs."""

from typing import Any, Callable
from sqlmodel import Session

HandlerFn = Callable[[dict, Session], dict]

TASK_HANDLERS: dict[str, HandlerFn] = {}


def register_task_handler(task_type: str, handler: HandlerFn) -> None:
    TASK_HANDLERS[task_type] = handler


def execute_task_type(task_type: str, task_input: dict, session: Session) -> dict[str, Any]:
    """
    Execute a task type using the registered handler.
    """
    handler = TASK_HANDLERS.get(task_type)
    if not handler:
        raise ValueError(f"No A2A handler implemented for taskType={task_type}")

    result = handler(task_input, session)
    if result is None:
        return {}
    if not isinstance(result, dict):
        return {"result": result}
    return result
