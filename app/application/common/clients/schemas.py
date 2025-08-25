from pydantic import BaseModel
from typing import Optional

class ClientResponse(BaseModel):
    id: str
    name: str
    email: Optional[str]

class ClientListResponse(BaseModel):
    clients: list[ClientResponse]

