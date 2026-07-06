"""
Pydantic schemas for the Drill-Down Intelligence endpoints.
Strict validation prevents 'str has no attribute copy' class of errors.
"""
from pydantic import BaseModel, Field


class ProductContextRequest(BaseModel):
    """POST /api/drilldown/product-context"""
    buyer_id:     str = Field(min_length=1, description="Buyer ID from GET /api/drilldown/buyers")
    product_code: str = Field(min_length=2, description="Product code e.g. CPO, RBDPO")


class ResolutionRequest(BaseModel):
    """POST /api/drilldown/resolve-gap"""
    buyer_id:     str = Field(min_length=1)
    product_code: str = Field(min_length=2)
