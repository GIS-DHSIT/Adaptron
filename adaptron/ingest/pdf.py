from __future__ import annotations

from pathlib import Path

from adaptron.core.registry import register_plugin
from adaptron.ingest.base import BaseIngester
from adaptron.ingest.models import DataSource, RawDocument


@register_plugin("ingester", "pdf")
class PDFIngester(BaseIngester):
    def ingest(self, source: DataSource) -> list[RawDocument]:
        path = Path(source.path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        from pypdf import PdfReader

        reader = PdfReader(path)
        documents = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                documents.append(
                    RawDocument(
                        content=text.strip(),
                        metadata={"page": i + 1, "total_pages": len(reader.pages)},
                        source_ref=str(path),
                    )
                )
        return documents

    def supported_types(self) -> list[str]:
        return ["pdf"]
