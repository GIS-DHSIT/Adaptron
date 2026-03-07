from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class SourceType(enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    HTML = "html"
    SQL = "sql"
    ERP = "erp"
    CSV = "csv"
    TEXT = "text"


@dataclass
class DataSource:
    source_type: SourceType
    path: str | None = None
    connection_string: str | None = None
    query: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawDocument:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source_ref: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
