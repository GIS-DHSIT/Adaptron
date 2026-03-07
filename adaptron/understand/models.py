from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    content: str
    chunk_index: int = 0
    source_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    text: str
    label: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0


@dataclass
class QualityScore:
    overall: float = 0.0
    noise_ratio: float = 0.0
    duplicate_ratio: float = 0.0
    coverage: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzedCorpus:
    chunks: list[Chunk] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    quality: QualityScore = field(default_factory=QualityScore)
    schema_descriptions: dict[str, str] = field(default_factory=dict)
