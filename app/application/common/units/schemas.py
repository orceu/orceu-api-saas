from pydantic import BaseModel
from typing import Optional

class UnitResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]

class UnitListResponse(BaseModel):
    units: list[UnitResponse]

