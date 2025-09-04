# app/api/v1/endpoints/imports.py

from fastapi import APIRouter, UploadFile, File, Depends, status, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from uuid import uuid4
import os
import tempfile
import shutil
import subprocess
import shlex
import platform

from app.core.dependencies import get_tenant
from app.core.queue import enqueue_import_task
from app.application.common.imports.schemas import Estimate
from app.services.estimate_parser import parse_excel_to_json_freeform

# -------------------------------------------------------------------
# 1) Router DEVE existir antes de qualquer decorator
# -------------------------------------------------------------------
router = APIRouter()

MAX_FILE_SIZE_MB = 30
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# ===================================================================
# ENDPOINT EXISTENTE (mantido 1:1)
# ===================================================================
@router.post("/estimate_analytics", status_code=status.HTTP_202_ACCEPTED)
def import_estimate_analytics(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant)
):
    allowed_extensions = [".xls", ".xlsx"]
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xls ou .xlsx")

    # valida tamanho
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede o limite de {MAX_FILE_SIZE_MB}MB")

    import_id = str(uuid4())

    tmp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"{import_id}_{os.path.basename(filename)}")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())

    enqueue_import_task({
        "import_id": import_id,
        "tenant_id": tenant_id,
        "file_path": file_path,
        "filename": file.filename
    })

    estimate_data = parse_excel_to_json_freeform(file_path)

    # valida com seu schema (opcional, mas recomendado)
    Estimate(**estimate_data)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "import_id": import_id,
            "message": "Arquivo Excel recebido e enfileirado para importação.",
            "estimate_data": estimate_data
        }
    )


# ===================================================================
# 2) Helpers para Markdown
#    (imports opcionais são feitos dentro das funções)
# ===================================================================
def _lazy_import_pymupdf4llm():
    try:
        import pymupdf4llm  # type: ignore
        return pymupdf4llm
    except Exception as e:
        raise RuntimeError("Dependência faltando: instale 'pymupdf4llm'.") from e


def _xlsx_to_pdf_windows(xlsx_path: str, pdf_path: str) -> None:
    """Converte via Microsoft Excel COM (Windows). Requer MS Office + pywin32."""
    try:
        import win32com.client  # type: ignore
    except Exception as e:
        raise RuntimeError("Para converter XLSX no Windows, instale 'pywin32' ou use LibreOffice.") from e

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    wb = None
    try:
        wb = excel.Workbooks.Open(os.path.abspath(xlsx_path))
        # (ajuda o detector baseado em linhas)
        try:
            for ws in wb.Worksheets:
                ws.PageSetup.PrintGridlines = True
        except Exception:
            pass
        # 0 = xlTypePDF
        wb.ExportAsFixedFormat(0, os.path.abspath(pdf_path))
    finally:
        try:
            if wb is not None:
                wb.Close(False)
        except Exception:
            pass
        excel.Quit()


def _xlsx_to_pdf_soffice(xlsx_path: str, pdf_path: str) -> None:
    """Converte via LibreOffice headless (soffice). Requer LibreOffice no PATH."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice ('soffice') não encontrado no PATH para converter XLSX -> PDF.")
    outdir = os.path.dirname(pdf_path) or "."
    cmd = f'"{soffice}" --headless --convert-to pdf "{xlsx_path}" --outdir "{outdir}"'
    subprocess.check_call(shlex.split(cmd))
    base_pdf = os.path.join(outdir, os.path.splitext(os.path.basename(xlsx_path))[0] + ".pdf")
    if os.path.abspath(base_pdf) != os.path.abspath(pdf_path):
        os.replace(base_pdf, pdf_path)


def _xlsx_to_markdown_raw(xlsx_path: str, strategy: str = "text", page_chunks: bool = False):
    pymupdf4llm = _lazy_import_pymupdf4llm()
    # 1) tenta direto (só funciona nativo para PDF e XLSX se PyMuPDF Pro estiver disponível)
    try:
        return pymupdf4llm.to_markdown(
            xlsx_path,
            table_strategy=strategy,
            page_chunks=page_chunks
        )
    except Exception:
        pass
    # 2) fallback para PDF
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "tmp.pdf")
        if platform.system().lower().startswith("win"):
            _xlsx_to_pdf_windows(xlsx_path, pdf_path)
        else:
            _xlsx_to_pdf_soffice(xlsx_path, pdf_path)

        return pymupdf4llm.to_markdown(
            pdf_path,
            table_strategy=strategy,
            page_chunks=page_chunks
        )


def _fmt_money(x):
    if x is None:
        return ""
    s = f"{x:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def _excel_to_markdown_tables(xlsx_path: str, only_sheet_contains: str | None = None) -> str:
    import pandas as pd  # lazy
    try:
        import tabulate  # noqa: F401  # garante que to_markdown funcione
    except Exception as e:
        raise RuntimeError("Dependência faltando: instale 'tabulate' para gerar Markdown de DataFrame.") from e

    xls = pd.ExcelFile(xlsx_path)
    sheet_names = xls.sheet_names
    chosen = (
        [s for s in sheet_names if only_sheet_contains and only_sheet_contains.lower() in s.lower()]
        or sheet_names
    )

    out = []
    for name in chosen:
        df = pd.read_excel(xlsx_path, sheet_name=name)
        if df.empty:
            continue
        out.append(f"# {name}")
        out.append(df.to_markdown(index=False))
        out.append("")  # linha em branco entre abas

    md = "\n".join(out).strip()
    return md or "# (Sem dados nas abas selecionadas)"


def _estimate_to_markdown(estimate_data: dict) -> str:
    lines = []
    name = estimate_data.get("name") or "Obra"
    bdi = estimate_data.get("bdi_global")
    header = f"# {name}"
    if bdi is not None:
        header += f"\n\n**BDI global:** {bdi:.2%}"
    lines.append(header)

    # Cabeçalho padrão
    TABLE_HEADER = (
        "| Tipagem | Código | Banco | Descrição | Tipo | Und | Quant. | Valor Unit | Total |\n"
        "|---|---|---|---|---|:---:|---:|---:|---:|"
    )

    def walk(items, level=2):
        for item in items or []:
            t = item.get("estimate_item_type")

            if t == "stage":
                # título de seção
                title = f'{"#"*level} {item.get("index","")} {item.get("name") or ""}'.strip()
                if item.get("price_total") is not None:
                    title += f" — {_fmt_money(item['price_total'])}"
                lines.append(title)
                walk(item.get("estimate_items") or item.get("estimate_item"), level + 1)

            elif t in ("composition", "resource"):
                # tabela única
                if not lines or not lines[-1].startswith("| Tipagem"):
                    lines.append("")
                    lines.append(TABLE_HEADER)

                desc = (item.get("name") or "").replace("|", "\\|")
                lines.append(
                    f"| {t} | {item.get('code','')} | {item.get('bank','')} | {desc} | "
                    f"{item.get('type','')} | {item.get('unit_symbol') or ''} | "
                    f"{'' if item.get('quantity') is None else item['quantity']} | "
                    f"{'' if item.get('price_unit') is None else _fmt_money(item['price_unit'])} | "
                    f"{'' if item.get('price_total') is None else _fmt_money(item['price_total'])} |"
                )

                # se for composição, também lista filhos
                if t == "composition":
                    for r in item.get("composition_child") or []:
                        desc_r = (r.get("name") or "").replace("|", "\\|")
                        lines.append(
                            f"| resource | {r.get('code','')} | {r.get('bank','')} | {desc_r} | "
                            f"{r.get('type','')} | {r.get('unit_symbol') or ''} | "
                            f"{'' if r.get('quantity') is None else r['quantity']} | "
                            f"{'' if r.get('price_unit') is None else _fmt_money(r['price_unit'])} | "
                            f"{'' if r.get('price_total') is None else _fmt_money(r['price_total'])} |"
                        )
                lines.append("")

    walk(estimate_data.get("estimate_items") or [], level=2)
    return "\n".join(lines)



# ===================================================================
# 3) NOVO ENDPOINT /estimate_markdown
# ===================================================================
@router.get("/estimate_markdown/{import_id}", name="get_estimate_markdown_file")
def get_estimate_markdown_file(import_id: str):
    md_path = os.path.join(os.getcwd(), "tmp", "markdown", f"{import_id}.md")
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Arquivo Markdown não encontrado.")
    return FileResponse(
        md_path,
        media_type="text/markdown; charset=utf-8",
        filename=f"orcamento_{import_id}.md"
    )
@router.post("/estimate_markdown", status_code=status.HTTP_200_OK)
def import_estimate_markdown(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant),
    mode: str = "semantic",     # 'semantic' (parser) ou 'raw' (tabular/llm)
    strategy: str = "text",     # para PDF no 'raw': 'text' | 'lines' | 'lines_strict'
    page_chunks: bool = False,
    request: Request = None,    # <-- adicionado para montar o download_url
):
    allowed_extensions = [".xls", ".xlsx", ".pdf"]
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xls, .xlsx ou .pdf")

    # valida tamanho
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede o limite de {MAX_FILE_SIZE_MB}MB")

    import_id = str(uuid4())

    tmp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"{import_id}_{os.path.basename(filename)}")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())

    ext_is_pdf = filename.endswith(".pdf")
    ext_is_xls = filename.endswith((".xls", ".xlsx"))

    try:
        engine_used = None

        if ext_is_xls:
            if mode == "semantic":
                # 1) Excel + semântico => parser -> markdown hierárquico
                estimate_data = parse_excel_to_json_freeform(file_path)
                Estimate(**estimate_data)
                md_text = _estimate_to_markdown(estimate_data)
                engine_used = "semantic-parser"
            else:
                # 2) Excel + raw => pandas -> markdown tabular (NÃO usa PyMuPDF)
                #    (opcional: filtrar aba "analític" se quiser focar)
                md_text = _excel_to_markdown_tables(file_path, only_sheet_contains="analític")
                engine_used = "pandas"
        elif ext_is_pdf:
            if mode == "semantic":
                # não faz sentido sem Excel -> avisa
                raise HTTPException(400, detail="Para PDF use mode=raw (ou envie Excel para modo semântico).")
            # 3) PDF + raw => PyMuPDF4LLM
            pymupdf4llm = _lazy_import_pymupdf4llm()
            # estratégia 'text' lida melhor com PDFs sem borda de tabela
            md_text = pymupdf4llm.to_markdown(
                file_path,
                table_strategy=strategy or "text",
                page_chunks=page_chunks
            )
            engine_used = f"pymupdf4llm:{strategy or 'text'}"

        else:
            raise HTTPException(400, detail="Extensão não suportada.")

    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao gerar Markdown: {e}")

    # salva o .md com o mesmo import_id
    md_dir = os.path.join(tmp_dir, "markdown")
    os.makedirs(md_dir, exist_ok=True)
    md_path = os.path.join(md_dir, f"{import_id}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    # monta o link para download (GET /estimate_markdown/{import_id})
    download_url = None
    if request is not None:
        try:
            download_url = str(request.url_for("get_estimate_markdown_file", import_id=import_id))
        except Exception:
            download_url = None

    enqueue_import_task({
        "import_id": import_id,
        "tenant_id": tenant_id,
        "file_path": file_path,
        "filename": file.filename,
        "op": f"estimate_markdown:{mode}",
        "engine_used": engine_used,
    })

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "import_id": import_id,
            "mode": mode,
            "engine_used": engine_used,
            "message": "Markdown gerado.",
            "markdown": md_text,
            "download_url": download_url,  # <-- link no mesmo endpoint
        }
    )

