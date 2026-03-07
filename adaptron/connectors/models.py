from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class CredentialConfig:
    profile: str | None = None
    env_var: str | None = None
    aws_secret: str | None = None
    azure_vault: str | None = None
    username: str | None = None
    password: str | None = None

@dataclass
class ConnectorConfig:
    connector_type: str
    connection_string: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    credentials: CredentialConfig | None = None
    options: dict[str, Any] = field(default_factory=dict)

@dataclass
class FieldInfo:
    name: str
    data_type: str  # normalized: "string", "integer", "float", "boolean", "datetime", "json", "binary"
    nullable: bool = True
    is_primary_key: bool = False
    sample_values: list[Any] = field(default_factory=list)

@dataclass
class CollectionSchema:
    name: str
    fields: list[FieldInfo] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    row_count: int | None = None
    source_type: str = ""  # "table", "collection", "index", "endpoint", "bucket"

@dataclass
class DataSchema:
    connector_type: str
    database: str
    collections: list[CollectionSchema] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class FetchQuery:
    collection: str
    columns: list[str] | None = None
    filters: dict[str, Any] | None = None
    limit: int | None = None
    offset: int = 0
    raw_query: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
