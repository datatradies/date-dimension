import csv
from datetime import date
from .build import STABLE_COLUMNS

def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, date):
        return v.isoformat()
    return v

def write_csv(rows: list, path: str, generated_on: date, columns: list = None) -> None:
    """`columns` defaults to STABLE_COLUMNS (NZ) for backward compatibility;
    AU/Combined callers pass their own dataset's actual columns.
    """
    cols = columns if columns is not None else STABLE_COLUMNS
    header = cols + ["GeneratedOn"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([_fmt(r[c]) for c in cols] + [generated_on.isoformat()])
