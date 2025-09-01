from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do segredo e algoritmo do JWT (ajuste conforme necessário)
JWT_SECRET = os.getenv("JWT_SECRET", "AquiToken")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

security = HTTPBearer()

def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        if token.startswith("Bearer "):
            token = token[7:]

        # Desativa a verificação de audience
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False}  # ← Desativa verificação
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token JWT inválido ou expirado: {str(e)}"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = decode_jwt(token)
    # Aqui você pode validar claims, tenant, etc.
    return payload
