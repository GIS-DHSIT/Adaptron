from __future__ import annotations

from abc import ABC, abstractmethod

from adaptron.ingest.models import RawDocument
from adaptron.understand.models import AnalyzedCorpus


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, documents: list[RawDocument]) -> AnalyzedCorpus: ...
