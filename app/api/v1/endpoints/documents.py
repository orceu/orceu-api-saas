# app/api/v1/endpoints/documents.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from uuid import uuid4
import os
import tempfile

from app.core.dependencies import get_tenant
from app.services.storage_manager import S3FileManager

router = APIRouter()
s3_manager = S3FileManager()

# ============================================
# DOCUMENTS PIPELINE
# ============================================

@router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant)
):
    """
    1) Gera UUID para o documento.
    2) Cria 'pasta' no S3 para o tenant/document_id (prefixo).
    3) Faz upload do arquivo.
    4) Retorna metadados + URL de download temporária.
    """
    document_id = str(uuid4())

    # define "pasta lógica" no bucket
    prefix = f"documents/{tenant_id}/{document_id}/"

    # cria arquivo temporário local
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    # chave do objeto final (nome original dentro da pasta do doc)
    object_name = f"{prefix}{file.filename}"

    # upload para o S3
    s3_manager.upload_file(tmp_path, object_name)

    # opcional: cria marcador de pasta
    s3_manager.upload_file(tmp_path, f"{prefix}.keep")

    # limpa temp
    os.remove(tmp_path)

    # gera link de download
    download_url = s3_manager.generate_presigned_url(object_name)

    return {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "object_name": object_name,
        "download_url": download_url,
        "message": "Documento recebido e armazenado com sucesso."
    }


@router.get("/documents/imports/{document_id}/preview")
def preview_document(document_id: str, tenant_id: str = Depends(get_tenant)):
    """
    Detecta:
    - sheets
    - headers
    - amostra de linhas
    - delimitadores/encoding
    """
    # TODO: implementar análise real
    return {
        "document_id": document_id,
        "sheets": ["Sheet1", "Sheet2"],
        "headers": ["col1", "col2", "col3"],
        "sample_rows": [["a", "b", "c"], ["1", "2", "3"]],
        "delimiter": ",",
        "encoding": "utf-8"
    }


@router.post("/documents/imports/{document_id}/schema:infer")
def infer_schema(document_id: str, tenant_id: str = Depends(get_tenant)):
    """
    Infere tipos, unidades, chaves candidatas e sugere targets
    (resources, compositions, estimates, clients).
    """
    # TODO: lógica de inferência real
    return {
        "document_id": document_id,
        "inferred_schema": {
            "columns": {
                "Código": {"type": "string", "target": "resources.code"},
                "Quantidade": {"type": "float", "unit": "m²"},
            }
        },
        "targets": ["resources", "compositions"]
    }


@router.post("/documents/imports/{document_id}/mapping")
def update_mapping(document_id: str, mapping: dict, tenant_id: str = Depends(get_tenant)):
    """
    Recebe ou atualiza mapeamento coluna → campo do target + transformações.
    """
    # TODO: salvar mapping em banco
    return {"document_id": document_id, "mapping": mapping, "message": "Mapping atualizado."}


@router.post("/documents/imports/{document_id}/validate")
def validate_document(document_id: str, tenant_id: str = Depends(get_tenant)):
    """
    Valida o arquivo (ou lote) contra o schema do target.
    """
    # TODO: rodar validação real
    return {
        "document_id": document_id,
        "valid": True,
        "errors": [],
        "warnings": []
    }


@router.post("/documents/imports/{document_id}/simulate")
def simulate_import(document_id: str, tenant_id: str = Depends(get_tenant)):
    """
    Simula a importação:
    - contabiliza creates/updates/dups/erros sem gravar.
    """
    # TODO: lógica real de simulação
    return {
        "document_id": document_id,
        "creates": 10,
        "updates": 2,
        "duplicates": 1,
        "errors": 0
    }


@router.post("/documents/imports/{document_id}/process")
def process_import(document_id: str, tenant_id: str = Depends(get_tenant)):
    """
    Enfileira a importação real.
    """
    run_id = str(uuid4())
    # TODO: enfileirar no worker
    return {"document_id": document_id, "run_id": run_id, "status": "queued"}


@router.get("/documents/imports/{document_id}/runs/{run_id}")
def get_import_run_status(document_id: str, run_id: str, tenant_id: str = Depends(get_tenant)):
    """
    Retorna status, métricas e erros exportáveis de uma execução de importação.
    """
    # TODO: consultar status real do run
    return {
        "document_id": document_id,
        "run_id": run_id,
        "status": "running",
        "metrics": {"processed": 100, "errors": 2},
        "errors": [
            {"row": 10, "message": "Código inválido"},
            {"row": 25, "message": "Unidade não reconhecida"}
        ]
    }
