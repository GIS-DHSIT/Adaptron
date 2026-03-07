from adaptron.core.registry import global_registry
from adaptron.synthesize.text2sql import Text2SQLSynthesizer
from adaptron.understand.models import Chunk


def test_text2sql_synthesizer_registered():
    cls = global_registry.get("synthesizer", "text2sql")
    assert cls is Text2SQLSynthesizer


def test_generate_returns_text2sql_pairs():
    chunks = [
        Chunk(
            content="CREATE TABLE users (id INT, name VARCHAR(255))",
            source_ref="test",
            chunk_index=0,
            metadata={"table_name": "users"},
        ),
        Chunk(
            content="CREATE TABLE orders (id INT, user_id INT, total DECIMAL)",
            source_ref="test",
            chunk_index=1,
            metadata={"table_name": "orders"},
        ),
    ]
    synth = Text2SQLSynthesizer()
    results = synth.generate(chunks)
    assert len(results) == 2
    for item in results:
        assert "question" in item
        assert "sql" in item
        assert len(item["question"]) > 0
        assert len(item["sql"]) > 0
