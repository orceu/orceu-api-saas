from pydantic import BaseModel
from typing import Optional

class LocationResponse(BaseModel):
    id: str
    name: str
    address: Optional[str]

class LocationListResponse(BaseModel):
    locations: list[LocationResponse]

