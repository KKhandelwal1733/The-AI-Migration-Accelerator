from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def _safe_type_name(raw_type: object) -> str:
    if raw_type is None:
        return "text"
    return str(raw_type).lower()


def _sample_rows(
    engine: Engine,
    table_name: str,
    dialect_name: str,
    sample_row_limit: int,
) -> list[dict[str, object]]:
    if sample_row_limit <= 0:
        return []

    if dialect_name == "oracle":
        query = text(f'SELECT * FROM {table_name} FETCH FIRST {sample_row_limit} ROWS ONLY')
    else:
        query = text(f'SELECT * FROM {table_name} LIMIT {sample_row_limit}')

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


def introspect_source(
    source_connection: str,
    include_sample_rows: bool,
    sample_row_limit: int,
) -> tuple[dict[str, object], str | None]:
    engine = create_engine(source_connection)

    try:
        inspector = inspect(engine)
        dialect_name = engine.dialect.name
        table_names = inspector.get_table_names()

        tables: list[dict[str, object]] = []
        constraints: list[dict[str, object]] = []

        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            primary_key = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)

            table_payload: dict[str, object] = {
                "name": table_name,
                "columns": [
                    {
                        "name": column["name"],
                        "type": _safe_type_name(column.get("type")),
                        "nullable": bool(column.get("nullable", True)),
                    }
                    for column in columns
                ],
                "primary_key": primary_key.get("constrained_columns", []),
                "foreign_keys": foreign_keys,
            }

            if include_sample_rows:
                table_payload["sample_rows"] = _sample_rows(
                    engine=engine,
                    table_name=table_name,
                    dialect_name=dialect_name,
                    sample_row_limit=sample_row_limit,
                )

            tables.append(table_payload)

            if primary_key.get("constrained_columns"):
                constraints.append(
                    {
                        "type": "primary_key",
                        "table": table_name,
                        "columns": primary_key.get("constrained_columns", []),
                    }
                )

            for fk in foreign_keys:
                constraints.append(
                    {
                        "type": "foreign_key",
                        "table": table_name,
                        "columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns", []),
                    }
                )

        return {"tables": tables, "constraints": constraints}, None
    except (SQLAlchemyError, Exception) as exc:
        return {"tables": [], "constraints": []}, str(exc)
    finally:
        engine.dispose()
