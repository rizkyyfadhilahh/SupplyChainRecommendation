"""
Pydantic schemas for domain config API endpoints.

Each class validates one section of the domain config that can be
updated via PUT /api/config.  Using strict schemas instead of
Dict[str, Any] ensures:
  - Unknown keys are rejected with a clear 422 error
  - Value types are validated (e.g. ratio must be a positive float)
  - Downstream code can trust the shape of what it receives
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ConversionMapConfig(BaseModel):
    """product -> conversion ratio (must be > 0)."""
    conversion_map: Dict[str, float] = Field(
        description="Map of product code to conversion ratio. All ratios must be positive."
    )

    @field_validator("conversion_map")
    @classmethod
    def ratios_must_be_positive(cls, v: Dict[str, float]) -> Dict[str, float]:
        bad = [k for k, ratio in v.items() if ratio <= 0]
        if bad:
            raise ValueError(f"Conversion ratios must be > 0. Invalid products: {bad}")
        return v


class ProcessMapConfig(BaseModel):
    """product -> raw_material (upstream product code)."""
    process_map: Dict[str, str] = Field(
        description="Map of product code to its upstream raw material product code."
    )


class FacilityGroupsConfig(BaseModel):
    """refinery_name -> list of plant IDs that belong to it."""
    facility_groups: Dict[str, List[str]] = Field(
        description="Map of refinery name to list of plant IDs."
    )

    @field_validator("facility_groups")
    @classmethod
    def plant_lists_must_not_be_empty(cls, v: Dict[str, List[str]]) -> Dict[str, List[str]]:
        empty = [ref for ref, plants in v.items() if not plants]
        if empty:
            raise ValueError(f"Facility groups must have at least one plant. Empty groups: {empty}")
        return v


class BuyerBlacklistConfig(BaseModel):
    """buyer_name -> list of blacklisted plant IDs."""
    buyer_blacklist: Dict[str, List[str]] = Field(
        description="Map of buyer name to list of plant IDs they cannot source from."
    )


class ForecastThresholdsConfig(BaseModel):
    """Forecast threshold parameters."""
    FORECAST_THRESHOLDS: Dict[str, float] = Field(
        description="Forecast threshold key-value pairs (e.g. MIN_TXN_FOR_EXACT, FORECAST_TARGET_DAYS)."
    )


class GeneralConfigUpdate(BaseModel):
    """
    Top-level config update payload.

    All sections are optional — only the sections provided will be updated.
    Unknown top-level keys are forbidden to prevent silent misconfigurations.
    """
    model_config = {"extra": "forbid"}

    conversion_map: Optional[Dict[str, float]] = None
    process_map: Optional[Dict[str, str]] = None
    facility_groups: Optional[Dict[str, List[str]]] = None
    buyer_blacklist: Optional[Dict[str, List[str]]] = None
    REFINED_PRODUCTS: Optional[List[str]] = None
    DIRECT_REFINERY_PRODUCTS: Optional[List[str]] = None
    DIRECT_PRODUCT_EMPTY_FALLBACK: Optional[Dict[str, str]] = None
    VENDOR_PARTNER_PCA_PRODUCTS: Optional[List[str]] = None
    REFINERIES_WITH_KCP: Optional[List[str]] = None
    PASS_THROUGH_TYPES: Optional[List[str]] = None
    DEFAULT_LEAD_DAYS_BY_TYPE: Optional[Dict[str, int]] = None
    DEFAULT_THROUGHPUT_TPD_BY_PRODUCT: Optional[Dict[str, float]] = None
    FORECAST_THRESHOLDS: Optional[Dict[str, float]] = None

    @field_validator("conversion_map")
    @classmethod
    def conversion_ratios_positive(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is None:
            return v
        bad = [k for k, ratio in v.items() if ratio <= 0]
        if bad:
            raise ValueError(f"Conversion ratios must be > 0. Invalid: {bad}")
        return v

    @field_validator("facility_groups")
    @classmethod
    def facility_groups_not_empty(cls, v: Optional[Dict[str, List[str]]]) -> Optional[Dict[str, List[str]]]:
        if v is None:
            return v
        empty = [ref for ref, plants in v.items() if not plants]
        if empty:
            raise ValueError(f"Facility groups must have at least one plant. Empty: {empty}")
        return v
