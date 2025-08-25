from fastapi import APIRouter, Depends
from app.application.common.locations.schemas import LocationListResponse
from app.application.common.locations.usecases.list_locations import list_locations_usecase
from app.core.dependencies import get_tenant

router = APIRouter()

@router.get("/", response_model=LocationListResponse)
def list_locations(tenant_id: str = Depends(get_tenant)):
    locations = list_locations_usecase(tenant_id)
    return {"locations": locations}
