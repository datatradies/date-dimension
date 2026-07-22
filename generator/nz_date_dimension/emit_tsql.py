from .sql_common import DIALECTS, create_table_sql, insert_statements_sql, relative_view_sql

DIALECT = "tsql"

def emit_tsql(rows: list, table_name: str = "NZDateDimension",
               view_name: str = "vw_NZDateDimensionRelative",
               fiscal_start_month: int = 4, batch_size: int = 1000) -> str:
    """Full T-SQL script: CREATE TABLE + batched INSERTs of the pre-computed
    stable rows, plus a companion VIEW deriving relative columns from
    CURRENT_DATE (spec §7, §8). T-SQL requires CREATE VIEW to be the only
    statement in its batch, so GO separators are inserted between sections.
    """
    sep = DIALECTS[DIALECT]["statement_sep"]
    parts = [create_table_sql(table_name, DIALECT)]
    parts.extend(insert_statements_sql(rows, table_name, DIALECT, batch_size))
    parts.append(relative_view_sql(table_name, view_name, DIALECT, fiscal_start_month))
    return sep.join(parts) + "\n"

def write_tsql(rows: list, path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(emit_tsql(rows, **kwargs))
