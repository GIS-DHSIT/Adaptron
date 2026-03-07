from __future__ import annotations

import hashlib

from adaptron.core.registry import register_plugin
from adaptron.understand.models import Chunk, QualityScore


@register_plugin("analyzer", "quality_scorer")
class QualityScorer:
    def score(self, chunks: list[Chunk]) -> QualityScore:
        if not chunks:
            return QualityScore(overall=0.0)

        hashes = [hashlib.md5(c.content.encode()).hexdigest() for c in chunks]
        unique_hashes = set(hashes)
        duplicate_ratio = (
            1.0 - (len(unique_hashes) / len(hashes)) if hashes else 0.0
        )

        noise_count = sum(
            1
            for c in chunks
            if len(c.content.strip()) < 20
            or c.content.strip().count(" ") / max(len(c.content), 1) > 0.5
        )
        noise_ratio = noise_count / len(chunks)

        avg_len = sum(len(c.content) for c in chunks) / len(chunks)
        coverage = min(avg_len / 500.0, 1.0)

        overall = (
            (1.0 - duplicate_ratio) * 0.4
            + (1.0 - noise_ratio) * 0.3
            + coverage * 0.3
        )

        return QualityScore(
            overall=overall,
            noise_ratio=noise_ratio,
            duplicate_ratio=duplicate_ratio,
            coverage=coverage,
            details={
                "total_chunks": len(chunks),
                "unique_chunks": len(unique_hashes),
            },
        )
