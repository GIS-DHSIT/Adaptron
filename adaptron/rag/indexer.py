from __future__ import annotations

from adaptron.core.registry import register_plugin
from adaptron.understand.models import Chunk


@register_plugin("rag", "indexer")
class ChromaIndexer:
    def __init__(self, persist_dir: str = "./chroma_db") -> None:
        self.persist_dir = persist_dir

    def index(self, chunks: list[Chunk], collection_name: str = "default") -> int:
        import chromadb

        client = chromadb.PersistentClient(path=self.persist_dir)
        collection = client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        ids = [f"chunk-{c.chunk_index}-{hash(c.content) % 10000}" for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {"source_ref": c.source_ref, "chunk_index": c.chunk_index} for c in chunks
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)
