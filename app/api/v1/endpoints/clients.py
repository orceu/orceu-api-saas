from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("/", response_model=List[str])
def list_clients():
    # Aqui futuramente será integrado com o orceu-core
    return ["Cliente 1", "Cliente 2"]


