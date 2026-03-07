# tests/rag/test_rag.py
import pytest
from adaptron.rag.indexer import ChromaIndexer
from adaptron.rag.retriever import ChromaRetriever
from adaptron.understand.models import Chunk


def test_index_and_retrieve(tmp_path):
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")
    chunks = [
        Chunk(content="Machine learning is a subset of artificial intelligence.", chunk_index=0, source_ref="doc1"),
        Chunk(content="Fine-tuning adapts pre-trained models to specific tasks.", chunk_index=1, source_ref="doc1"),
        Chunk(content="Ollama runs LLMs locally on your machine.", chunk_index=2, source_ref="doc2"),
    ]
    indexer = ChromaIndexer(persist_dir=str(tmp_path / "chroma"))
    indexer.index(chunks, collection_name="test")
    retriever = ChromaRetriever(persist_dir=str(tmp_path / "chroma"))
    results = retriever.retrieve("What is machine learning?", collection_name="test", top_k=2)
    assert len(results) <= 2
    assert any("machine learning" in r.content.lower() for r in results)
