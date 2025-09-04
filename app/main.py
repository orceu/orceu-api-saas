from fastapi import FastAPI
from app.api.v1.endpoints import clients, locations, imports, documents

app = FastAPI(title="API SaaS - By Orceu")

app.include_router(clients.router, prefix="/v1/clients", tags=["clients"])
app.include_router(locations.router, prefix="/v1/locations", tags=["locations"])
app.include_router(imports.router, prefix="/v1/imports", tags=["imports"])
app.include_router(documents.router, prefix="/v1/documents", tags=["documents"])
