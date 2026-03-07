from __future__ import annotations

from adaptron.core.registry import register_plugin
from adaptron.understand.models import Chunk


@register_plugin("rag", "retriever")
class ChromaRetriever:
    def __init__(self, persist_dir: str = "./chroma_db") -> None:
        self.persist_dir = persist_dir

    def retrieve(
        self, query: str, collection_name: str = "default", top_k: int = 5
    ) -> list[Chunk]:
        import chromadb

        client = chromadb.PersistentClient(path=self.persist_dir)
        collection = client.get_collection(name=collection_name)
        results = collection.query(query_texts=[query], n_results=top_k)
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            chunks.append(
                Chunk(
                    content=doc,
                    chunk_index=meta.get("chunk_index", i),
                    source_ref=meta.get("source_ref", ""),
                )
            )
        return chunks
