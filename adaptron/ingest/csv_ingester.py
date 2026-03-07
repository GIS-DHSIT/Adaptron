from __future__ import annotations

import csv
from pathlib import Path

from adaptron.core.registry import register_plugin
from adaptron.ingest.base import BaseIngester
from adaptron.ingest.models import DataSource, RawDocument


@register_plugin("ingester", "csv")
class CSVIngester(BaseIngester):
    def ingest(self, source: DataSource) -> list[RawDocument]:
        path = Path(source.path)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)

        # Build a text representation of the CSV content
        lines = [",".join(headers)]
        for row in rows:
            lines.append(",".join(row.get(h, "") for h in headers))
        content = "\n".join(lines)

        # Store parsed rows in the tables field
        tables = [{"headers": headers, "rows": [dict(r) for r in rows]}]

        return [
            RawDocument(
                content=content,
                metadata={
                    "headers": headers,
                    "row_count": len(rows),
                },
                source_ref=str(path),
                tables=tables,
            )
        ]

    def supported_types(self) -> list[str]:
        return ["csv"]
