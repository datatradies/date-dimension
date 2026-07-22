"""Guards spec section 11's "cross-format consistency" requirement: CSV,
SQL (T-SQL INSERT data), and Power Query (M) all derive from the SAME
`rows` list (spec section 3's single-source-of-truth architecture), so
this test round-trip-decodes a representative sample of dates from each
format's own literal syntax and asserts every STABLE column agrees with
the original computed value and with the other two formats. This is the
guard against one emitter silently drifting (wrong column order, a
formatting bug, a dropped column) even though each emitter's own unit
tests pass individually -- exactly the trailing-comma-class bug found and
fixed in emit_dbt.py during development.

Deliberately NOT a full byte-for-byte round-trip of every row (no SQL/M
parser exists in this stdlib-only project) -- covers a representative
sample spanning every stable-column category: a national holiday, a
regional-only holiday, an ordinary weekday, a weekend, and Christmas.
"""
import csv
import io
import re
from datetime import date
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.emit_csv import write_csv
from nz_date_dimension.emit_tsql import emit_tsql
from nz_date_dimension.emit_powerquery import emit_powerquery
from nz_date_dimension.sql_common import column_kind

SAMPLE_DATES = [
    date(2025, 1, 1),    # New Year's Day -- national holiday
    date(2025, 1, 27),   # Auckland Anniversary -- regional-only holiday
    date(2025, 7, 23),   # ordinary weekday
    date(2025, 7, 26),   # Saturday -- weekend, non-holiday
    date(2025, 12, 25),  # Christmas -- national holiday
]

def _split_top_level(s: str, quote_char: str) -> list:
    """Split a comma-separated literal list on top-level commas, respecting
    quote_char-quoted strings (escaped by doubling, per both SQL '' and M
    "" convention) and parenthesis nesting (M's #date(y, m, d) contains
    commas that must NOT be treated as field separators).
    """
    tokens, current, in_quotes, depth = [], "", False, 0
    i = 0
    while i < len(s):
        ch = s[i]
        if in_quotes:
            if ch == quote_char and i + 1 < len(s) and s[i + 1] == quote_char:
                current += quote_char * 2
                i += 2
                continue
            if ch == quote_char:
                in_quotes = False
                current += ch
                i += 1
                continue
            current += ch
            i += 1
            continue
        if ch == quote_char:
            in_quotes = True
            current += ch
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            tokens.append(current.strip())
            current = ""
            i += 1
            continue
        current += ch
        i += 1
    if current.strip():
        tokens.append(current.strip())
    return tokens

def _decode_sql_token(token: str, kind: str, dialect: str):
    if token == "NULL":
        return None
    if kind == "bool":
        return token == ("1" if dialect == "tsql" else "TRUE")
    if kind == "date":
        m = re.match(r"'(\d{4})-(\d{2})-(\d{2})'", token)
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if kind == "int":
        return int(token)
    return token[1:-1].replace("''", "'")

def _decode_m_token(token: str, kind: str):
    if token == "null":
        return None
    if kind == "bool":
        return token == "true"
    if kind == "date":
        m = re.match(r"#date\((\d+),\s*(\d+),\s*(\d+)\)", token)
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if kind == "int":
        return int(token)
    return token[1:-1].replace('""', '"')

def _decode_csv_value(value: str, kind: str):
    if value == "":
        return None
    if kind == "bool":
        return value == "true"
    if kind == "date":
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    if kind == "int":
        return int(value)
    return value

def _extract_row_tokens(text: str, date_key: int, first_field_pattern: str, close_char: str,
                         quote_char: str) -> list:
    pattern = re.compile(
        rf"{first_field_pattern}, {date_key}, .*?{re.escape(close_char)}", re.DOTALL
    )
    m = pattern.search(text)
    assert m, f"row for DateKey {date_key} not found (pattern: {first_field_pattern})"
    inner = m.group(0)[1:-1]  # strip outer ( or {
    return _split_top_level(inner, quote_char)

def test_stable_columns_agree_across_csv_sql_and_powerquery(tmp_path):
    rows = build_dataset(2025, 2025)  # 365 rows
    rows_by_date = {r["Date"]: r for r in rows}

    csv_path = tmp_path / "nz.csv"
    write_csv(rows, str(csv_path), generated_on=date(2026, 7, 22))
    with open(csv_path, newline="", encoding="utf-8") as f:
        csv_by_date = {r["Date"]: r for r in csv.DictReader(f)}

    sql_text = emit_tsql(rows, fiscal_start_month=4)
    m_text = emit_powerquery(rows, fiscal_start_month=4)

    for d in SAMPLE_DATES:
        original = rows_by_date[d]
        date_key = original["DateKey"]

        csv_row = csv_by_date[d.isoformat()]
        sql_tokens = _extract_row_tokens(
            sql_text, date_key, r"\('\d{4}-\d{2}-\d{2}'", ")", "'"
        )
        m_tokens = _extract_row_tokens(
            m_text, date_key, r"\{#date\(\d+,\s*\d+,\s*\d+\)", "}", '"'
        )

        for i, col in enumerate(STABLE_COLUMNS):
            kind = column_kind(col)
            expected = original[col]
            csv_val = _decode_csv_value(csv_row[col], kind)
            sql_val = _decode_sql_token(sql_tokens[i], kind, "tsql")
            m_val = _decode_m_token(m_tokens[i], kind)
            assert csv_val == expected, f"{d} {col}: CSV={csv_val!r} != source={expected!r}"
            assert sql_val == expected, f"{d} {col}: T-SQL={sql_val!r} != source={expected!r}"
            assert m_val == expected, f"{d} {col}: M={m_val!r} != source={expected!r}"
