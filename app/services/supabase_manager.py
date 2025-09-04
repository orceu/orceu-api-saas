# app/services/supabase_manager.py

import os
from supabase import create_client, Client
from typing import List, Dict, Any, Optional


class SupabaseManager:
    """
    Classe genérica para gerenciar interações com o Supabase.
    Suporta autenticação via JWT para respeitar RLS.
    """

    def __init__(self, jwt_token: Optional[str] = None):
        url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")  # chave pública (não service_role!)

        if not url or not anon_key:
            raise RuntimeError("Variáveis SUPABASE_URL e SUPABASE_ANON_KEY não configuradas no .env")

        self.client: Client = create_client(url, anon_key)

        # Se for passado um JWT (usuário logado), ele será usado nas requisições
        if jwt_token:
            self.client.postgrest.auth(jwt_token)

    # --------------------------
    # Métodos genéricos
    # --------------------------

    def insert(self, table: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Insere um registro em uma tabela."""
        response = self.client.table(table).insert(data).execute()
        return response.data

    def bulk_insert(self, table: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insere vários registros de uma vez."""
        response = self.client.table(table).insert(data).execute()
        return response.data

    def get(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Consulta registros de uma tabela com filtros opcionais."""
        query = self.client.table(table).select("*")
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)
        response = query.execute()
        return response.data

    def update(self, table: str, filters: Dict[str, Any], new_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Atualiza registros que correspondem aos filtros."""
        query = self.client.table(table).update(new_values)
        for col, val in filters.items():
            query = query.eq(col, val)
        response = query.execute()
        return response.data

    def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Deleta registros que correspondem aos filtros."""
        query = self.client.table(table).delete()
        for col, val in filters.items():
            query = query.eq(col, val)
        response = query.execute()
        return response.data
