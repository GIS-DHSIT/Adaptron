import pytest

from adaptron.core.registry import global_registry
from adaptron.ingest.csv_ingester import CSVIngester
from adaptron.ingest.models import DataSource, SourceType


def test_registered_as_ingester_csv():
    cls = global_registry.get("ingester", "csv")
    assert cls is CSVIngester


def test_ingest_csv_file(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("name,age,city\nAlice,30,London\nBob,25,Paris\n", encoding="utf-8")

    ingester = CSVIngester()
    source = DataSource(source_type=SourceType.CSV, path=str(csv_path))
    docs = ingester.ingest(source)

    assert len(docs) == 1
    assert "name,age,city" in docs[0].content
    assert "Alice,30,London" in docs[0].content
    assert docs[0].metadata["headers"] == ["name", "age", "city"]
    assert docs[0].metadata["row_count"] == 2
    assert len(docs[0].tables) == 1
    assert docs[0].tables[0]["headers"] == ["name", "age", "city"]
    assert len(docs[0].tables[0]["rows"]) == 2
    assert docs[0].source_ref == str(csv_path)


def test_ingest_missing_file():
    ingester = CSVIngester()
    source = DataSource(source_type=SourceType.CSV, path="/nonexistent/file.csv")
    with pytest.raises(FileNotFoundError):
        ingester.ingest(source)
