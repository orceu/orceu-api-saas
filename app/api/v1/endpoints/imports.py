from fastapi import APIRouter, UploadFile, File, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
import os
from app.core.dependencies import get_tenant
from app.core.queue import enqueue_import_task

router = APIRouter()

MAX_FILE_SIZE_MB = 30
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

@router.post("/excel", status_code=status.HTTP_202_ACCEPTED)
def import_excel_file(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant)
):
    allowed_extensions = [".xls", ".xlsx", ".csv"]
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xls, .xlsx ou .csv")
    # Valida tamanho do arquivo
    file.file.seek(0, 2)  # Move para o final do arquivo
    file_size = file.file.tell()
    file.file.seek(0)  # Volta para o início
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede o limite de {MAX_FILE_SIZE_MB}MB")
    import_id = str(uuid4())
    # Garante que o diretório temporário existe
    tmp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"{import_id}_{filename}")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())
    # Enfileira a tarefa
    enqueue_import_task({
        "import_id": import_id,
        "tenant_id": tenant_id,
        "file_path": file_path,
        "filename": file.filename
    })
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"import_id": import_id, "message": "Arquivo Excel recebido e enfileirado para importação."})

@router.post("/estimate_analytics", status_code=status.HTTP_202_ACCEPTED)
def import_estimate_analytics(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant)
):
    try:
        allowed_extensions = [".docx", ".xlsx", ".csv", ".xls"]
        filename = file.filename.lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(status_code=400, detail="Arquivo deve ser PDF, DOCX, XLS, XLSX ou CSV")
        # Valida tamanho do arquivo
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"Arquivo excede o limite de {MAX_FILE_SIZE_MB}MB")
        import_id = str(uuid4())
        tmp_dir = os.path.join(os.getcwd(), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        file_path = os.path.join(tmp_dir, f"estimate_analytics_{import_id}_{filename}")
        with open(file_path, "wb") as f_out:
            f_out.write(file.file.read())
        enqueue_import_task({
            "import_id": import_id,
            "tenant_id": tenant_id,
            "file_path": file_path,
            "filename": file.filename,
            "type": "estimate_analytics"
        })
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"import_id": import_id, "message": "Documento recebido e tratado com sucesso."})
    except HTTPException as e:
        raise e
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Erro interno: {str(e)}"})
