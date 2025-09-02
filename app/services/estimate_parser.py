import re
from typing import Optional, List, Dict, Any
import pandas as pd

from app.utils.number import br_to_float
from app.services.estimate_tree import ensure_stage_path, add_child_to_index

# Regexes
INDEX_AT_START_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.*)$", re.IGNORECASE)
PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
QTY_PRICE_INLINE_RE = re.compile(r"Quant\.\s*=>\s*([0-9\.,]+).+?Preço\s+Total\s*=>\s*([0-9\.,]+)", re.IGNORECASE)

def clean_text(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s or None

def is_tabular_header(text: str) -> bool:
    low = text.lower()
    return (
        ("código" in low or "codigo" in low) and
        ("descri" in low) and
        ("quant" in low) and
        ("valor" in low) and
        ("total" in low)
    )

def is_tabular_item(tokens: List[str]) -> bool:
    # Considera tabular se, varrendo do fim, conseguirmos obter 3 números válidos seguidos (total, unit, quant)
    if len(tokens) < 4:
        return False
    tail = tokens[:]
    total = br_to_float(tail[-1])
    unitv = br_to_float(tail[-2]) if len(tail) >= 2 else None
    quantv = br_to_float(tail[-3]) if len(tail) >= 3 else None
    # Precisamos pelo menos desses três números; a unidade virá antes deles
    return (total is not None) and (unitv is not None) and (quantv is not None)

def normalize_unit(u: Optional[str]) -> Optional[str]:
    if u is None:
        return None
    u = u.strip()
    # normalizações comuns
    repl = {
        "m2": "m²",
        "M2": "m²",
        "m^2": "m²",
        "M^2": "m²",
    }
    return repl.get(u, u)

def parse_index_and_name_if_stage(text: str):
    """
    Detecta stage: idx + name [+ total no fim].
    Regras:
    - Se após o índice parecer linha tabular ou começar com 'Composição'/'Insumo', não é stage.
    - price_total é extraído como o último número "limpo" no final, se esse número vier
      separado por espaços (ou seja, não colado em letras).
    """
    m = INDEX_AT_START_RE.match(text)
    if not m:
        return None, None, None

    after = m.group(2).strip()
    low = after.lower()

    # Se for composição/insumo, não é stage
    if low.startswith(("composição", "composicao", "composi", "insumo")):
        return None, None, None

    # Se parecer tabular, não é stage
    tokens = [p for p in re.split(r"\s{2,}|\t+", after) if p.strip()]
    if is_tabular_item(tokens):
        return None, None, None

    # Extrai último número da linha (provável total) se estiver isolado
    # Critério: um número no final, separado por espaço, sem letras junto
    m_num = re.search(r"(?:^|\s)([-+]?\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)(\s*)$", after)
    price_total = None
    name = after
    if m_num:
        val = br_to_float(m_num.group(1))
        if val is not None:
            price_total = val
            # remove o sufixo numérico do nome
            name = after[:m_num.start()].rstrip(" -\t")

    return m.group(1), clean_text(name), price_total

def find_bdi(text_lines: List[str]) -> Optional[float]:
    # Procura "ADM 15,0%" ou "BDI 15%"
    for line in text_lines[:30]:
        m = PERCENT_RE.search(line)
        if m:
            val = br_to_float(m.group(1))
            if val is not None:
                return round(val / 100.0, 6)
    return None

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

def parse_tabular_item_from_tokens(tokens):
    # Total = último número válido
    total = None
    while tokens and total is None:
        total = br_to_float(tokens[-1])
        if total is None: tokens.pop()
        else: tokens.pop()

    # Valor unitário = próximo número válido
    price_unit = None
    while tokens and price_unit is None:
        price_unit = br_to_float(tokens[-1])
        if price_unit is None: tokens.pop()
        else: tokens.pop()

    # Quantidade = próximo número válido
    quantity = None
    while tokens and quantity is None:
        quantity = br_to_float(tokens[-1])
        if quantity is None: tokens.pop()
        else: tokens.pop()

    # Unidade = próximo token (curto e não-numérico)
    unit_symbol = None
    if tokens and br_to_float(tokens[-1]) is None and len(tokens[-1]) <= 5:
        unit_symbol = normalize_unit(tokens.pop())

    # O resto é código + descrição
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

def parse_excel_to_json_freeform(file_path: str) -> dict:
    xls = pd.ExcelFile(file_path)
    sheet_name = choose_sheet(xls)

    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str)
    lines: List[str] = []
    for _, row in df.iterrows():
        cells = [c for c in row.tolist() if pd.notna(c)]
        text = "    ".join(str(c) for c in cells).strip()
        if text:
            lines.append(text)

    # Nome da obra
    work_name: Optional[str] = None
    for line in lines[:50]:
        low = line.lower()
        if ("planilha" in low and "analit" in low) or ("analít" in low):
            continue
        if INDEX_AT_START_RE.match(line):
            continue
        if "obra" in low:
            perc = PERCENT_RE.search(line)
            name_part = line[:perc.start()].strip(" -:\t") if perc else line
            name_part = re.sub(r"(?i)\bobra\b[:\s-]*", "", name_part).strip()
            if name_part:
                work_name = name_part
                break
        if sum(ch.isdigit() for ch in line) <= 2 and any(ch.isalpha() for ch in line):
            work_name = line.strip()
            break

    bdi_global = find_bdi(lines)

    estimate_data: Dict[str, Any] = {
        "name": work_name,
        "bdi_global": bdi_global,
        "estimate_items": []
    }

    current_composition: Optional[Dict[str, Any]] = None
    last_stage_index_for_auto: Optional[str] = None
    auto_seq = 0

    for line in lines:
        low = line.lower()

        # Ignora cabeçalhos tabulares
        if is_tabular_header(line):
            continue

        # 1) Linha que começa com índice: decidir se é stage ou item tabular com índice explícito
        m_idx = INDEX_AT_START_RE.match(line)
        if m_idx:
            idx = m_idx.group(1)
            after = m_idx.group(2).strip()
            after_low = after.lower()

            # Caso 1: "idx Composição ..." => composição com índice explícito
            if after_low.startswith(("composição", "composicao", "composi")):
                tokens = [p for p in re.split(r"\s{2,}|\t+", after) if p.strip()]
                if is_tabular_item(tokens):
                    item = parse_tabular_item_from_tokens(tokens)
                    comp = {
                        "estimate_item_type": "composition",
                        "index": idx,
                        "code": item["code"],
                        "name": item["name"],
                        "unit_symbol": item["unit_symbol"],
                        "quantity": item["quantity"],
                        "price_unit": item["price_unit"],
                        "price_total": item["price_total"],
                        "composition_child": []
                    }
                    add_child_to_index(estimate_data["estimate_items"], idx, comp)
                    current_composition = comp
                    last_stage_index_for_auto = ".".join(idx.split(".")[:-1]) if "." in idx else None
                    auto_seq = int(idx.split(".")[-1]) if "." in idx else 0
                    continue
                # Se não parecer tabular, trata como stage (caso raro)

            # Caso 2: "idx Insumo ..." => resource direto com índice explícito
            if after_low.startswith("insumo"):
                tokens = [p for p in re.split(r"\s{2,}|\t+", after) if p.strip()]
                if is_tabular_item(tokens):
                    item = parse_tabular_item_from_tokens(tokens)
                    res = {
                        "estimate_item_type": "resource",
                        "index": idx,
                        "code": item["code"],
                        "name": item["name"],
                        "unit_symbol": item["unit_symbol"],
                        "quantity": item["quantity"],
                        "price_unit": item["price_unit"],
                        "price_total": item["price_total"]
                    }
                    add_child_to_index(estimate_data["estimate_items"], idx, res)
                    current_composition = None
                    last_stage_index_for_auto = ".".join(idx.split(".")[:-1]) if "." in idx else None
                    auto_seq = int(idx.split(".")[-1]) if "." in idx else 0
                    continue

            # Caso 3: "idx <linha tabular sem rótulo>" => resource direto com índice explícito
            # Ex.: "2.5.4 RZ0974  Próprio  Material de limpeza  VB  10  20  200"
            tokens = [p for p in re.split(r"\s{2,}|\t+", after) if p.strip()]
            if is_tabular_item(tokens):
                item = parse_tabular_item_from_tokens(tokens)
                res = {
                    "estimate_item_type": "resource",
                    "index": idx,
                    "code": item["code"],
                    "name": item["name"],
                    "unit_symbol": item["unit_symbol"],
                    "quantity": item["quantity"],
                    "price_unit": item["price_unit"],
                    "price_total": item["price_total"]
                }
                add_child_to_index(estimate_data["estimate_items"], idx, res)
                current_composition = None
                last_stage_index_for_auto = ".".join(idx.split(".")[:-1]) if "." in idx else None
                auto_seq = int(idx.split(".")[-1]) if "." in idx else 0
                continue

            # Caso 4: não é tabular — deve ser stage
            idx_stage, name_stage, stage_total = parse_index_and_name_if_stage(line)
            if idx_stage:
                node = ensure_stage_path(estimate_data["estimate_items"], idx_stage.split("."))
                if name_stage:
                    node["name"] = name_stage
                if stage_total is not None:
                    node["price_total"] = stage_total
                current_composition = None
                last_stage_index_for_auto = idx_stage
                auto_seq = 0
                continue
            # Se chegou aqui, cai para análise geral abaixo

        # 2) Linha "Composição ..." sem índice explícito: cria índice auto
        if low.startswith(("composição", "composicao", "composi")):
            tokens = [p for p in re.split(r"\s{2,}|\t+", line) if p.strip()]
            if not is_tabular_item(tokens):
                # linha incompleta; ignore
                continue
            item = parse_tabular_item_from_tokens(tokens)
            # Gera índice após último estágio
            if last_stage_index_for_auto:
                auto_seq += 1
                comp_index = f"{last_stage_index_for_auto}.{auto_seq}"
            else:
                comp_index = "1"
            comp = {
                "estimate_item_type": "composition",
                "index": comp_index,
                "code": item["code"],
                "name": item["name"],
                "unit_symbol": item["unit_symbol"],
                "quantity": item["quantity"],
                "price_unit": item["price_unit"],
                "price_total": item["price_total"],
                "composition_child": []
            }
            add_child_to_index(estimate_data["estimate_items"], comp_index, comp)
            current_composition = comp
            continue

        # 3) Linha "Insumo ..." (filho da composição atual)
        if low.startswith("insumo"):
            if current_composition is None:
                # Sem composição aberta: ignore ou trate como item solto (aqui ignoramos)
                continue
            tokens = [p for p in re.split(r"\s{2,}|\t+", line) if p.strip()]
            if not is_tabular_item(tokens):
                continue
            item = parse_tabular_item_from_tokens(tokens)
            res = {
                "estimate_item_type": "resource",
                "code": item["code"],
                "name": item["name"],
                "unit_symbol": item["unit_symbol"],
                "quantity": item["quantity"],
                "price_unit": item["price_unit"],
                "price_total": item["price_total"]
            }
            current_composition["composition_child"].append(res)
            continue

        # 4) Linha "Quant. => ... Preço Total => ..." atualiza a composição corrente
        if ("quant." in low) and ("preço total" in low or "preco total" in low):
            m = QTY_PRICE_INLINE_RE.search(line)
            if m and current_composition is not None:
                q = br_to_float(m.group(1))
                tot = br_to_float(m.group(2))
                if q is not None:
                    current_composition["quantity"] = q
                if tot is not None:
                    current_composition["price_total"] = tot
            continue

        # Outras linhas: ignorar

    return estimate_data