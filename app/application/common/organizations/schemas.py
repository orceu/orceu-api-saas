from pydantic import BaseModel
from typing import Optional

class OrganizationResponse(BaseModel):
    id: str
    name: str
    cnpj: Optional[str]

class OrganizationListResponse(BaseModel):
    organizations: list[OrganizationResponse]

