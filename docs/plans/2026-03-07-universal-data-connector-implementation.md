# Universal Data Connector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a universal data connectivity layer that can plug into any database, API, or streaming source and automatically convert any dataset into optimized training data.

**Architecture:** Unified connector framework with `BaseConnector` ABC, `ConnectionManager` for credential/profile management, `TrainingFormatDetector` for auto-detecting optimal training format, `DataCleaner`/`DataAugmenter` for data quality, and new synthesizers (QA, Chat, DPO, Text2SQL, Corpus, Auto). All connectors are plugins in the existing `PluginRegistry`.

**Tech Stack:** SQLAlchemy (relational), PyMongo/motor (MongoDB), redis-py, elasticsearch-py, boto3 (DynamoDB/S3), cassandra-driver, google-cloud-bigquery, snowflake-connector-python, confluent-kafka, httpx (REST API), APScheduler (scheduling)

---

## Phase 1: Connector Framework & Core Infrastructure

### Task 1: Connector data models

**Files:**
- Create: `adaptron/connectors/__init__.py`
- Create: `adaptron/connectors/models.py`
- Create: `tests/connectors/__init__.py`
- Create: `tests/connectors/test_models.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_models.py
from adaptron.connectors.models import (
    ConnectorConfig, CredentialConfig, FieldInfo, CollectionSchema,
    DataSchema, FetchQuery,
)


def test_connector_config_defaults():
    config = ConnectorConfig(connector_type="postgresql")
    assert config.connector_type == "postgresql"
    assert config.connection_string is None
    assert config.options == {}


def test_credential_config_with_env_var():
    cred = CredentialConfig(env_var="DB_PASSWORD")
    assert cred.env_var == "DB_PASSWORD"
    assert cred.aws_secret is None


def test_field_info_with_samples():
    field = FieldInfo(name="email", data_type="string", sample_values=["a@b.com", "c@d.com"])
    assert field.name == "email"
    assert len(field.sample_values) == 2
    assert field.nullable is True


def test_collection_schema():
    schema = CollectionSchema(
        name="users",
        fields=[FieldInfo(name="id", data_type="integer", is_primary_key=True)],
        relationships=["orders.user_id -> users.id"],
        row_count=1500,
        source_type="table",
    )
    assert schema.name == "users"
    assert schema.fields[0].is_primary_key is True
    assert len(schema.relationships) == 1


def test_data_schema():
    ds = DataSchema(connector_type="postgresql", database="mydb")
    assert ds.collections == []


def test_fetch_query_defaults():
    q = FetchQuery(collection="users")
    assert q.columns is None
    assert q.limit is None
    assert q.offset == 0
    assert q.raw_query is None


def test_fetch_query_with_raw():
    q = FetchQuery(collection="users", raw_query="SELECT * FROM users WHERE active = true")
    assert q.raw_query is not None
```

**Step 2: Run tests to verify failure**

Run: `py -m pytest tests/connectors/test_models.py -v`
Expected: ImportError

**Step 3: Implement data models**

```python
# adaptron/connectors/__init__.py
"""Universal data connector framework."""

# adaptron/connectors/models.py
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
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class CollectionSchema:
    name: str
    fields: list[FieldInfo] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    row_count: int | None = None
    source_type: str = ""


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
```

**Step 4: Run tests**

Run: `py -m pytest tests/connectors/test_models.py -v`
Expected: All 7 pass

**Step 5: Commit**

```bash
git add adaptron/connectors/ tests/connectors/
git commit -m "feat: connector data models (ConnectorConfig, DataSchema, FetchQuery)"
```

---

### Task 2: BaseConnector interface

**Files:**
- Create: `adaptron/connectors/base.py`
- Create: `tests/connectors/test_base.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_base.py
import pytest
from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.ingest.models import RawDocument


def test_base_connector_is_abstract():
    with pytest.raises(TypeError):
        BaseConnector()


def test_base_connector_supports_streaming_default():
    class DummyConnector(BaseConnector):
        async def connect(self, config): pass
        async def disconnect(self): pass
        async def fetch(self, query): return []
        async def discover_schema(self): return DataSchema(connector_type="test", database="test")

    c = DummyConnector()
    assert c.supports_streaming() is False


@pytest.mark.asyncio
async def test_base_connector_stream_raises_by_default():
    class DummyConnector(BaseConnector):
        async def connect(self, config): pass
        async def disconnect(self): pass
        async def fetch(self, query): return []
        async def discover_schema(self): return DataSchema(connector_type="test", database="test")

    c = DummyConnector()
    with pytest.raises(NotImplementedError):
        async for _ in c.stream(FetchQuery(collection="test")):
            pass
```

**Step 2: Implement**

```python
# adaptron/connectors/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.ingest.models import RawDocument


class BaseConnector(ABC):
    @abstractmethod
    async def connect(self, config: ConnectorConfig) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def fetch(self, query: FetchQuery) -> list[RawDocument]: ...

    async def stream(self, query: FetchQuery) -> AsyncIterator[RawDocument]:
        raise NotImplementedError("This connector does not support streaming")
        yield  # makes it an async generator

    @abstractmethod
    async def discover_schema(self) -> DataSchema: ...

    def supports_streaming(self) -> bool:
        return False
```

**Step 3: Run tests, commit**

Run: `py -m pytest tests/connectors/test_base.py -v`

```bash
git add adaptron/connectors/base.py tests/connectors/test_base.py
git commit -m "feat: BaseConnector abstract interface with fetch/stream/discover_schema"
```

---

### Task 3: Credential resolver

**Files:**
- Create: `adaptron/connectors/credentials.py`
- Create: `tests/connectors/test_credentials.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_credentials.py
import os
import pytest
from unittest.mock import patch, MagicMock
from adaptron.connectors.credentials import CredentialResolver
from adaptron.connectors.models import CredentialConfig


def test_resolve_direct_credentials():
    resolver = CredentialResolver()
    cred = CredentialConfig(username="admin", password="secret123")
    result = resolver.resolve(cred)
    assert result["username"] == "admin"
    assert result["password"] == "secret123"


def test_resolve_env_var():
    resolver = CredentialResolver()
    cred = CredentialConfig(env_var="TEST_DB_URL")
    with patch.dict(os.environ, {"TEST_DB_URL": "postgresql://user:pass@host/db"}):
        result = resolver.resolve(cred)
    assert result["connection_string"] == "postgresql://user:pass@host/db"


def test_resolve_env_var_missing_raises():
    resolver = CredentialResolver()
    cred = CredentialConfig(env_var="NONEXISTENT_VAR_12345")
    with pytest.raises(ValueError, match="Environment variable"):
        resolver.resolve(cred)


def test_resolve_none_returns_empty():
    resolver = CredentialResolver()
    result = resolver.resolve(None)
    assert result == {}


def test_resolve_aws_secret_mocked():
    resolver = CredentialResolver()
    cred = CredentialConfig(aws_secret="arn:aws:secretsmanager:us-east-1:123:secret:mydb")
    mock_boto = MagicMock()
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": '{"username": "admin", "password": "secret"}'
    }
    mock_boto.client.return_value = mock_client
    with patch.dict("sys.modules", {"boto3": mock_boto}):
        result = resolver.resolve(cred)
    assert result["username"] == "admin"
    assert result["password"] == "secret"


def test_resolve_azure_vault_mocked():
    resolver = CredentialResolver()
    cred = CredentialConfig(azure_vault="https://myvault.vault.azure.net/secrets/dbpass")
    mock_secret = MagicMock()
    mock_secret.value = "my-secret-password"
    mock_client_cls = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.get_secret.return_value = mock_secret
    mock_client_cls.return_value = mock_client_instance
    mock_identity = MagicMock()
    mock_kv = MagicMock()
    mock_kv.SecretClient = mock_client_cls
    with patch.dict("sys.modules", {
        "azure.identity": mock_identity,
        "azure.keyvault.secrets": mock_kv,
    }):
        result = resolver.resolve(cred)
    assert result["password"] == "my-secret-password"
```

**Step 2: Implement**

```python
# adaptron/connectors/credentials.py
from __future__ import annotations

import json
import logging
import os
from typing import Any

from adaptron.connectors.models import CredentialConfig

logger = logging.getLogger(__name__)


class CredentialResolver:
    def resolve(self, config: CredentialConfig | None) -> dict[str, Any]:
        if config is None:
            return {}

        # Priority 1: Direct credentials
        if config.username or config.password:
            return {
                k: v for k, v in {
                    "username": config.username,
                    "password": config.password,
                }.items() if v is not None
            }

        # Priority 2: Environment variable
        if config.env_var:
            value = os.environ.get(config.env_var)
            if value is None:
                raise ValueError(
                    f"Environment variable '{config.env_var}' is not set. "
                    f"Set it before running Adaptron."
                )
            return {"connection_string": value}

        # Priority 3: AWS Secrets Manager
        if config.aws_secret:
            return self._resolve_aws(config.aws_secret)

        # Priority 4: Azure Key Vault
        if config.azure_vault:
            return self._resolve_azure(config.azure_vault)

        return {}

    def _resolve_aws(self, secret_arn: str) -> dict[str, Any]:
        try:
            import boto3
        except ImportError:
            raise RuntimeError(
                "boto3 is required for AWS Secrets Manager. "
                "Install it with: pip install boto3"
            )
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
        secret_str = response["SecretString"]
        try:
            return json.loads(secret_str)
        except json.JSONDecodeError:
            return {"password": secret_str}

    def _resolve_azure(self, vault_url: str) -> dict[str, Any]:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError:
            raise RuntimeError(
                "azure-identity and azure-keyvault-secrets are required. "
                "Install with: pip install azure-identity azure-keyvault-secrets"
            )
        # Parse vault URL: https://myvault.vault.azure.net/secrets/secretname
        parts = vault_url.rstrip("/").split("/")
        secret_name = parts[-1]
        vault_base = "/".join(parts[:-2])
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_base, credential=credential)
        secret = client.get_secret(secret_name)
        return {"password": secret.value}
```

**Step 3: Run tests, commit**

Run: `py -m pytest tests/connectors/test_credentials.py -v`

```bash
git add adaptron/connectors/credentials.py tests/connectors/test_credentials.py
git commit -m "feat: credential resolver with env var, AWS Secrets Manager, Azure Key Vault"
```

---

### Task 4: Connection manager with profiles

**Files:**
- Create: `adaptron/connectors/manager.py`
- Create: `tests/connectors/test_manager.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_manager.py
import pytest
from pathlib import Path
from adaptron.connectors.manager import ConnectionManager
from adaptron.connectors.models import ConnectorConfig, CredentialConfig


def test_save_and_load_profile(tmp_path):
    profiles_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(profiles_path=profiles_path)
    config = ConnectorConfig(
        connector_type="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
    )
    manager.save_profile("test-db", config)
    profiles = manager.list_profiles()
    assert "test-db" in profiles


def test_load_profile(tmp_path):
    profiles_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(profiles_path=profiles_path)
    config = ConnectorConfig(
        connector_type="mongodb",
        connection_string="mongodb://localhost:27017/mydb",
    )
    manager.save_profile("mongo-local", config)
    loaded = manager.load_profile("mongo-local")
    assert loaded.connector_type == "mongodb"
    assert loaded.connection_string == "mongodb://localhost:27017/mydb"


def test_load_missing_profile_raises(tmp_path):
    profiles_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(profiles_path=profiles_path)
    with pytest.raises(KeyError, match="not found"):
        manager.load_profile("nonexistent")


def test_remove_profile(tmp_path):
    profiles_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(profiles_path=profiles_path)
    config = ConnectorConfig(connector_type="redis", host="localhost")
    manager.save_profile("cache", config)
    manager.remove_profile("cache")
    assert "cache" not in manager.list_profiles()


def test_empty_profiles(tmp_path):
    profiles_path = tmp_path / "connections.yaml"
    manager = ConnectionManager(profiles_path=profiles_path)
    assert manager.list_profiles() == []
```

**Step 2: Implement**

```python
# adaptron/connectors/manager.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from adaptron.connectors.credentials import CredentialResolver
from adaptron.connectors.models import ConnectorConfig, CredentialConfig

logger = logging.getLogger(__name__)

_DEFAULT_PROFILES_PATH = Path.home() / ".adaptron" / "connections.yaml"


class ConnectionManager:
    def __init__(self, profiles_path: Path | None = None) -> None:
        self.profiles_path = Path(profiles_path or _DEFAULT_PROFILES_PATH)
        self._credential_resolver = CredentialResolver()

    def _load_file(self) -> dict[str, Any]:
        if not self.profiles_path.exists():
            return {"profiles": {}}
        with open(self.profiles_path) as f:
            data = yaml.safe_load(f) or {}
        return data if "profiles" in data else {"profiles": {}}

    def _save_file(self, data: dict[str, Any]) -> None:
        self.profiles_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profiles_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_profile(self, name: str, config: ConnectorConfig) -> None:
        data = self._load_file()
        profile: dict[str, Any] = {"connector_type": config.connector_type}
        if config.connection_string:
            profile["connection_string"] = config.connection_string
        if config.host:
            profile["host"] = config.host
        if config.port:
            profile["port"] = config.port
        if config.database:
            profile["database"] = config.database
        if config.options:
            profile["options"] = config.options
        if config.credentials:
            cred: dict[str, Any] = {}
            for field_name in ("profile", "env_var", "aws_secret", "azure_vault"):
                val = getattr(config.credentials, field_name, None)
                if val:
                    cred[field_name] = val
            if cred:
                profile["credentials"] = cred
        data["profiles"][name] = profile
        self._save_file(data)
        logger.info("Saved connection profile: %s", name)

    def load_profile(self, name: str) -> ConnectorConfig:
        data = self._load_file()
        if name not in data["profiles"]:
            raise KeyError(f"Connection profile '{name}' not found. Available: {list(data['profiles'].keys())}")
        p = data["profiles"][name]
        cred = None
        if "credentials" in p:
            cred = CredentialConfig(**p["credentials"])
        return ConnectorConfig(
            connector_type=p["connector_type"],
            connection_string=p.get("connection_string"),
            host=p.get("host"),
            port=p.get("port"),
            database=p.get("database"),
            credentials=cred,
            options=p.get("options", {}),
        )

    def remove_profile(self, name: str) -> None:
        data = self._load_file()
        data["profiles"].pop(name, None)
        self._save_file(data)

    def list_profiles(self) -> list[str]:
        data = self._load_file()
        return list(data["profiles"].keys())
```

**Step 3: Run tests, commit**

Run: `py -m pytest tests/connectors/test_manager.py -v`

```bash
git add adaptron/connectors/manager.py tests/connectors/test_manager.py
git commit -m "feat: connection manager with YAML profile save/load/remove"
```

---

### Task 5: PostgreSQL connector

**Files:**
- Create: `adaptron/connectors/postgresql.py`
- Create: `tests/connectors/test_postgresql.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_postgresql.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from adaptron.connectors.postgresql import PostgreSQLConnector
from adaptron.connectors.models import ConnectorConfig, FetchQuery


def test_registered_as_connector_postgresql():
    from adaptron.core.registry import global_registry
    plugin = global_registry.get("connector", "postgresql")
    assert plugin is PostgreSQLConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    connector = PostgreSQLConnector()
    mock_engine = MagicMock()
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["users", "orders"]
    mock_inspector.get_columns.side_effect = [
        [{"name": "id", "type": MagicMock(__str__=lambda s: "INTEGER"), "nullable": False, "primary_key": True}],
        [{"name": "id", "type": MagicMock(__str__=lambda s: "INTEGER"), "nullable": False, "primary_key": True}],
    ]
    mock_inspector.get_pk_constraint.side_effect = [
        {"constrained_columns": ["id"]},
        {"constrained_columns": ["id"]},
    ]
    mock_inspector.get_foreign_keys.side_effect = [[], []]
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchmany.return_value = []
    mock_result.keys.return_value = ["id"]
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch("adaptron.connectors.postgresql.create_engine", return_value=mock_engine), \
         patch("adaptron.connectors.postgresql.inspect", return_value=mock_inspector):
        config = ConnectorConfig(
            connector_type="postgresql",
            connection_string="postgresql://user:pass@localhost/testdb",
        )
        await connector.connect(config)
        schema = await connector.discover_schema()

    assert schema.connector_type == "postgresql"
    assert len(schema.collections) == 2
    assert schema.collections[0].name == "users"


@pytest.mark.asyncio
async def test_fetch_mocked():
    connector = PostgreSQLConnector()
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
    mock_result.keys.return_value = ["id", "name"]
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch("adaptron.connectors.postgresql.create_engine", return_value=mock_engine):
        config = ConnectorConfig(
            connector_type="postgresql",
            connection_string="postgresql://user:pass@localhost/testdb",
        )
        await connector.connect(config)
        connector._engine = mock_engine
        docs = await connector.fetch(FetchQuery(collection="users"))

    assert len(docs) == 2
    assert "Alice" in docs[0].content
```

**Step 2: Implement**

```python
# adaptron/connectors/postgresql.py
from __future__ import annotations

import logging
from typing import Any

from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import (
    CollectionSchema, ConnectorConfig, DataSchema, FetchQuery, FieldInfo,
)
from adaptron.core.registry import register_plugin
from adaptron.ingest.models import RawDocument

logger = logging.getLogger(__name__)


@register_plugin("connector", "postgresql")
class PostgreSQLConnector(BaseConnector):
    def __init__(self) -> None:
        self._engine = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        from sqlalchemy import create_engine
        conn_str = config.connection_string or self._build_conn_str(config)
        self._engine = create_engine(conn_str)
        self._config = config
        logger.info("Connected to PostgreSQL: %s", config.database or conn_str.split("@")[-1] if conn_str else "")

    def _build_conn_str(self, config: ConnectorConfig) -> str:
        user = config.credentials.username if config.credentials else ""
        pwd = config.credentials.password if config.credentials else ""
        host = config.host or "localhost"
        port = config.port or 5432
        db = config.database or ""
        auth = f"{user}:{pwd}@" if user else ""
        return f"postgresql://{auth}{host}:{port}/{db}"

    async def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        from sqlalchemy import text
        if not self._engine:
            raise RuntimeError("Not connected. Call connect() first.")
        sql = query.raw_query or self._build_select(query)
        with self._engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            col_names = list(result.keys())
        documents = []
        for row in rows:
            row_dict = dict(zip(col_names, row))
            content = ", ".join(f"{k}={v}" for k, v in row_dict.items())
            documents.append(RawDocument(
                content=content,
                metadata={"table": query.collection, "columns": col_names, "row": row_dict},
                source_ref=f"postgresql://{query.collection}",
            ))
        return documents

    def _build_select(self, query: FetchQuery) -> str:
        cols = ", ".join(query.columns) if query.columns else "*"
        sql = f'SELECT {cols} FROM "{query.collection}"'
        if query.filters:
            where_clauses = [f'"{k}" = \'{v}\'' for k, v in query.filters.items()]
            sql += " WHERE " + " AND ".join(where_clauses)
        if query.limit:
            sql += f" LIMIT {query.limit}"
        if query.offset:
            sql += f" OFFSET {query.offset}"
        return sql

    async def discover_schema(self) -> DataSchema:
        from sqlalchemy import inspect, text
        if not self._engine:
            raise RuntimeError("Not connected. Call connect() first.")
        inspector = inspect(self._engine)
        collections = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            pk = inspector.get_pk_constraint(table_name)
            pk_cols = pk.get("constrained_columns", []) if pk else []
            fks = inspector.get_foreign_keys(table_name)
            fields = []
            for col in columns:
                fields.append(FieldInfo(
                    name=col["name"],
                    data_type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    is_primary_key=col["name"] in pk_cols,
                    sample_values=[],
                ))
            # Fetch sample values
            try:
                with self._engine.connect() as conn:
                    result = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT 5'))
                    sample_rows = result.fetchmany(5)
                    keys = list(result.keys())
                for field_info in fields:
                    idx = keys.index(field_info.name) if field_info.name in keys else -1
                    if idx >= 0:
                        field_info.sample_values = [row[idx] for row in sample_rows if row[idx] is not None][:3]
            except Exception:
                pass
            relationships = []
            for fk in fks:
                for cc, rc in zip(fk["constrained_columns"], fk.get("referred_columns", [])):
                    relationships.append(f"{table_name}.{cc} -> {fk['referred_table']}.{rc}")
            collections.append(CollectionSchema(
                name=table_name,
                fields=fields,
                relationships=relationships,
                source_type="table",
            ))
        db_name = self._config.database or "" if self._config else ""
        return DataSchema(connector_type="postgresql", database=db_name, collections=collections)
```

**Step 3: Run tests, commit**

Run: `py -m pytest tests/connectors/test_postgresql.py -v`

```bash
git add adaptron/connectors/postgresql.py tests/connectors/test_postgresql.py
git commit -m "feat: PostgreSQL connector with schema discovery and fetch"
```

---

### Task 6: MySQL connector

**Files:**
- Create: `adaptron/connectors/mysql.py`
- Create: `tests/connectors/test_mysql.py`

Same pattern as PostgreSQL but with `mysql+pymysql://` connection string and `@register_plugin("connector", "mysql")`. Uses SQLAlchemy — the implementation is nearly identical to PostgreSQL, with `_build_conn_str` using port 3306 default and `mysql+pymysql://` prefix. Tests follow the same mock pattern as Task 5 with MySQL-specific config.

**Step 1: Write tests** (registration + mocked discover_schema + mocked fetch)
**Step 2: Implement** (copy PostgreSQL pattern, adjust defaults)
**Step 3: Run tests, commit**

```bash
git commit -m "feat: MySQL connector with schema discovery and fetch"
```

---

### Task 7: SQLite connector

**Files:**
- Create: `adaptron/connectors/sqlite.py`
- Create: `tests/connectors/test_sqlite.py`

Same SQLAlchemy pattern as PostgreSQL. `sqlite:///path/to/db.sqlite3` connection string. `@register_plugin("connector", "sqlite")`. Tests can use a real in-memory SQLite database (`sqlite:///:memory:`) for integration testing — no mocks needed.

**Step 1: Write tests** (registration + real SQLite in-memory integration test with schema discovery and fetch)
**Step 2: Implement**
**Step 3: Run tests, commit**

```bash
git commit -m "feat: SQLite connector with schema discovery and fetch"
```

---

### Task 8: MSSQL and Oracle connectors

**Files:**
- Create: `adaptron/connectors/mssql.py`
- Create: `adaptron/connectors/oracle.py`
- Create: `tests/connectors/test_mssql.py`
- Create: `tests/connectors/test_oracle.py`

Both follow the SQLAlchemy pattern. MSSQL uses `mssql+pyodbc://`, Oracle uses `oracle+oracledb://`. Tests mock SQLAlchemy like Task 5. 2 tests each (registration + mocked schema discovery).

```bash
git commit -m "feat: MSSQL and Oracle connectors"
```

---

### Task 9: MongoDB connector

**Files:**
- Create: `adaptron/connectors/mongodb.py`
- Create: `tests/connectors/test_mongodb.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_mongodb.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from adaptron.connectors.mongodb import MongoDBConnector
from adaptron.connectors.models import ConnectorConfig, FetchQuery


def test_registered_as_connector_mongodb():
    from adaptron.core.registry import global_registry
    plugin = global_registry.get("connector", "mongodb")
    assert plugin is MongoDBConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    connector = MongoDBConnector()
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_db.list_collection_names.return_value = ["users", "orders"]
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"_id": "abc", "name": "Alice", "email": "a@b.com"}
    mock_collection.estimated_document_count.return_value = 100
    mock_collection.find.return_value.limit.return_value = [
        {"_id": "abc", "name": "Alice", "email": "a@b.com"}
    ]
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    mock_client.__getitem__ = MagicMock(return_value=mock_db)

    with patch("adaptron.connectors.mongodb.MongoClient", return_value=mock_client):
        config = ConnectorConfig(
            connector_type="mongodb",
            connection_string="mongodb://localhost:27017",
            database="testdb",
        )
        await connector.connect(config)
        schema = await connector.discover_schema()

    assert schema.connector_type == "mongodb"
    assert len(schema.collections) == 2


@pytest.mark.asyncio
async def test_fetch_mocked():
    connector = MongoDBConnector()
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.limit.return_value = [
        {"_id": "1", "name": "Alice", "age": 30},
        {"_id": "2", "name": "Bob", "age": 25},
    ]
    mock_collection.find.return_value = mock_cursor
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    mock_client.__getitem__ = MagicMock(return_value=mock_db)

    with patch("adaptron.connectors.mongodb.MongoClient", return_value=mock_client):
        config = ConnectorConfig(
            connector_type="mongodb",
            connection_string="mongodb://localhost:27017",
            database="testdb",
        )
        await connector.connect(config)
        docs = await connector.fetch(FetchQuery(collection="users", limit=10))

    assert len(docs) == 2
    assert "Alice" in docs[0].content
```

**Step 2: Implement**

```python
# adaptron/connectors/mongodb.py
from __future__ import annotations

import json
import logging
from typing import Any

from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import (
    CollectionSchema, ConnectorConfig, DataSchema, FetchQuery, FieldInfo,
)
from adaptron.core.registry import register_plugin
from adaptron.ingest.models import RawDocument

logger = logging.getLogger(__name__)

_MONGO_TYPE_MAP = {
    str: "string", int: "integer", float: "float", bool: "boolean",
    list: "json", dict: "json",
}


@register_plugin("connector", "mongodb")
class MongoDBConnector(BaseConnector):
    def __init__(self) -> None:
        self._client = None
        self._db = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            from pymongo import MongoClient
        except ImportError:
            raise RuntimeError("pymongo is required. Install with: pip install pymongo")
        self._client = MongoClient(config.connection_string or "mongodb://localhost:27017")
        self._db = self._client[config.database or "test"]
        self._config = config
        logger.info("Connected to MongoDB: %s", config.database)

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if not self._db:
            raise RuntimeError("Not connected. Call connect() first.")
        collection = self._db[query.collection]
        filters = query.filters or {}
        projection = {c: 1 for c in query.columns} if query.columns else None
        cursor = collection.find(filters, projection)
        if query.limit:
            cursor = cursor.limit(query.limit)
        if query.offset:
            cursor = cursor.skip(query.offset)
        documents = []
        for doc in cursor:
            doc_serializable = {k: str(v) for k, v in doc.items()}
            content = json.dumps(doc_serializable, default=str)
            documents.append(RawDocument(
                content=content,
                metadata={"collection": query.collection, "document": doc_serializable},
                source_ref=f"mongodb://{query.collection}",
            ))
        return documents

    async def discover_schema(self) -> DataSchema:
        if not self._db:
            raise RuntimeError("Not connected. Call connect() first.")
        collections = []
        for coll_name in self._db.list_collection_names():
            coll = self._db[coll_name]
            sample = coll.find_one()
            count = coll.estimated_document_count()
            fields = []
            if sample:
                for key, value in sample.items():
                    py_type = type(value)
                    data_type = _MONGO_TYPE_MAP.get(py_type, "string")
                    samples = []
                    try:
                        for s in coll.find().limit(3):
                            if key in s and s[key] is not None:
                                samples.append(str(s[key]))
                    except Exception:
                        pass
                    fields.append(FieldInfo(
                        name=key,
                        data_type=data_type,
                        is_primary_key=(key == "_id"),
                        sample_values=samples[:3],
                    ))
            collections.append(CollectionSchema(
                name=coll_name, fields=fields, row_count=count, source_type="collection",
            ))
        db_name = self._config.database or "" if self._config else ""
        return DataSchema(connector_type="mongodb", database=db_name, collections=collections)
```

**Step 3: Run tests, commit**

Run: `py -m pytest tests/connectors/test_mongodb.py -v`

```bash
git add adaptron/connectors/mongodb.py tests/connectors/test_mongodb.py
git commit -m "feat: MongoDB connector with schema discovery and fetch"
```

---

### Task 10: Redis connector

**Files:**
- Create: `adaptron/connectors/redis_conn.py`
- Create: `tests/connectors/test_redis_conn.py`

Registered as `@register_plugin("connector", "redis")`. Uses `redis-py`. Schema discovery scans key patterns (SCAN). Fetch retrieves key-value pairs as RawDocuments. 3 tests: registration, mocked discover_schema, mocked fetch.

```bash
git commit -m "feat: Redis connector with key scanning and fetch"
```

---

### Task 11: Elasticsearch connector

**Files:**
- Create: `adaptron/connectors/elasticsearch.py`
- Create: `tests/connectors/test_elasticsearch.py`

Registered as `@register_plugin("connector", "elasticsearch")`. Uses `elasticsearch-py`. Schema discovery reads index mappings. Fetch uses scroll/search API. 3 tests: registration, mocked discover_schema, mocked fetch.

```bash
git commit -m "feat: Elasticsearch connector with index mapping discovery"
```

---

### Task 12: DynamoDB connector

**Files:**
- Create: `adaptron/connectors/dynamodb.py`
- Create: `tests/connectors/test_dynamodb.py`

Registered as `@register_plugin("connector", "dynamodb")`. Uses `boto3`. Schema discovery reads table description + scan sample. Fetch uses scan/query API. 3 tests with mocked boto3.

```bash
git commit -m "feat: DynamoDB connector with table scanning"
```

---

### Task 13: Cassandra connector

**Files:**
- Create: `adaptron/connectors/cassandra.py`
- Create: `tests/connectors/test_cassandra.py`

Registered as `@register_plugin("connector", "cassandra")`. Uses `cassandra-driver`. Schema discovery reads keyspace metadata. Fetch uses CQL. 3 tests with mocked driver.

```bash
git commit -m "feat: Cassandra connector with CQL support"
```

---

### Task 14: BigQuery connector

**Files:**
- Create: `adaptron/connectors/bigquery.py`
- Create: `tests/connectors/test_bigquery.py`

Registered as `@register_plugin("connector", "bigquery")`. Uses `google-cloud-bigquery`. Schema discovery lists tables in dataset. Fetch runs SQL via BigQuery client. 3 tests with mocked client.

```bash
git commit -m "feat: BigQuery connector with dataset schema discovery"
```

---

### Task 15: Snowflake connector

**Files:**
- Create: `adaptron/connectors/snowflake.py`
- Create: `tests/connectors/test_snowflake.py`

Registered as `@register_plugin("connector", "snowflake")`. Uses `snowflake-connector-python`. Schema discovery via `SHOW TABLES` + `DESCRIBE TABLE`. Fetch runs SQL. 3 tests with mocked connector.

```bash
git commit -m "feat: Snowflake connector with warehouse support"
```

---

### Task 16: Redshift connector

**Files:**
- Create: `adaptron/connectors/redshift.py`
- Create: `tests/connectors/test_redshift.py`

Registered as `@register_plugin("connector", "redshift")`. Uses SQLAlchemy with `redshift+redshift_connector://` dialect. Same pattern as PostgreSQL. 2 tests (registration + mocked schema).

```bash
git commit -m "feat: Redshift connector via SQLAlchemy"
```

---

### Task 17: REST API connector

**Files:**
- Create: `adaptron/connectors/rest_api.py`
- Create: `tests/connectors/test_rest_api.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_rest_api.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from adaptron.connectors.rest_api import RESTAPIConnector
from adaptron.connectors.models import ConnectorConfig, FetchQuery


def test_registered_as_connector_rest_api():
    from adaptron.core.registry import global_registry
    plugin = global_registry.get("connector", "rest_api")
    assert plugin is RESTAPIConnector


@pytest.mark.asyncio
async def test_fetch_json_api():
    connector = RESTAPIConnector()
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": 1, "title": "Post 1", "body": "Content 1"},
        {"id": 2, "title": "Post 2", "body": "Content 2"},
    ]
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("adaptron.connectors.rest_api.httpx.AsyncClient", return_value=mock_client):
        config = ConnectorConfig(
            connector_type="rest_api",
            options={"base_url": "https://api.example.com", "headers": {"Authorization": "Bearer token"}},
        )
        await connector.connect(config)
        docs = await connector.fetch(FetchQuery(collection="/posts"))

    assert len(docs) == 2
    assert "Post 1" in docs[0].content


@pytest.mark.asyncio
async def test_discover_schema_from_sample():
    connector = RESTAPIConnector()
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": 1, "name": "Alice", "active": True}]
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("adaptron.connectors.rest_api.httpx.AsyncClient", return_value=mock_client):
        config = ConnectorConfig(
            connector_type="rest_api",
            options={
                "base_url": "https://api.example.com",
                "endpoints": ["/users"],
            },
        )
        await connector.connect(config)
        schema = await connector.discover_schema()

    assert schema.connector_type == "rest_api"
    assert len(schema.collections) == 1
    assert schema.collections[0].name == "/users"
```

**Step 2: Implement** — uses `httpx.AsyncClient` for HTTP requests. `discover_schema()` fetches each endpoint, infers field types from JSON response. `fetch()` GETs the endpoint and converts each JSON object to a RawDocument.

**Step 3: Run tests, commit**

```bash
git commit -m "feat: REST API connector with JSON inference and fetch"
```

---

### Task 18: S3 connector

**Files:**
- Create: `adaptron/connectors/s3.py`
- Create: `tests/connectors/test_s3.py`

Registered as `@register_plugin("connector", "s3")`. Uses `boto3`. Lists objects in bucket/prefix, reads CSV/JSON/text files. Schema discovery lists files with types. Fetch downloads and parses files. 3 tests with mocked boto3.

```bash
git commit -m "feat: S3 connector for CSV/JSON/text file ingestion"
```

---

### Task 19: Kafka streaming connector

**Files:**
- Create: `adaptron/connectors/kafka.py`
- Create: `tests/connectors/test_kafka.py`

Registered as `@register_plugin("connector", "kafka")`. Uses `confluent-kafka`. Implements `stream()` as async generator. `supports_streaming()` returns True. `discover_schema()` reads topic metadata. 3 tests: registration, supports_streaming, mocked consume.

```bash
git commit -m "feat: Kafka streaming connector with async consumer"
```

---

## Phase 2: Data Cleaning & Augmentation

### Task 20: Data cleaner

**Files:**
- Create: `adaptron/connectors/cleaner.py`
- Create: `tests/connectors/test_cleaner.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_cleaner.py
from adaptron.connectors.cleaner import DataCleaner, CleanConfig
from adaptron.ingest.models import RawDocument


def test_remove_empty_documents():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Hello world", source_ref="a.txt"),
        RawDocument(content="", source_ref="b.txt"),
        RawDocument(content="   ", source_ref="c.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig(remove_empty=True))
    assert len(result.cleaned) == 1
    assert result.removed_count == 2


def test_dedup_exact():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Same content here", source_ref="a.txt"),
        RawDocument(content="Same content here", source_ref="b.txt"),
        RawDocument(content="Different content", source_ref="c.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig(dedup=True))
    assert len(result.cleaned) == 2
    assert result.dedup_count == 1


def test_normalize_whitespace():
    cleaner = DataCleaner()
    docs = [RawDocument(content="Hello   world\n\n\nfoo   bar", source_ref="a.txt")]
    result = cleaner.clean(docs, CleanConfig(normalize_whitespace=True, remove_empty=False, dedup=False))
    assert "  " not in result.cleaned[0].content


def test_min_content_length():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Short", source_ref="a.txt"),
        RawDocument(content="This is a sufficiently long document", source_ref="b.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig(min_content_length=10, dedup=False))
    assert len(result.cleaned) == 1


def test_fix_encoding():
    cleaner = DataCleaner()
    docs = [RawDocument(content="caf\xe9 na\xefve", source_ref="a.txt")]
    result = cleaner.clean(docs, CleanConfig(fix_encoding=True, dedup=False, remove_empty=False))
    assert len(result.cleaned) == 1


def test_strip_html():
    cleaner = DataCleaner()
    docs = [RawDocument(content="<p>Hello <b>world</b></p>", source_ref="a.txt")]
    result = cleaner.clean(docs, CleanConfig(strip_html=True, dedup=False, remove_empty=False))
    assert "<p>" not in result.cleaned[0].content
    assert "Hello" in result.cleaned[0].content


def test_clean_report():
    cleaner = DataCleaner()
    docs = [
        RawDocument(content="Good content", source_ref="a.txt"),
        RawDocument(content="", source_ref="b.txt"),
    ]
    result = cleaner.clean(docs, CleanConfig())
    assert "removed_empty" in result.report
```

**Step 2: Implement** the `DataCleaner` with sequential pipeline: fix_encoding -> strip_html -> normalize_whitespace -> remove_empty -> min_content_length -> dedup. Each step is tracked in the report.

**Step 3: Run tests, commit**

```bash
git commit -m "feat: data cleaner with dedup, encoding fix, HTML strip, whitespace normalization"
```

---

### Task 21: Data augmenter

**Files:**
- Create: `adaptron/connectors/augmenter.py`
- Create: `tests/connectors/test_augmenter.py`

**Step 1: Write failing tests**

```python
# tests/connectors/test_augmenter.py
from adaptron.connectors.augmenter import DataAugmenter, AugmentConfig


def test_synonym_swap():
    augmenter = DataAugmenter()
    dataset = [{"instruction": "Explain machine learning", "response": "ML is..."}]
    result = augmenter.augment(dataset, AugmentConfig(synonym_swap=True, target_multiplier=2.0))
    assert len(result) >= 2  # original + augmented


def test_preserve_originals():
    augmenter = DataAugmenter()
    dataset = [{"instruction": "Hello", "response": "Hi"}]
    result = augmenter.augment(dataset, AugmentConfig(synonym_swap=True, preserve_originals=True))
    assert dataset[0] in result


def test_no_augmentation_returns_original():
    augmenter = DataAugmenter()
    dataset = [{"instruction": "Test", "response": "OK"}]
    result = augmenter.augment(dataset, AugmentConfig())
    assert result == dataset
```

**Step 2: Implement** the `DataAugmenter` with synonym_swap (using a small built-in synonym dict) and balance_categories. Paraphrase and back_translate are stubs that log warnings (require external models).

**Step 3: Run tests, commit**

```bash
git commit -m "feat: data augmenter with synonym swap and category balancing"
```

---

## Phase 3: Smart Synthesis

### Task 22: QA pair synthesizer

**Files:**
- Create: `adaptron/synthesize/qa.py`
- Create: `tests/synthesize/test_qa.py`

Registered as `@register_plugin("synthesizer", "qa")`. Takes chunks and generates question/answer pairs using templates like "What is {topic}?" -> chunk content. 2 tests: registration + generate.

```bash
git commit -m "feat: QA pair synthesizer"
```

---

### Task 23: Chat/conversation synthesizer

**Files:**
- Create: `adaptron/synthesize/chat.py`
- Create: `tests/synthesize/test_chat.py`

Registered as `@register_plugin("synthesizer", "chat")`. Converts chunks into multi-turn conversation format with system/user/assistant roles. 2 tests.

```bash
git commit -m "feat: chat conversation synthesizer"
```

---

### Task 24: DPO preference pair synthesizer

**Files:**
- Create: `adaptron/synthesize/dpo.py`
- Create: `tests/synthesize/test_dpo.py`

Registered as `@register_plugin("synthesizer", "dpo")`. Generates preference pairs: chosen (good response from chunk) and rejected (degraded/generic response). 2 tests.

```bash
git commit -m "feat: DPO preference pair synthesizer"
```

---

### Task 25: Text-to-SQL synthesizer

**Files:**
- Create: `adaptron/synthesize/text2sql.py`
- Create: `tests/synthesize/test_text2sql.py`

Registered as `@register_plugin("synthesizer", "text2sql")`. Takes schema descriptions and generates natural language question -> SQL query pairs. 2 tests.

```bash
git commit -m "feat: text-to-SQL pair synthesizer"
```

---

### Task 26: Corpus synthesizer (for CPT)

**Files:**
- Create: `adaptron/synthesize/corpus.py`
- Create: `tests/synthesize/test_corpus.py`

Registered as `@register_plugin("synthesizer", "corpus")`. Concatenates chunks into clean raw text documents for continued pre-training. 2 tests.

```bash
git commit -m "feat: corpus synthesizer for continued pre-training"
```

---

### Task 27: Training format auto-detector

**Files:**
- Create: `adaptron/synthesize/detector.py`
- Create: `tests/synthesize/test_detector.py`

**Step 1: Write failing tests**

```python
# tests/synthesize/test_detector.py
from adaptron.synthesize.detector import TrainingFormatDetector, FormatRecommendation
from adaptron.connectors.models import DataSchema, CollectionSchema, FieldInfo


def test_detect_qa_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="faq",
            fields=[
                FieldInfo(name="question", data_type="string"),
                FieldInfo(name="answer", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "qa"
    assert result.confidence >= 0.8


def test_detect_instruction_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="training",
            fields=[
                FieldInfo(name="instruction", data_type="string"),
                FieldInfo(name="response", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "instruction"


def test_detect_dpo_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="prefs",
            fields=[
                FieldInfo(name="prompt", data_type="string"),
                FieldInfo(name="chosen", data_type="string"),
                FieldInfo(name="rejected", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "dpo"


def test_detect_chat_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="mongodb", database="test",
        collections=[CollectionSchema(
            name="messages",
            fields=[
                FieldInfo(name="role", data_type="string"),
                FieldInfo(name="content", data_type="string"),
                FieldInfo(name="session_id", data_type="string"),
            ],
            source_type="collection",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "chat"


def test_detect_text2sql_complex_schema():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[
            CollectionSchema(name="users", fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="name", data_type="string"),
            ], relationships=["orders.user_id -> users.id"], source_type="table"),
            CollectionSchema(name="orders", fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="user_id", data_type="integer"),
                FieldInfo(name="total", data_type="float"),
            ], source_type="table"),
            CollectionSchema(name="products", fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="name", data_type="string"),
                FieldInfo(name="price", data_type="float"),
            ], source_type="table"),
        ],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "text2sql"


def test_detect_corpus_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="articles",
            fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="title", data_type="string"),
                FieldInfo(name="body", data_type="string"),
                FieldInfo(name="published_at", data_type="datetime"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "corpus"


def test_detect_low_confidence():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="redis", database="0",
        collections=[CollectionSchema(
            name="keys",
            fields=[FieldInfo(name="key", data_type="string"), FieldInfo(name="value", data_type="string")],
            source_type="keyspace",
        )],
    )
    result = detector.detect(schema, [])
    assert result.confidence < 0.8
    assert result.reasoning != ""


def test_format_recommendation_has_column_mapping():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="faq",
            fields=[
                FieldInfo(name="question", data_type="string"),
                FieldInfo(name="answer", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert "question" in result.column_mapping or "answer" in result.column_mapping
```

**Step 2: Implement** the rule-based `TrainingFormatDetector` with heuristics from the design doc. Column name matching, relationship analysis, and field type inference.

**Step 3: Run tests, commit**

```bash
git commit -m "feat: training format auto-detector with heuristic rules"
```

---

### Task 28: Mapping validator

**Files:**
- Create: `adaptron/synthesize/validator.py`
- Create: `tests/synthesize/test_validator.py`

**Step 1: Write failing tests**

```python
# tests/synthesize/test_validator.py
from adaptron.synthesize.validator import MappingValidator, ValidationReport
from adaptron.ingest.models import RawDocument


def test_validate_all_valid():
    validator = MappingValidator()
    mapping = {"question": "input", "answer": "output"}
    data = [
        RawDocument(content="", metadata={"row": {"question": "What is AI?", "answer": "AI is..."}}),
        RawDocument(content="", metadata={"row": {"question": "What is ML?", "answer": "ML is..."}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert report.coverage_pct == 100.0
    assert report.approved is True
    assert report.invalid_records == 0


def test_validate_with_null_values():
    validator = MappingValidator()
    mapping = {"question": "input", "answer": "output"}
    data = [
        RawDocument(content="", metadata={"row": {"question": "What?", "answer": "Something"}}),
        RawDocument(content="", metadata={"row": {"question": None, "answer": "Something"}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert report.invalid_records == 1
    assert report.coverage_pct == 50.0
    assert report.approved is False


def test_validate_nonexistent_column():
    validator = MappingValidator()
    mapping = {"nonexistent": "input"}
    data = [
        RawDocument(content="", metadata={"row": {"question": "What?", "answer": "Something"}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert report.invalid_records == 1
    assert len(report.errors) > 0


def test_validate_high_coverage_needs_confirmation():
    validator = MappingValidator()
    mapping = {"question": "input", "answer": "output"}
    data = [
        RawDocument(content="", metadata={"row": {"question": f"Q{i}", "answer": f"A{i}"}})
        for i in range(99)
    ] + [
        RawDocument(content="", metadata={"row": {"question": None, "answer": "A100"}}),
    ]
    report = validator.validate(mapping, data, "qa")
    assert 99.0 <= report.coverage_pct < 100.0
    assert report.approved is True  # 99% is auto-approved with notification
```

**Step 2: Implement** the `MappingValidator` with per-record validation, null checking, type consistency, and coverage calculation. Approval gates: 100% auto, 99-99.9% approved with notification, 95-99% needs explicit approval, <95% blocked.

**Step 3: Run tests, commit**

```bash
git commit -m "feat: mapping validator with coverage-based approval gates"
```

---

### Task 29: AutoSynthesizer

**Files:**
- Create: `adaptron/synthesize/auto.py`
- Create: `tests/synthesize/test_auto.py`

Registered as `@register_plugin("synthesizer", "auto")`. Ties together `TrainingFormatDetector` and dispatches to the correct synthesizer. Falls back to `TemplateInstructionGenerator` if no format detected. 3 tests: auto-detect dispatches correctly, fallback to instruction, low confidence returns recommendation.

```bash
git commit -m "feat: AutoSynthesizer with format detection and dispatch"
```

---

## Phase 4: CLI & API Integration

### Task 30: CLI connect commands

**Files:**
- Modify: `adaptron/cli/main.py`
- Create: `tests/cli/test_connect.py`

Add `connect`, `connect_list`, `connect_test`, `connect_schema`, `connect_remove` commands to the Typer CLI. The interactive wizard guides users through data source selection, connection, schema discovery, and profile saving.

3 tests: connect_list empty, connect_list with profile, connect_remove.

```bash
git commit -m "feat: CLI connect commands for data source management"
```

---

### Task 31: API connector routes

**Files:**
- Create: `adaptron/api/routes/connectors.py`
- Modify: `adaptron/api/main.py` (add router)
- Create: `tests/api/test_connectors.py`

Add routes:
- `GET /api/connectors/types`
- `POST /api/connectors/test`
- `POST /api/connectors/discover`
- `POST /api/connectors/preview`
- `POST /api/connectors/profiles` (save)
- `GET /api/connectors/profiles` (list)
- `POST /api/connectors/generate`

3 tests with FastAPI TestClient: list types, list profiles, test connection (mocked).

```bash
git commit -m "feat: API routes for connector management and data generation"
```

---

## Phase 5: Scheduling & Streaming

### Task 32: Ingestion scheduler

**Files:**
- Create: `adaptron/connectors/scheduler.py`
- Create: `tests/connectors/test_scheduler.py`

Implement `IngestionScheduler` with `add_schedule`, `remove_schedule`, `list_schedules`, `run_now`. Schedules are stored in a YAML file. Uses APScheduler for cron-based execution. Incremental mode tracks checkpoint values.

3 tests: add/list schedule, remove schedule, incremental checkpoint tracking.

```bash
git commit -m "feat: ingestion scheduler with cron and incremental support"
```

---

### Task 33: Stream processor

**Files:**
- Create: `adaptron/connectors/stream.py`
- Create: `tests/connectors/test_stream.py`

Implement `StreamProcessor` that consumes from streaming connectors (Kafka), buffers into configurable batch sizes, and synthesizes training data incrementally.

2 tests: batch buffering, stop/start lifecycle.

```bash
git commit -m "feat: stream processor with batch buffering for real-time ingestion"
```

---

### Task 34: Schedule CLI and API routes

**Files:**
- Modify: `adaptron/cli/main.py` (add schedule commands)
- Create: `adaptron/api/routes/schedules.py`
- Modify: `adaptron/api/main.py` (add router)
- Create: `tests/cli/test_schedule.py`
- Create: `tests/api/test_schedules.py`

CLI: `adaptron schedule add`, `schedule list`, `schedule run`.
API: `GET /api/schedules`, `POST /api/schedules`, `DELETE /api/schedules/{id}`.

2 tests each for CLI and API.

```bash
git commit -m "feat: schedule CLI commands and API routes"
```

---

## Phase 6: Pipeline Integration & pyproject.toml

### Task 35: Update PipelineFactory and pyproject.toml

**Files:**
- Modify: `adaptron/core/factory.py` (add CleanStage, use AutoSynthesizer)
- Modify: `adaptron/core/config.py` (add connector_profiles, clean_config, augment_config fields)
- Modify: `pyproject.toml` (add connectors dependency group)
- Create: `tests/connectors/test_pipeline_integration.py`

Add a `connectors` optional dependency group to `pyproject.toml`:
```toml
connectors = [
    "pymongo>=4.6",
    "redis>=5.0",
    "elasticsearch>=8.12",
    "boto3>=1.34",
    "cassandra-driver>=3.29",
    "google-cloud-bigquery>=3.17",
    "snowflake-connector-python>=3.7",
    "confluent-kafka>=2.3",
    "httpx>=0.27",
    "apscheduler>=3.10",
]
```

Update `all` group to include `connectors`.

Add `CleanStage` between Understand and Synthesize in `PipelineFactory`. Make `SynthesizeStage` use `AutoSynthesizer` when available, falling back to `TemplateInstructionGenerator`.

2 tests: pipeline with clean stage, pipeline with auto synthesizer.

```bash
git commit -m "feat: pipeline integration with CleanStage, AutoSynthesizer, and connectors deps"
```

---

### Task 36: Integration test for connector pipeline

**Files:**
- Create: `tests/integration/test_connector_e2e.py`

End-to-end test: create a SQLite database with test data, connect via SQLiteConnector, discover schema, auto-detect format, clean data, synthesize training data. Verify the full flow produces valid training records.

```bash
git commit -m "test: end-to-end connector pipeline integration test"
```
