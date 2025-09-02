import re
from typing import Optional

NUMBER_RE = re.compile(r"[-+]?\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?")

def br_to_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s:
        return None
    s = s.replace("\u00a0", " ")
    # tenta conversão direta após normalização
    try:
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        m = NUMBER_RE.search(s)
        if not m:
            return None
        token = m.group(0).replace(".", "").replace(",", ".")
        try:
            return float(token)
        except Exception:
            return None