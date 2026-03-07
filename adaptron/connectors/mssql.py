"""MSSQL connector using SQLAlchemy for schema discovery and data fetching."""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect, text

from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import (
    CollectionSchema,
    ConnectorConfig,
    DataSchema,
    FetchQuery,
    FieldInfo,
)
from adaptron.core.registry import register_plugin
from adaptron.ingest.models import RawDocument

# SQLAlchemy type to normalized type mapping
_TYPE_MAP: dict[str, str] = {
    "VARCHAR": "string",
    "NVARCHAR": "string",
    "TEXT": "string",
    "NTEXT": "string",
    "CHAR": "string",
    "NCHAR": "string",
    "INTEGER": "integer",
    "INT": "integer",
    "BIGINT": "integer",
    "SMALLINT": "integer",
    "TINYINT": "integer",
    "FLOAT": "float",
    "REAL": "float",
    "DOUBLE PRECISION": "float",
    "NUMERIC": "float",
    "DECIMAL": "float",
    "MONEY": "float",
    "SMALLMONEY": "float",
    "BIT": "boolean",
    "DATE": "datetime",
    "DATETIME": "datetime",
    "DATETIME2": "datetime",
    "SMALLDATETIME": "datetime",
    "DATETIMEOFFSET": "datetime",
    "VARBINARY": "binary",
    "IMAGE": "binary",
}


def _normalize_type(sa_type: Any) -> str:
    """Convert a SQLAlchemy column type to a normalized string."""
    type_str = str(sa_type).upper()
    for key, value in _TYPE_MAP.items():
        if key in type_str:
            return value
    return "string"


@register_plugin("connector", "mssql")
class MSSQLConnector(BaseConnector):
    """Connector for Microsoft SQL Server databases via SQLAlchemy."""

    def __init__(self) -> None:
        self._engine: Any = None
        self._config: ConnectorConfig | None = None

    @staticmethod
    def _build_conn_str(config: ConnectorConfig) -> str:
        """Construct mssql+pyodbc://user:pass@host:port/db from individual fields."""
        creds = config.credentials
        user = creds.username if creds else ""
        password = creds.password if creds else ""
        host = config.host or "localhost"
        port = config.port or 1433
        database = config.database or ""
        auth = f"{user}:{password}@" if user else ""
        return f"mssql+pyodbc://{auth}{host}:{port}/{database}"

    async def connect(self, config: ConnectorConfig) -> None:
        """Create SQLAlchemy engine from config."""
        self._config = config
        conn_str = config.connection_string or self._build_conn_str(config)
        self._engine = create_engine(conn_str, **config.options)

    async def disconnect(self) -> None:
        """Dispose the SQLAlchemy engine."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    @staticmethod
    def _build_select(query: FetchQuery) -> str:
        """Construct a SELECT statement from a FetchQuery."""
        cols = ", ".join(query.columns) if query.columns else "*"
        sql = f"SELECT {cols} FROM {query.collection}"

        if query.filters:
            clauses = [f"{k} = :filter_{k}" for k in query.filters]
            sql += " WHERE " + " AND ".join(clauses)

        if query.limit is not None:
            sql += f" LIMIT {query.limit}"

        if query.offset:
            sql += f" OFFSET {query.offset}"

        return sql

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        """Execute SQL and return a list of RawDocument."""
        if self._engine is None:
            raise RuntimeError("Not connected. Call connect() first.")

        if query.raw_query:
            sql_text = text(query.raw_query)
            params: dict[str, Any] = {}
        else:
            sql_text = text(self._build_select(query))
            params = {f"filter_{k}": v for k, v in (query.filters or {}).items()}

        documents: list[RawDocument] = []
        with self._engine.connect() as conn:
            result = conn.execute(sql_text, params)
            columns = list(result.keys())
            for row in result:
                row_dict = dict(zip(columns, row))
                content = ", ".join(f"{k}={v}" for k, v in row_dict.items())
                doc = RawDocument(
                    content=content,
                    metadata={
                        "table": query.collection,
                        "columns": columns,
                        "row": row_dict,
                    },
                    source_ref=f"mssql://{query.collection}",
                )
                documents.append(doc)

        return documents

    async def discover_schema(self) -> DataSchema:
        """Use SQLAlchemy inspect() to discover database schema."""
        if self._engine is None:
            raise RuntimeError("Not connected. Call connect() first.")

        insp = inspect(self._engine)
        table_names = insp.get_table_names()
        collections: list[CollectionSchema] = []

        for table_name in table_names:
            columns_info = insp.get_columns(table_name)
            pk_info = insp.get_pk_constraint(table_name)
            pk_cols = set(pk_info.get("constrained_columns", []))
            fk_list = insp.get_foreign_keys(table_name)

            relationships = []
            for fk in fk_list:
                ref = fk.get("referred_table", "")
                if ref:
                    relationships.append(ref)

            # Fetch sample values
            sample_rows: list[dict[str, Any]] = []
            try:
                with self._engine.connect() as conn:
                    result = conn.execute(
                        text(f"SELECT * FROM {table_name} LIMIT 5")
                    )
                    col_keys = list(result.keys())
                    for row in result:
                        sample_rows.append(dict(zip(col_keys, row)))
            except Exception:
                pass

            fields: list[FieldInfo] = []
            for col in columns_info:
                col_name = col["name"]
                samples = [r[col_name] for r in sample_rows if col_name in r]
                fields.append(
                    FieldInfo(
                        name=col_name,
                        data_type=_normalize_type(col["type"]),
                        nullable=col.get("nullable", True),
                        is_primary_key=col_name in pk_cols,
                        sample_values=samples,
                    )
                )

            collections.append(
                CollectionSchema(
                    name=table_name,
                    fields=fields,
                    relationships=relationships,
                    source_type="table",
                )
            )

        database = self._config.database or "" if self._config else ""
        return DataSchema(
            connector_type="mssql",
            database=database,
            collections=collections,
        )
