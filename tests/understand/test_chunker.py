from adaptron.understand.chunker import SemanticChunker
from adaptron.ingest.models import RawDocument


def test_chunker_splits_long_text():
    text = (
        "First paragraph about machine learning. " * 50
        + "\n\n"
        + "Second paragraph about fine-tuning. " * 50
    )
    doc = RawDocument(content=text, source_ref="test.pdf")
    chunker = SemanticChunker(max_chunk_size=500, overlap=50)
    chunks = chunker.chunk(doc)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 600
        assert chunk.source_ref == "test.pdf"


def test_chunker_preserves_short_text():
    doc = RawDocument(content="Short text.", source_ref="test.pdf")
    chunker = SemanticChunker(max_chunk_size=500, overlap=50)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].content == "Short text."


def test_chunker_respects_paragraph_boundaries():
    text = "Paragraph one. " * 20 + "\n\n" + "Paragraph two. " * 20
    doc = RawDocument(content=text, source_ref="test.pdf")
    chunker = SemanticChunker(max_chunk_size=200, overlap=30)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 2
