from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class BaseDiscrepancy(BaseModel):
    type: str
    details: str
    detected_by: Literal["document_intelligence", "matching", "validation"]
    detected_at: datetime = Field(default_factory=lambda: datetime.now())
