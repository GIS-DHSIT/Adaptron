"""Tests for the SchemaInferenceAnalyzer."""

from adaptron.ingest.models import RawDocument
from adaptron.understand.schema import SchemaInferenceAnalyzer


def _make_sql_doc(table_name: str, content: str) -> RawDocument:
    return RawDocument(
        content=content,
        source_ref=f"sql://{table_name}",
        metadata={"table": table_name},
    )


USERS_SCHEMA = (
    "Table: users\n"
    "Columns:\n"
    "  - id (INTEGER)\n"
    "  - name (TEXT)\n"
    "  - email (TEXT)\n"
    "Sample Data (2 rows):\n"
    "  id=1, name=Alice, email=alice@test.com\n"
    "  id=2, name=Bob, email=bob@test.com"
)

ORDERS_SCHEMA = (
    "Table: orders\n"
    "Columns:\n"
    "  - id (INTEGER)\n"
    "  - user_id (INTEGER)\n"
    "  - amount (REAL)\n"
    "Foreign Keys:\n"
    "  - ['user_id'] -> users.['id']\n"
)


def test_describe_table_basic():
    doc = _make_sql_doc("users", USERS_SCHEMA)
    analyzer = SchemaInferenceAnalyzer()
    description = analyzer.describe_table(doc)

    assert "users" in description
    assert "3 column(s)" in description
    assert "'id' (INTEGER)" in description
    assert "'name' (TEXT)" in description
    assert "'email' (TEXT)" in description


def test_describe_table_with_foreign_keys():
    doc = _make_sql_doc("orders", ORDERS_SCHEMA)
    analyzer = SchemaInferenceAnalyzer()
    description = analyzer.describe_table(doc)

    assert "orders" in description
    assert "3 column(s)" in description
    assert "Relationships:" in description
    assert "users" in description


def test_analyze_filters_sql_documents():
    sql_doc = _make_sql_doc("users", USERS_SCHEMA)
    non_sql_doc = RawDocument(
        content="Some plain text document.",
        source_ref="file://readme.txt",
    )
    analyzer = SchemaInferenceAnalyzer()
    corpus = analyzer.analyze([sql_doc, non_sql_doc])

    assert "users" in corpus.schema_descriptions
    assert len(corpus.schema_descriptions) == 1


def test_analyze_empty_documents():
    analyzer = SchemaInferenceAnalyzer()
    corpus = analyzer.analyze([])

    assert corpus.schema_descriptions == {}
    assert corpus.chunks == []
    assert corpus.entities == []


def test_analyze_multiple_sql_documents():
    users_doc = _make_sql_doc("users", USERS_SCHEMA)
    orders_doc = _make_sql_doc("orders", ORDERS_SCHEMA)
    analyzer = SchemaInferenceAnalyzer()
    corpus = analyzer.analyze([users_doc, orders_doc])

    assert "users" in corpus.schema_descriptions
    assert "orders" in corpus.schema_descriptions
    assert len(corpus.schema_descriptions) == 2
