"""
Pydantic schemas for Recipe and Production APIs.
"""

from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


# ============================================================================
# Recipe Schemas
# ============================================================================


class RecipeItemCreate(BaseModel):
    """One raw item in a recipe: quantity required per 1 unit of final product."""

    raw_item_id: str = Field(..., min_length=1, max_length=10, description="Raw item ID")
    quantity_per_unit: Decimal = Field(..., gt=0, description="Units of raw item per 1 final product")

    @field_validator("quantity_per_unit")
    @classmethod
    def quantity_reasonable(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity_per_unit must be positive")
        return v


class RecipeItemUpdate(RecipeItemCreate):
    """Same as create for update (replace list)."""

    pass


class RecipeCreate(BaseModel):
    """Create a recipe for a final product. Same raw item can appear multiple times (quantities aggregated in production)."""

    final_product_id: str = Field(..., min_length=1, max_length=10, description="Final product item ID")
    name: Optional[str] = Field(None, max_length=200)
    items: List[RecipeItemCreate] = Field(
        ...,
        min_length=1,
        description="Raw items and quantity per unit (at least one required). Same raw item can appear multiple times.",
    )


class RecipeUpdate(BaseModel):
    """Update recipe (name and/or items). Same raw item can appear multiple times (quantities aggregated)."""

    name: Optional[str] = Field(None, max_length=200)
    items: Optional[List[RecipeItemCreate]] = Field(
        None,
        min_length=1,
        description="Replace recipe items; if omitted, items are unchanged. Same raw item can appear multiple times.",
    )


def _decimal_two_places(v):
    """Format Decimal for JSON with 2 decimal places (e.g. 8.00, 1840.00)."""
    if v is None:
        return None
    d = Decimal(str(v))
    return str(d.quantize(Decimal("0.01")))


# Response: nested item with raw item details
# For 1 unit of final product: quantity_per_unit = how many of this raw item (e.g. 4 wheels per 1 car);
# amount_per_unit = quantity_per_unit × avg_price (e.g. 4 × 90 = 360).
class RecipeItemResponse(BaseModel):
    id: int
    raw_item_id: str
    raw_item_name: str
    quantity_per_unit: Decimal = Field(..., description="Units of this raw item needed per 1 unit of final product (e.g. 4 wheels per 1 car)")
    avg_price: Optional[Decimal] = Field(None, description="Average price per unit of this raw item")
    amount_per_unit: Decimal = Field(..., description="Cost of this raw item for 1 final product = quantity_per_unit × avg_price (e.g. 4 × 90 = 360)")
    total_quantity: int = Field(..., description="Current stock of this raw item")

    @field_serializer("quantity_per_unit", "avg_price", "amount_per_unit")
    def _serialize_decimal_two_places(self, v):
        return _decimal_two_places(v)

    class Config:
        from_attributes = True


class RecipeResponse(BaseModel):
    id: str
    final_product_id: str
    final_product_name: str
    name: Optional[str] = None
    items: List[RecipeItemResponse]
    total_cost_per_unit: Optional[Decimal] = Field(None, description="Total raw cost to build 1 unit of final product (sum of all amount_per_unit)")
    created_at: datetime
    updated_at: datetime

    @field_serializer("total_cost_per_unit")
    def _serialize_decimal_two_places(self, v):
        return _decimal_two_places(v)

    class Config:
        from_attributes = True


class RecipeListResponse(BaseModel):
    total: int
    recipes: List[RecipeResponse]


# ============================================================================
# Production Preview / Feasibility / Execute Schemas
# ============================================================================

SERIAL_PREFIX = "LEH-"


def normalize_serial_number(s: str) -> str:
    """Add LEH- prefix if user gave serial without it (e.g. 2201 -> LEH-2201)."""
    s = s.strip()
    if not s:
        return s
    if s.upper().startswith(SERIAL_PREFIX):
        return s
    return f"{SERIAL_PREFIX}{s}"


class ProductionPreviewQuery(BaseModel):
    """Query params for production preview."""

    final_product_id: str = Field(..., min_length=1)
    quantity: int = Field(1, ge=1, description="Number of units to produce")


class ProductionFeasibilityRequest(BaseModel):
    """Request body for feasibility check."""

    final_product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)


class ProductionExecuteRequest(BaseModel):
    """Request body for production execution. User provides serial numbers (one per unit)."""

    final_product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)
    serial_numbers: List[str] = Field(
        ...,
        min_length=1,
        description="One serial number per unit; LEH- prefix is added if omitted (e.g. 2201 -> LEH-2201)",
    )

    @field_validator("serial_numbers")
    @classmethod
    def validate_serial_numbers(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one serial number is required")
        seen = set()
        out = []
        for s in v:
            s = s.strip()
            if not s:
                raise ValueError("Serial number cannot be blank")
            s = normalize_serial_number(s)
            if s in seen:
                raise ValueError(f"Duplicate serial number: {s}")
            seen.add(s)
            out.append(s)
        return out

    @model_validator(mode="after")
    def quantity_matches_serials(self):
        if len(self.serial_numbers) != self.quantity:
            raise ValueError(
                f"quantity ({self.quantity}) must equal number of serial_numbers ({len(self.serial_numbers)})"
            )
        return self


# Response schemas
class RawItemRequirement(BaseModel):
    """One raw item requirement for production (preview/feasibility)."""

    raw_item_id: str
    raw_item_name: str
    quantity_required: Decimal  # total for N units
    quantity_per_unit: Decimal
    avg_price: Optional[Decimal] = None
    available_quantity: int
    sufficient: bool


class ProductionPreviewResponse(BaseModel):
    """Production preview: required raw items and total cost for N units."""

    final_product_id: str
    final_product_name: str
    quantity: int
    raw_requirements: List[RawItemRequirement]
    total_estimated_cost: Decimal


class InsufficientItem(BaseModel):
    """One raw item that is insufficient for requested quantity."""

    raw_item_id: str
    raw_item_name: str
    required_quantity: Decimal
    available_quantity: int
    shortfall: Decimal


class ProductionFeasibilityResponse(BaseModel):
    """Feasibility: can produce full quantity, or partial with details."""

    feasible: bool
    requested_quantity: int
    max_producible_quantity: int
    insufficient_items: List[InsufficientItem] = Field(default_factory=list)
    message: str


class ProductionExecuteResponse(BaseModel):
    """Response after successful production execution."""

    production_batch_id: str
    final_product_id: str
    final_product_name: str
    quantity_produced: int
    serial_numbers: List[str]
    created_at: datetime


# Production stages: draft and in_process (recipe editable), done (production complete, recipe not editable)
class ProductionStageEnum(str, Enum):
    DRAFT = "DRAFT"
    IN_PROCESS = "IN_PROCESS"
    DONE = "DONE"


class ProductionDraftCreate(BaseModel):
    """Create a production batch in DRAFT stage (no inventory moved). User can edit recipe in DRAFT and IN_PROCESS; not in DONE."""

    final_product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)
    serial_numbers: List[str] = Field(
        ...,
        min_length=1,
        description="One serial number per unit; LEH- prefix is added if omitted (e.g. 2201 -> LEH-2201)",
    )

    @field_validator("serial_numbers")
    @classmethod
    def validate_serial_numbers(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one serial number is required")
        seen = set()
        out = []
        for s in v:
            s = s.strip()
            if not s:
                raise ValueError("Serial number cannot be blank")
            s = normalize_serial_number(s)
            if s in seen:
                raise ValueError(f"Duplicate serial number: {s}")
            seen.add(s)
            out.append(s)
        return out

    @model_validator(mode="after")
    def quantity_matches_serials(self):
        if len(self.serial_numbers) != self.quantity:
            raise ValueError(
                f"quantity ({self.quantity}) must equal number of serial_numbers ({len(self.serial_numbers)})"
            )
        return self


class ProductionBatchResponse(BaseModel):
    """Single production batch (draft, in_process, or done)."""

    id: str
    final_product_id: str
    final_product_name: str
    quantity_produced: int
    stage: ProductionStageEnum
    serial_numbers: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductionBatchListResponse(BaseModel):
    """List of production batches with total count."""

    total: int
    batches: List[ProductionBatchResponse]


# ============================================================================
# Production Batch Detail Schemas (with recipe snapshot)
# ============================================================================


class ProductionBatchRecipeItemResponse(BaseModel):
    """One raw item in a production batch recipe snapshot."""

    id: int
    raw_item_id: str
    raw_item_name: str
    quantity_per_unit: Decimal = Field(..., description="Units of raw item per 1 unit of final product")
    avg_price: Optional[Decimal] = Field(None, description="Current average price of raw item")
    total_quantity: int = Field(..., description="Current stock of raw item")
    
    @field_serializer("quantity_per_unit", "avg_price")
    def _serialize_decimal(self, v):
        return _decimal_two_places(v)

    class Config:
        from_attributes = True


class ProductionBatchDetailResponse(BaseModel):
    """Detailed production batch with recipe snapshot and calculations."""

    id: str
    final_product_id: str
    final_product_name: str
    quantity_produced: int
    stage: ProductionStageEnum
    serial_numbers: List[str] = Field(default_factory=list)
    recipe_items: List[ProductionBatchRecipeItemResponse] = Field(default_factory=list)
    total_estimated_cost: Decimal = Field(..., description="Total cost for all units in this batch")
    cost_per_unit: Decimal = Field(..., description="Estimated cost per unit")
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer("total_estimated_cost", "cost_per_unit")
    def _serialize_decimal(self, v):
        return _decimal_two_places(v)

    class Config:
        from_attributes = True


class ProductionBatchRecipeItemUpdate(BaseModel):
    """Update a raw item in batch recipe."""

    raw_item_id: str = Field(..., min_length=1, max_length=10)
    quantity_per_unit: Decimal = Field(..., gt=0, description="Units of raw item per 1 unit of final product")

    @field_validator("quantity_per_unit")
    @classmethod
    def quantity_reasonable(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity_per_unit must be positive")
        return v


class ProductionBatchUpdate(BaseModel):
    """Update production batch in DRAFT stage (recipe items, quantity, serial numbers)."""

    quantity: Optional[int] = Field(None, ge=1, description="Update quantity (must match serial_numbers count)")
    serial_numbers: Optional[List[str]] = Field(
        None,
        min_length=1,
        description="Update serial numbers; LEH- prefix added if omitted",
    )
    recipe_items: Optional[List[ProductionBatchRecipeItemUpdate]] = Field(
        None,
        min_length=1,
        description="Update recipe items (replaces all existing items)",
    )

    @field_validator("serial_numbers")
    @classmethod
    def validate_serial_numbers(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if not v:
            raise ValueError("At least one serial number is required")
        seen = set()
        out = []
        for s in v:
            s = s.strip()
            if not s:
                raise ValueError("Serial number cannot be blank")
            s = normalize_serial_number(s)
            if s in seen:
                raise ValueError(f"Duplicate serial number: {s}")
            seen.add(s)
            out.append(s)
        return out

    @model_validator(mode="after")
    def validate_consistency(self):
        # If both quantity and serial_numbers provided, they must match
        if self.quantity is not None and self.serial_numbers is not None:
            if len(self.serial_numbers) != self.quantity:
                raise ValueError(
                    f"quantity ({self.quantity}) must equal number of serial_numbers ({len(self.serial_numbers)})"
                )
        return self
