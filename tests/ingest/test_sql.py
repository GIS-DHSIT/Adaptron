import sqlite3
from pathlib import Path
from adaptron.ingest.sql import SQLIngester
from adaptron.ingest.models import DataSource, SourceType


def _create_test_db(path: Path) -> str:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@test.com')")
    conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@test.com')")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL)")
    conn.execute("INSERT INTO orders VALUES (1, 1, 99.99)")
    conn.commit()
    conn.close()
    return f"sqlite:///{path}"


def test_sql_ingester_extracts_schema_and_data(tmp_path):
    db_path = tmp_path / "test.db"
    conn_str = _create_test_db(db_path)
    ingester = SQLIngester()
    source = DataSource(source_type=SourceType.SQL, connection_string=conn_str)
    docs = ingester.ingest(source)
    assert len(docs) >= 2
    full_text = " ".join(d.content for d in docs)
    assert "users" in full_text
    assert "Alice" in full_text


def test_sql_ingester_supported_types():
    ingester = SQLIngester()
    assert "sql" in ingester.supported_types()
