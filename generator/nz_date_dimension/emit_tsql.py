from .sql_common import DIALECTS, create_table_sql, insert_statements_sql, relative_view_sql

DIALECT = "tsql"

def emit_tsql(rows: list, table_name: str = "NZDateDimension",
               view_name: str = "vw_NZDateDimensionRelative",
               fiscal_start_month: int = 4, batch_size: int = 1000,
               columns: list = None, primary_key: list = None) -> str:
    """Full T-SQL script: CREATE TABLE + batched INSERTs of the pre-computed
    stable rows, plus a companion VIEW deriving relative columns from
    CURRENT_DATE (spec §7, §8). T-SQL requires CREATE VIEW to be the only
    statement in its batch, so GO separators are inserted between sections.

    `columns` defaults to STABLE_COLUMNS (NZ); AU/Combined callers pass
    their own dataset's columns. `primary_key` defaults to `["Date"]`;
    Combined mode passes `["Date", "Country"]`.
    """
    sep = DIALECTS[DIALECT]["statement_sep"]
    parts = [create_table_sql(table_name, DIALECT, columns=columns, primary_key=primary_key)]
    parts.extend(insert_statements_sql(rows, table_name, DIALECT, batch_size, columns=columns))
    parts.append(relative_view_sql(table_name, view_name, DIALECT, fiscal_start_month))
    return sep.join(parts) + "\n"

def write_tsql(rows: list, path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(emit_tsql(rows, **kwargs))
