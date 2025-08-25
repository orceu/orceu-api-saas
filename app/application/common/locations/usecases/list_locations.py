from typing import List
from app.application.common.locations.schemas import LocationResponse

def list_locations_usecase(tenant_id: str) -> List[LocationResponse]:
    # Aqui você integraria com o orceu-core para buscar as localizações do tenant
    # Exemplo fictício:
    return [
        LocationResponse(id="1", name="Matriz", address="Rua Central, 100"),
        LocationResponse(id="2", name="Filial", address="Av. Leste, 200")
    ]

