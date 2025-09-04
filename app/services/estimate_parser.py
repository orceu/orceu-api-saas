# app/services/estimate_parser.py

import re
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

from app.utils.number import br_to_float
from app.services.estimate_tree import ensure_stage_path, add_child_to_index

# ----------------------------------
# Regexes e splits
# ----------------------------------
INDEX_AT_START_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.*)$", re.IGNORECASE)
PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
QTY_PRICE_INLINE_RE = re.compile(
    r"Quant\.\s*=>\s*([0-9\.,]+).+?Preço\s+Total\s*=>\s*([0-9\.,]+)",
    re.IGNORECASE
)
_SPLIT_RE = re.compile(r"\s{2,}|\t+")

# ----------------------------------
# Helpers básicos
# ----------------------------------
def clean_text(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s or None

def is_tabular_header(text: str) -> bool:
    low = text.lower()
    return (
        ("código" in low or "codigo" in low)
        and ("descri" in low)
        and ("quant" in low)
        and (("valor unit" in low) or ("val unit" in low) or ("valor unitário" in low))
        and ("total" in low)
    )

def is_tabular_item(tokens: List[str]) -> bool:
    if len(tokens) < 4:
        return False
    tail = tokens[:]
    total = br_to_float(tail[-1])
    unitv = br_to_float(tail[-2]) if len(tail) >= 2 else None
    quantv = br_to_float(tail[-3]) if len(tail) >= 3 else None
    return (total is not None) and (unitv is not None) and (quantv is not None)

def normalize_unit(u: Optional[str]) -> Optional[str]:
    if u is None:
        return None
    u = u.strip()
    repl = {
        "m2": "m²", "M2": "m²", "m^2": "m²", "M^2": "m²",
        "m3": "m³", "M3": "m³",
        "dia": "DIA", "Dia": "DIA", "DIA": "DIA",
        "un.": "UN", "Un.": "UN", "UN.": "UN",
        "un": "un", "Un": "un",  # manter "un" minúsculo se vier assim
        "h": "H", "H": "H",
        "l": "l", "L": "l",
        "kg": "Kg", "KG": "Kg",
        "vb": "VB", "Vb": "VB", "VB": "VB",
        "m": "m", "M": "M",
        "m²": "m²", "m³": "m³",
    }
    return repl.get(u, u)

# ----------------------------------
# Estágios (índice + nome + total)
# ----------------------------------
def parse_index_and_name_if_stage(text: str):
    m = INDEX_AT_START_RE.match(text)
    if not m:
        return None, None, None
    after = m.group(2).strip()
    low = after.lower()
    # não confundir com "Composição ..." ou linhas tabulares
    if low.startswith(("composição", "composicao", "composi", "composição auxiliar")):
        return None, None, None
    tokens = [p for p in _SPLIT_RE.split(after) if p.strip()]
    if is_tabular_item(tokens):
        return None, None, None
    # tentar capturar total ao fim da linha
    m_num = re.search(r"(?:^|\s)([-+]?\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)(\s*)$", after)
    price_total = None
    name = after
    if m_num:
        val = br_to_float(m_num.group(1))
        if val is not None:
            price_total = val
            name = after[:m_num.start()].rstrip(" -\t")
    return m.group(1), clean_text(name), price_total

def _extract_work_name_and_bdi(lines: List[str]) -> Tuple[Optional[str], Optional[float]]:
    work_name: Optional[str] = None
    bdi_global: Optional[float] = None

    for line in lines[:80]:
        low = line.lower()

        if bdi_global is None:
            m = PERCENT_RE.search(line)
            if m:
                val = br_to_float(m.group(1))
                if val is not None:
                    bdi_global = round(val / 100.0, 6)

        if ("obra" in low) and (not INDEX_AT_START_RE.match(line)):
            name_part = re.sub(r"(?i)\bobra\b[:\s-]*", "", line).strip()
            m = PERCENT_RE.search(name_part)
            if m:
                name_part = name_part[:m.start()].strip(" -:\t")
            if name_part and any(ch.isalpha() for ch in name_part):
                work_name = name_part

    if work_name is None:
        for line in lines[:50]:
            if sum(ch.isdigit() for ch in line) <= 2 and any(ch.isalpha() for ch in line):
                work_name = line.strip()
                break

    return work_name, bdi_global

# ----------------------------------
# Itens tabulares (composição/insumo)
# ----------------------------------
def parse_tabular_item_from_tokens(tokens: List[str]) -> Dict[str, Any]:
    # Consome de trás pra frente: total, unit, qty
    total = None
    while tokens and total is None:
        total = br_to_float(tokens[-1])
        if total is None:
            tokens.pop()
        else:
            tokens.pop()

    price_unit = None
    while tokens and price_unit is None:
        price_unit = br_to_float(tokens[-1])
        if price_unit is None:
            tokens.pop()
        else:
            tokens.pop()

    quantity = None
    while tokens and quantity is None:
        quantity = br_to_float(tokens[-1])
        if quantity is None:
            tokens.pop()
        else:
            tokens.pop()

    unit_symbol = None
    if tokens and br_to_float(tokens[-1]) is None and len(tokens[-1]) <= 5:
        unit_symbol = normalize_unit(tokens.pop())

    code = tokens[0] if tokens else None
    desc = " ".join(tokens[1:]) if len(tokens) > 1 else None

    return {
        "code": clean_text(code),
        "name": clean_text(desc),
        "unit_symbol": unit_symbol,
        "quantity": quantity,
        "price_unit": price_unit,
        "price_total": total,
    }

# ----------------------------------
# Pós-processamento: ajuste fino do schema
# ----------------------------------
def _find_stage_by_index(root_list: List[Dict[str, Any]], idx: str) -> Optional[Dict[str, Any]]:
    for item in root_list:
        if item.get("estimate_item_type") == "stage" and item.get("index") == idx:
            return item
        if item.get("estimate_item_type") == "stage":
            found = _find_stage_by_index(item.get("estimate_items", []), idx)
            if found:
                return found
    return None

def _finalize_schema_exact(estimate_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica apenas a transformação exigida pelo JSON-alvo:
    - No estágio de índice "1", renomear 'estimate_items' -> 'estimate_item'
    """
    stage_1 = _find_stage_by_index(estimate_data.get("estimate_items", []), "1")
    if stage_1 and "estimate_items" in stage_1:
        stage_1["estimate_item"] = stage_1.pop("estimate_items")
    return estimate_data

# ----------------------------------
# Parser principal
# ----------------------------------
def choose_sheet(xls: pd.ExcelFile) -> str:
    desired_names = [
        "analitico", "analítico", "analitico_orcamento",
        "planilha orçamentária analítica", "planilha orcamentaria analitica"
    ]
    lower_names = [s.lower() for s in xls.sheet_names]
    for name in desired_names:
        if name in lower_names:
            return xls.sheet_names[lower_names.index(name)]
    return xls.sheet_names[0]

def parse_excel_to_json_freeform(file_path: str) -> dict:
    xls = pd.ExcelFile(file_path)
    sheet_name = choose_sheet(xls)

    # lê a aba completa, sem header
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str)

    # nome da obra + bdi
    lines_joined = [" ".join(str(c) for c in row if pd.notna(c)) for _, row in df.iterrows()]
    work_name, bdi_global = _extract_work_name_and_bdi(lines_joined)

    estimate_data: Dict[str, Any] = {
        "name": work_name,
        "bdi_global": bdi_global,
        "estimate_items": []
    }

    current_composition: Optional[Dict[str, Any]] = None
    last_stage_index_for_auto: Optional[str] = None
    auto_seq = 0

    for _, row in df.iterrows():
        cells = [str(c).strip() if pd.notna(c) else "" for c in row.tolist()]
        if not any(cells):
            continue

        # cabeçalho tabular
        header_line = "".join(cells).lower()
        if ("código" in header_line and "descr" in header_line and "total" in header_line) \
           or ("tipagem" in header_line and "código" in header_line):
            continue

        # -------------------------
        # caso 1: stage (índice + nome)
        # -------------------------
        m_idx = INDEX_AT_START_RE.match(cells[0])
        if m_idx:
            idx = m_idx.group(1)
            name_stage = m_idx.group(2).strip()
            total_stage = br_to_float(cells[-1]) if cells[-1] else None

            node = ensure_stage_path(estimate_data["estimate_items"], idx.split("."))
            node["name"] = clean_text(name_stage)
            if total_stage is not None:
                node["price_total"] = total_stage

            current_composition = None
            last_stage_index_for_auto = idx
            auto_seq = 0
            continue

        # -------------------------
        # caso 2: linha tabular (>=9 colunas)
        # -------------------------
        if len(cells) >= 9:
            tipagem = cells[0].lower()
            item = {
                "estimate_item_type": "composition" if "comp" in tipagem else "resource",
                "code": clean_text(cells[1]),
                "bank": clean_text(cells[2]),
                "name": clean_text(cells[3]),
                "type": clean_text(cells[4]),
                "unit_symbol": normalize_unit(cells[5]),
                "quantity": br_to_float(cells[6]),
                "price_unit": br_to_float(cells[7]),
                "price_total": br_to_float(cells[8]),
            }

            if item["estimate_item_type"] == "composition":
                if last_stage_index_for_auto:
                    auto_seq += 1
                    comp_index = f"{last_stage_index_for_auto}.{auto_seq}"
                else:
                    comp_index = "1"
                item["index"] = comp_index
                item["composition_child"] = []
                add_child_to_index(estimate_data["estimate_items"], comp_index, item)
                current_composition = item
            else:
                if current_composition:
                    current_composition["composition_child"].append(item)
                else:
                    if last_stage_index_for_auto:
                        add_child_to_index(estimate_data["estimate_items"], last_stage_index_for_auto, item)
                    else:
                        estimate_data["estimate_items"].append(item)
            continue

    # ajuste final
    estimate_data = _finalize_schema_exact(estimate_data)
    return estimate_data

