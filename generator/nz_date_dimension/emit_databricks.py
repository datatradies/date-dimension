from .sql_common import DIALECTS, create_table_sql, insert_statements_sql, relative_view_sql

DIALECT = "databricks"

def emit_databricks(rows: list, table_name: str = "NZDateDimension",
                     view_name: str = "vw_NZDateDimensionRelative",
                     fiscal_start_month: int = 4, batch_size: int = 1000) -> str:
    """Full Databricks SQL script: CREATE TABLE + batched INSERTs of the
    pre-computed stable rows, plus a companion VIEW deriving relative
    columns from current_date() (spec §7, §8).
    """
    sep = DIALECTS[DIALECT]["statement_sep"]
    parts = [create_table_sql(table_name, DIALECT)]
    parts.extend(insert_statements_sql(rows, table_name, DIALECT, batch_size))
    parts.append(relative_view_sql(table_name, view_name, DIALECT, fiscal_start_month))
    return sep.join(parts) + "\n"

def write_databricks(rows: list, path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(emit_databricks(rows, **kwargs))
