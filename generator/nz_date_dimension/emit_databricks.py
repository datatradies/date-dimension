from .sql_common import DIALECTS, create_table_sql, insert_statements_sql, relative_view_sql

DIALECT = "databricks"

def emit_databricks(rows: list, table_name: str = "NZDateDimension",
                     view_name: str = "vw_NZDateDimensionRelative",
                     fiscal_start_month: int = 4, batch_size: int = 1000,
                     columns: list = None, primary_key: list = None) -> str:
    """Full Databricks SQL script: CREATE TABLE + batched INSERTs of the
    pre-computed stable rows, plus a companion VIEW deriving relative
    columns from current_date() (spec §7, §8).

    `columns` defaults to STABLE_COLUMNS (NZ); AU/Combined callers pass
    their own dataset's columns. `primary_key` defaults to `["Date"]`;
    Combined mode passes `["Date", "Country"]` (documented only -- Databricks
    never emits a real PRIMARY KEY constraint, see create_table_sql).
    """
    sep = DIALECTS[DIALECT]["statement_sep"]
    parts = [create_table_sql(table_name, DIALECT, columns=columns, primary_key=primary_key)]
    parts.extend(insert_statements_sql(rows, table_name, DIALECT, batch_size, columns=columns))
    parts.append(relative_view_sql(table_name, view_name, DIALECT, fiscal_start_month))
    return sep.join(parts) + "\n"

def write_databricks(rows: list, path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(emit_databricks(rows, **kwargs))
