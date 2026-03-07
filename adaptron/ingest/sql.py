from __future__ import annotations

from adaptron.core.registry import register_plugin
from adaptron.ingest.base import BaseIngester
from adaptron.ingest.models import DataSource, RawDocument


@register_plugin("ingester", "sql")
class SQLIngester(BaseIngester):
    def __init__(self, sample_rows: int = 10) -> None:
        self.sample_rows = sample_rows

    def ingest(self, source: DataSource) -> list[RawDocument]:
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(source.connection_string)
        inspector = inspect(engine)
        documents = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            col_descriptions = [f"  - {col['name']} ({col['type']})" for col in columns]
            schema_text = f"Table: {table_name}\nColumns:\n" + "\n".join(col_descriptions)
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                fk_lines = [
                    f"  - {fk['constrained_columns']} -> "
                    f"{fk['referred_table']}.{fk['referred_columns']}"
                    for fk in fks
                ]
                schema_text += "\nForeign Keys:\n" + "\n".join(fk_lines)
            with engine.connect() as conn:
                result = conn.execute(
                    text(f'SELECT * FROM "{table_name}" LIMIT {self.sample_rows}')
                )
                rows = result.fetchall()
                col_names = list(result.keys())
            sample_text = ""
            if rows:
                sample_lines = []
                for row in rows:
                    row_str = ", ".join(
                        f"{col}={val}" for col, val in zip(col_names, row)
                    )
                    sample_lines.append(f"  {row_str}")
                sample_text = (
                    f"\nSample Data ({len(rows)} rows):\n" + "\n".join(sample_lines)
                )
            documents.append(
                RawDocument(
                    content=schema_text + sample_text,
                    metadata={
                        "table": table_name,
                        "columns": [c["name"] for c in columns],
                        "row_count": len(rows),
                    },
                    source_ref=f"sql://{table_name}",
                )
            )
        return documents

    def supported_types(self) -> list[str]:
        return ["sql"]
