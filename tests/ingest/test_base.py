from adaptron.ingest.models import RawDocument, DataSource, SourceType
from adaptron.ingest.base import BaseIngester


def test_raw_document_creation():
    doc = RawDocument(content="Hello world", metadata={"source": "test.pdf", "page": 1}, source_ref="test.pdf")
    assert doc.content == "Hello world"
    assert doc.metadata["page"] == 1


def test_data_source_creation():
    src = DataSource(source_type=SourceType.PDF, path="/data/test.pdf")
    assert src.source_type == SourceType.PDF


def test_base_ingester_is_abstract():
    try:
        BaseIngester()
        assert False, "Should not instantiate abstract class"
    except TypeError:
        pass
