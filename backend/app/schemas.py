import math
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

MAX_QUANTITY = 1_000_000_000

class OrderRequest(BaseModel):
    facility: str = Field(min_length=1)
    product: str = Field(min_length=1)
    quantity: float = Field(gt=0, le=MAX_QUANTITY)
    spec: Literal["ALL", "EUDR"] = "ALL"
    buyer: Optional[str] = None
    target_total_days: Optional[int] = Field(default=None, ge=1, le=365)
    enable_tolling: bool = False
    recommendation_metric: Literal["VOLUME", "LOWEST_PCF"] = "VOLUME"

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("quantity must be finite")
        return value


class TraceRequest(BaseModel):
    orders: List[OrderRequest] = Field(min_length=1, max_length=50)


class SLOCConfigItem(BaseModel):
    plant: str = Field(min_length=1)
    storagelocation: str = Field(min_length=1)
    material: str = Field(min_length=1)
    eudr: bool = False
    eudr_valid_from: Optional[str] = None
    eudr_valid_to: Optional[str] = None


class SLOCConfigRequest(BaseModel):
    items: List[SLOCConfigItem] = Field(min_length=1, max_length=5000)