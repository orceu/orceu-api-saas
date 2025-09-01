from fastapi import Depends
from app.core.auth import get_current_user

def get_tenant(user=Depends(get_current_user)):
    # Exemplo: extrai o tenant_id do payload do JWT
    tenant_id = user.get("sub")
    if not tenant_id:
        raise Exception("Sub não encontrado no token JWT.")
    return tenant_id

