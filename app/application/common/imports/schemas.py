from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal, Union

class ImportResponse(BaseModel):
    import_id: str
    message: str


class EstimateResource(BaseModel):
    estimate_item_type: Literal["resource"] = "resource"
    index: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    unit_symbol: Optional[str] = None
    quantity: Optional[float] = None
    price_unit: Optional[float] = None
    price_total: Optional[float] = None


class EstimateComposition(BaseModel):
    estimate_item_type: Literal["composition"] = "composition"
    index: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    unit_symbol: Optional[str] = None
    quantity: Optional[float] = None
    price_unit: Optional[float] = None
    price_total: Optional[float] = None
    composition_child: List[EstimateResource] = Field(default_factory=list)


class EstimateStage(BaseModel):
    estimate_item_type: Literal["stage"] = "stage"
    index: Optional[str] = None
    name: Optional[str] = None
    price_total: Optional[float] = None
    estimate_items: List[Union["EstimateStage", EstimateComposition, EstimateResource]] = Field(default_factory=list)


EstimateItem = Union[EstimateStage, EstimateComposition, EstimateResource]


class Estimate(BaseModel):
    name: Optional[str] = None
    bdi_global: Optional[float] = None
    estimate_items: List[EstimateItem] = Field(default_factory=list)

    @validator("bdi_global")
    def validate_bdi(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("bdi_global must be >= 0")
        return v

