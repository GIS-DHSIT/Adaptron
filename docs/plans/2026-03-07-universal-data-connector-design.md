# Universal Data Connector & Smart Training Data Synthesis

**Date:** 2026-03-07
**Status:** Approved

## Overview

A universal data connectivity layer for Adaptron that can plug into any type of database, API, or streaming source and automatically convert any dataset into optimized training data. Supports relational DBs, NoSQL, cloud warehouses, REST APIs, S3, and Kafka with auto-detection of the best training data format, robust LLM-assisted analysis with deterministic validation, data cleaning/augmentation, credential management, and batch/scheduled/streaming ingestion.

## Architecture

### Approach: Unified Connector Framework

A single `BaseConnector` abstract class with a standardized interface. Each connector is a plugin registered in the existing `PluginRegistry` under the `"connector"` category. A `ConnectionManager` handles credential profiles, secrets resolution, and connection pooling.

```
                    NEW                                    EXISTING
    +-----------------------------+          +------------------------------+
    |  ConnectionManager          |          |                              |
    |    +- CredentialResolver    |          |                              |
    |    +- BaseConnector(s)      |--fetch-->|  RawDocument[]               |
    |         +- discover_schema()|          |       |                      |
    |                             |          |       v                      |
    |  TrainingFormatDetector     |          |  Understand Stage            |
    |    +- MappingValidator      |          |  (chunker, entities, etc.)   |
    |                             |          |       |                      |
    |  DataCleaner               |--clean-->|       v                      |
    |                             |          |  Synthesize Stage            |
    |  New Synthesizers           |          |  (auto-detect dispatches     |
    |    +- QASynthesizer         |----------|   to correct synthesizer)    |
    |    +- ChatSynthesizer       |          |       |                      |
    |    +- DPOSynthesizer        |          |       v                      |
    |    +- Text2SQLSynthesizer   |          |  Train / Evaluate / Deploy   |
    |    +- CorpusSynthesizer     |          |                              |
    |    +- AutoSynthesizer       |          |                              |
    |                             |          |                              |
    |  IngestionScheduler         |          |                              |
    |  StreamProcessor            |          |                              |
    +-----------------------------+          +------------------------------+
```

## Components

### 1. Connector Framework (`adaptron/connectors/`)

#### BaseConnector Interface

```python
class BaseConnector(ABC):
    @abstractmethod
    async def connect(self, config: ConnectorConfig) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def fetch(self, query: FetchQuery) -> list[RawDocument]: ...

    async def stream(self, query: FetchQuery) -> AsyncIterator[RawDocument]:
        raise NotImplementedError("This connector does not support streaming")

    @abstractmethod
    async def discover_schema(self) -> DataSchema: ...

    def supports_streaming(self) -> bool:
        return False
```

#### Connectors

| Category | Connectors | Underlying Library |
|----------|-----------|-------------------|
| Relational | PostgreSQL, MySQL, MSSQL, Oracle, SQLite | SQLAlchemy |
| NoSQL | MongoDB, Redis, Elasticsearch, DynamoDB, Cassandra | PyMongo, redis-py, elasticsearch-py, boto3, cassandra-driver |
| Cloud Warehouses | BigQuery, Snowflake, Redshift | google-cloud-bigquery, snowflake-connector-python, redshift_connector |
| APIs & Streaming | REST API, S3, Kafka | httpx, boto3, confluent-kafka |

### 2. Connection Manager & Credentials (`adaptron/connectors/manager.py`, `credentials.py`)

#### ConnectorConfig

```python
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
class CredentialConfig:
    profile: str | None = None
    env_var: str | None = None
    aws_secret: str | None = None
    azure_vault: str | None = None
    username: str | None = None
    password: str | None = None
```

#### CredentialResolver

Resolves credentials in priority order:
1. Direct values (username/password) -- dev convenience
2. Environment variables
3. Named profile from `~/.adaptron/connections.yaml`
4. AWS Secrets Manager
5. Azure Key Vault

Credentials are never logged or stored in pipeline configs.

#### Profile File (`~/.adaptron/connections.yaml`)

```yaml
profiles:
  production-db:
    connector_type: postgresql
    host: db.example.com
    port: 5432
    database: myapp
    credentials:
      env_var: PROD_DB_URL

  data-lake:
    connector_type: s3
    options:
      bucket: my-training-data
      prefix: datasets/
    credentials:
      aws_secret: arn:aws:secretsmanager:us-east-1:123:secret:s3-creds
```

### 3. Schema Discovery & Data Models (`adaptron/connectors/models.py`)

```python
@dataclass
class FieldInfo:
    name: str
    data_type: str           # normalized: "string", "integer", "float", "boolean", "datetime", "json", "binary"
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

### 4. Training Format Auto-Detection (`adaptron/synthesize/auto.py`)

#### TrainingFormatDetector

```python
class TrainingFormatDetector:
    def detect(self, schema: DataSchema, samples: list[RawDocument]) -> FormatRecommendation: ...
    async def detect_with_llm(self, schema: DataSchema, samples: list[RawDocument],
                               model: str = "adaptron-default") -> FormatRecommendation: ...

@dataclass
class FormatRecommendation:
    primary_format: str
    confidence: float
    alternatives: list[str]
    column_mapping: dict[str, str]
    reasoning: str
```

#### Heuristic Rules

| Source Pattern | Detected Format | Mapping |
|---|---|---|
| Table with question/answer columns | QA pairs | question->input, answer->output |
| Table with prompt/response or instruction/output | Instruction pairs | direct mapping |
| Table with prompt/chosen/rejected | DPO preference pairs | direct mapping |
| Chat/message tables with role/content + session grouping | Conversation/chat | group by session_id |
| SQL database with complex schema + relationships | Text-to-SQL | schema->context, generate SQL pairs |
| Large text/document tables | Raw corpus (CPT) | concatenate text fields |
| REST API responses (JSON) | Instruction pairs | generate Q&A from JSON structure |
| Key-value store (Redis) | Instruction pairs | key->instruction, value->response |
| Unrecognizable pattern (confidence < 0.4) | Prompt user OR LLM analysis | -- |

### 5. Robust LLM-Assisted Analysis (Accuracy Guarantees)

**Principle: LLM suggests, never decides. 100% accuracy is non-negotiable.**

#### Validation Pipeline

```
Source Data
    |
    v
[1. Sample Extraction] -- statistically representative sample (stratified, not random)
    |
    v
[2. LLM Analysis] -- analyze sample, propose format + column mapping + reasoning
    |
    v
[3. Deterministic Validator] -- apply mapping to FULL dataset, verify:
    - No null/empty outputs
    - Type consistency
    - Coverage check (% of records successfully mapped)
    - Schema conformance
    |
    v
[4. Validation Report] -- present results to user
    |
    v
[5. User Approval Gate] -- explicit approval required
```

#### MappingValidator

```python
class MappingValidator:
    def validate(self, mapping: dict[str, str], data: list[RawDocument],
                 target_format: str) -> ValidationReport: ...

@dataclass
class ValidationReport:
    total_records: int
    valid_records: int
    invalid_records: int
    coverage_pct: float
    errors: list[ValidationError]
    warnings: list[str]
    approved: bool

@dataclass
class ValidationError:
    record_index: int
    field: str
    error_type: str
    raw_value: Any
    suggestion: str
```

#### LLM Safeguards

- Temperature 0 -- deterministic output
- Structured output -- strict JSON schema, parsed and validated
- Multiple samples -- 3 independent sample batches, cross-checked for consistency
- Confidence threshold -- if 3 analyses disagree, flag for manual review
- No hallucinated columns -- validator rejects mappings referencing non-existent columns
- Audit trail -- every analysis logged with prompt, response, and validation result

#### Approval Gates

| Coverage | Action |
|---|---|
| 100% valid | Auto-proceed with user notification |
| 99-99.9% | Show report, ask user to confirm |
| 95-99% | Show report + error details, require explicit approval |
| < 95% | Block -- require manual mapping or LLM re-analysis |

### 6. Data Cleaning & Augmentation (`adaptron/connectors/cleaner.py`, `augmenter.py`)

#### DataCleaner

```python
class DataCleaner:
    def clean(self, documents: list[RawDocument], config: CleanConfig) -> CleanResult: ...

@dataclass
class CleanConfig:
    dedup: bool = True
    dedup_threshold: float = 0.95
    fix_encoding: bool = True
    strip_html: bool = True
    normalize_whitespace: bool = True
    remove_empty: bool = True
    min_content_length: int = 10
    max_content_length: int | None = None
    custom_filters: list[Callable] = field(default_factory=list)

@dataclass
class CleanResult:
    cleaned: list[RawDocument]
    removed_count: int
    dedup_count: int
    encoding_fixes: int
    report: dict[str, Any]
```

#### DataAugmenter

```python
class DataAugmenter:
    def augment(self, dataset: list[dict], config: AugmentConfig) -> list[dict]: ...

@dataclass
class AugmentConfig:
    paraphrase: bool = False
    paraphrase_model: str | None = None
    synonym_swap: bool = False
    back_translate: bool = False
    balance_categories: bool = False
    target_multiplier: float = 2.0
    preserve_originals: bool = True
```

Cleaning runs before synthesis, augmentation runs after. Every removed record is tracked for audit.

### 7. Scheduling & Streaming (`adaptron/connectors/scheduler.py`, `stream.py`)

#### IngestionScheduler

```python
@dataclass
class ScheduleConfig:
    connector_profile: str
    query: FetchQuery
    cron: str
    mode: str                        # "full" or "incremental"
    incremental_key: str | None = None
    last_checkpoint: Any = None
    output_format: str | None = None
    enabled: bool = True

class IngestionScheduler:
    async def add_schedule(self, config: ScheduleConfig) -> str: ...
    async def remove_schedule(self, schedule_id: str) -> None: ...
    async def list_schedules(self) -> list[ScheduleConfig]: ...
    async def run_now(self, schedule_id: str) -> None: ...
    async def start(self) -> None: ...
```

#### StreamProcessor

```python
class StreamProcessor:
    def __init__(self, connector: BaseConnector, synthesizer: BaseSynthesizer): ...
    async def start(self, query: FetchQuery, batch_size: int = 100) -> None: ...
    async def stop(self) -> None: ...
```

Incremental mode tracks checkpoint column. Stream processor buffers into batches before synthesis. Schedules stored in SQLite.

### 8. New Synthesizers (`adaptron/synthesize/`)

| File | Class | Format |
|------|-------|--------|
| `qa.py` | `QASynthesizer` | Question/Answer pairs |
| `chat.py` | `ChatSynthesizer` | Multi-turn conversation format |
| `dpo.py` | `DPOSynthesizer` | Preference pairs (chosen/rejected) |
| `text2sql.py` | `Text2SQLSynthesizer` | Natural language to SQL pairs |
| `corpus.py` | `CorpusSynthesizer` | Raw text corpus for CPT |
| `auto.py` | `AutoSynthesizer` | Dispatches to correct synthesizer via FormatDetector |

### 9. CLI Commands

```
adaptron connect                    # interactive wizard
adaptron connect list               # list saved profiles
adaptron connect test <profile>     # test a saved connection
adaptron connect schema <profile>   # show discovered schema
adaptron connect remove <profile>   # delete a profile
adaptron schedule add <profile>     # set up scheduled ingestion
adaptron schedule list              # list active schedules
adaptron schedule run <id>          # trigger immediate run
```

### 10. API Routes

```
GET  /api/connectors/types              # list available connector types
POST /api/connectors/test               # test a connection config
POST /api/connectors/discover           # discover schema from a connection
POST /api/connectors/preview            # fetch sample data + auto-detect format
POST /api/connectors/profiles           # save a connection profile
GET  /api/connectors/profiles           # list saved profiles
POST /api/connectors/generate           # generate training data from connection
GET  /api/schedules                     # list schedules
POST /api/schedules                     # create schedule
DELETE /api/schedules/{id}              # remove schedule
```

### 11. Web UI Data Mapper (`web/app/connect/page.tsx`)

- Source panel: browse discovered schema (tables/collections/fields with sample values)
- Target panel: training data format fields (instruction, response, context, etc.)
- Drag-and-drop column mapping
- Live preview: 5 sample training records as you map
- Format selector: auto-detected with manual override
- Validation indicator: green/yellow/red based on coverage
- Save & generate button with progress bar

## Technology

| Component | Technology |
|-----------|-----------|
| Relational connectors | SQLAlchemy 2.0 (async) |
| MongoDB | PyMongo / motor (async) |
| Redis | redis-py (async) |
| Elasticsearch | elasticsearch-py (async) |
| DynamoDB, S3 | boto3 / aiobotocore |
| Cassandra | cassandra-driver |
| BigQuery | google-cloud-bigquery |
| Snowflake | snowflake-connector-python |
| Redshift | redshift_connector |
| REST API | httpx (async) |
| Kafka | confluent-kafka |
| Scheduling | APScheduler (cron) |
| Secrets (AWS) | boto3 Secrets Manager |
| Secrets (Azure) | azure-keyvault-secrets |
| Data cleaning | ftfy (encoding), simhash (dedup) |

## Phase 1 Priority

Database connectors first: get all DB types connected with schema discovery, credential management, and the unified connector interface. Smart synthesis auto-detection follows in Phase 2.

## Error Handling

- Connection failures: clear message with troubleshooting suggestions (firewall, credentials, driver not installed)
- Schema discovery timeout: configurable timeout with partial results
- Fetch failures: retry with exponential backoff (configurable max retries)
- Streaming disconnection: auto-reconnect with checkpoint resume
- Validation failures: detailed error report with per-record diagnostics
- Credential resolution: fail fast with clear message about which credential source was attempted
