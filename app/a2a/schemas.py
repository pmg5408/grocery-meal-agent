from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
import app.models as app_models


class A2ATaskStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class A2AError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable error summary")
    retryable: bool = Field(default=False)
    details: Optional[Dict[str, Any]] = Field(default=None)


class A2ATaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taskType: str = Field(description="Delegated capability identifier")
    input: Dict[str, Any] = Field(default_factory=dict, description="Task input payload")
    callbackUrl: Optional[HttpUrl] = Field(default=None)
    correlationId: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class A2ATaskCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taskId: str
    status: A2ATaskStatus
    receivedAt: datetime


class A2ATaskStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taskId: str
    taskType: str
    status: A2ATaskStatus
    createdAt: datetime
    updatedAt: datetime
    correlationId: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[A2AError] = None


class A2ATaskEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taskId: str
    status: A2ATaskStatus
    timestamp: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)


class MealTaskOutputStatus(str, Enum):
    OK = "ok"
    NO_MEALS_AVAILABLE = "no_meals_available"


class MealTaskScope(str, Enum):
    ALL_DAY = "all_day"
    ACTIVE_ONLY = "active_only"


class MealGetBatchedMealsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userId: int = Field(gt=0, description="Target user id in pantry system")
    activeOnly: bool = Field(default=False)


class MealWindowsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    breakfast: Optional[app_models.RecipeSuggestions] = None
    lunch: Optional[app_models.RecipeSuggestions] = None
    eveningSnack: Optional[app_models.RecipeSuggestions] = None
    dinner: Optional[app_models.RecipeSuggestions] = None


class MealGetBatchedMealsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MealTaskOutputStatus
    scope: MealTaskScope
    generatedOnDemand: bool
    userId: int
    meals: MealWindowsPayload
