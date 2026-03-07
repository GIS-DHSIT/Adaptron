from __future__ import annotations

import re

from adaptron.core.registry import register_plugin
from adaptron.ingest.models import RawDocument
from adaptron.understand.models import Chunk


@register_plugin("analyzer", "chunker")
class SemanticChunker:
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100) -> None:
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, document: RawDocument) -> list[Chunk]:
        text = document.content.strip()
        if len(text) <= self.max_chunk_size:
            return [
                Chunk(
                    content=text,
                    chunk_index=0,
                    source_ref=document.source_ref,
                    metadata=document.metadata.copy(),
                )
            ]
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: list[Chunk] = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) + 1 <= self.max_chunk_size:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(self._make_chunk(current, len(chunks), document))
                if len(para) > self.max_chunk_size:
                    sentence_chunks = self._split_by_sentences(
                        para, document, len(chunks)
                    )
                    chunks.extend(sentence_chunks)
                    current = ""
                else:
                    current = para
        if current.strip():
            chunks.append(self._make_chunk(current.strip(), len(chunks), document))
        return chunks

    def _split_by_sentences(
        self, text: str, document: RawDocument, start_index: int
    ) -> list[Chunk]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[Chunk] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) + 1 <= self.max_chunk_size:
                current = (current + " " + sent).strip()
            else:
                if current:
                    chunks.append(
                        self._make_chunk(
                            current, start_index + len(chunks), document
                        )
                    )
                current = sent
        if current.strip():
            chunks.append(
                self._make_chunk(
                    current.strip(), start_index + len(chunks), document
                )
            )
        return chunks

    def _make_chunk(
        self, content: str, index: int, document: RawDocument
    ) -> Chunk:
        return Chunk(
            content=content,
            chunk_index=index,
            source_ref=document.source_ref,
            metadata=document.metadata.copy(),
        )
