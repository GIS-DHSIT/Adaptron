"""Data cleaner for preprocessing training data."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from adaptron.ingest.models import RawDocument

logger = logging.getLogger(__name__)


@dataclass
class CleanConfig:
    dedup: bool = True
    dedup_threshold: float = 0.95
    fix_encoding: bool = True
    strip_html: bool = True
    normalize_whitespace: bool = True
    remove_empty: bool = True
    min_content_length: int = 10
    max_content_length: int | None = None
    custom_filters: list[Callable] = field(default_factory=list)


@dataclass
class CleanResult:
    cleaned: list[RawDocument]
    removed_count: int
    dedup_count: int
    encoding_fixes: int
    report: dict[str, Any]


# Common mojibake replacements
_ENCODING_FIXES: dict[str, str] = {
    "â\x80\x99": "\u2019",  # right single quote
    "â\x80\x9c": "\u201c",  # left double quote
    "â\x80\x9d": "\u201d",  # right double quote
    "â\x80\x93": "\u2013",  # en dash
    "â\x80\x94": "\u2014",  # em dash
    "Ã©": "\u00e9",  # e-acute
    "Ã¨": "\u00e8",  # e-grave
    "Ã¯": "\u00ef",  # i-diaeresis
    "Ã¢": "\u00e2",  # a-circumflex
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{2,}")


class DataCleaner:
    """Processes RawDocument lists through a sequential cleaning pipeline."""

    def clean(self, docs: list[RawDocument], config: CleanConfig | None = None) -> CleanResult:
        if config is None:
            config = CleanConfig()

        report: dict[str, Any] = {}
        encoding_fixes = 0
        removed_empty = 0
        removed_short = 0
        removed_long = 0
        dedup_count = 0

        working = list(docs)

        # Step 1: fix_encoding
        if config.fix_encoding:
            fixed = 0
            for doc in working:
                original = doc.content
                doc.content = self._fix_encoding(doc.content)
                if doc.content != original:
                    fixed += 1
            encoding_fixes = fixed
            report["encoding_fixes"] = fixed

        # Step 2: strip_html
        if config.strip_html:
            for doc in working:
                doc.content = _HTML_TAG_RE.sub("", doc.content)
            report["strip_html"] = True

        # Step 3: normalize_whitespace
        if config.normalize_whitespace:
            for doc in working:
                doc.content = self._normalize_whitespace(doc.content)
            report["normalize_whitespace"] = True

        # Step 4: remove_empty
        if config.remove_empty:
            before = len(working)
            working = [d for d in working if d.content.strip()]
            removed_empty = before - len(working)
            report["removed_empty"] = removed_empty

        # Step 5: min_content_length
        before = len(working)
        working = [d for d in working if len(d.content) >= config.min_content_length]
        removed_short = before - len(working)
        report["removed_short"] = removed_short

        # Step 5b: max_content_length
        if config.max_content_length is not None:
            before = len(working)
            working = [d for d in working if len(d.content) <= config.max_content_length]
            removed_long = before - len(working)
            report["removed_long"] = removed_long

        # Step 6: dedup
        if config.dedup:
            before = len(working)
            seen: set[str] = set()
            deduped: list[RawDocument] = []
            for doc in working:
                h = hashlib.md5(doc.content.encode("utf-8")).hexdigest()
                if h not in seen:
                    seen.add(h)
                    deduped.append(doc)
            working = deduped
            dedup_count = before - len(working)
            report["dedup_count"] = dedup_count

        # Custom filters
        for filt in config.custom_filters:
            working = [d for d in working if filt(d)]

        total_removed = len(docs) - len(working)
        report["original_count"] = len(docs)
        report["final_count"] = len(working)

        return CleanResult(
            cleaned=working,
            removed_count=total_removed,
            dedup_count=dedup_count,
            encoding_fixes=encoding_fixes,
            report=report,
        )

    @staticmethod
    def _fix_encoding(text: str) -> str:
        try:
            import ftfy
            return ftfy.fix_text(text)
        except ImportError:
            for bad, good in _ENCODING_FIXES.items():
                text = text.replace(bad, good)
            return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        text = _MULTI_SPACE_RE.sub(" ", text)
        text = _MULTI_NEWLINE_RE.sub("\n", text)
        return text.strip()
