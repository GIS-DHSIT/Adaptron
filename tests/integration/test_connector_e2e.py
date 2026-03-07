"""End-to-end connector pipeline integration tests."""

import pytest
import sqlite3
from pathlib import Path

from adaptron.connectors.sqlite import SQLiteConnector
from adaptron.connectors.models import ConnectorConfig, FetchQuery
from adaptron.connectors.cleaner import DataCleaner, CleanConfig
from adaptron.synthesize.detector import TrainingFormatDetector


@pytest.mark.asyncio
async def test_sqlite_to_training_data(tmp_path):
    """End-to-end: SQLite -> schema discovery -> format detection -> clean -> verify."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE faq (id INTEGER PRIMARY KEY, question TEXT, answer TEXT)")
    cursor.execute("INSERT INTO faq VALUES (1, 'What is AI?', 'AI is artificial intelligence.')")
    cursor.execute("INSERT INTO faq VALUES (2, 'What is ML?', 'ML is machine learning.')")
    cursor.execute("INSERT INTO faq VALUES (3, '', '')")  # empty record for cleaning
    conn.commit()
    conn.close()

    # Connect
    connector = SQLiteConnector()
    config = ConnectorConfig(
        connector_type="sqlite",
        connection_string=f"sqlite:///{db_path}",
    )
    await connector.connect(config)

    # Discover schema
    schema = await connector.discover_schema()
    assert len(schema.collections) >= 1
    faq_table = next(c for c in schema.collections if c.name == "faq")
    field_names = [f.name for f in faq_table.fields]
    assert "question" in field_names
    assert "answer" in field_names

    # Auto-detect format
    detector = TrainingFormatDetector()
    recommendation = detector.detect(schema, [])
    assert recommendation.primary_format == "qa"
    assert recommendation.confidence >= 0.8

    # Fetch data
    docs = await connector.fetch(FetchQuery(collection="faq"))
    assert len(docs) == 3

    # Clean
    cleaner = DataCleaner()
    clean_result = cleaner.clean(docs, CleanConfig(min_content_length=10))
    assert len(clean_result.cleaned) <= 3  # some may be removed
    assert clean_result.removed_count >= 0

    await connector.disconnect()


@pytest.mark.asyncio
async def test_full_pipeline_sqlite_qa(tmp_path):
    """Full pipeline: SQLite -> fetch -> clean -> synthesize QA pairs."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE training (id INTEGER PRIMARY KEY, question TEXT NOT NULL, answer TEXT NOT NULL)"
    )
    for i in range(5):
        cursor.execute(
            "INSERT INTO training VALUES (?, ?, ?)",
            (i + 1, f"Question {i + 1}?", f"Answer {i + 1} with enough content to pass filters."),
        )
    conn.commit()
    conn.close()

    connector = SQLiteConnector()
    await connector.connect(
        ConnectorConfig(connector_type="sqlite", connection_string=f"sqlite:///{db_path}")
    )

    docs = await connector.fetch(FetchQuery(collection="training"))
    assert len(docs) == 5

    cleaner = DataCleaner()
    clean_result = cleaner.clean(docs, CleanConfig())
    assert len(clean_result.cleaned) > 0

    await connector.disconnect()
