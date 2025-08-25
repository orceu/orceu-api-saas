from fastapi import FastAPI
from app.api.v1.endpoints import clients, locations

app = FastAPI(title="Orceu API SaaS")

app.include_router(clients.router, prefix="/v1/clients", tags=["clients"])
app.include_router(locations.router, prefix="/v1/locations", tags=["locations"])
