# schemas/common.py
"""
Common Pydantic schemas used across the API
"""
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

