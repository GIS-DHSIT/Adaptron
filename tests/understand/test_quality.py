from adaptron.understand.quality import QualityScorer
from adaptron.understand.models import Chunk


def test_quality_scorer_detects_duplicates():
    chunks = [
        Chunk(content="This is some text about AI.", chunk_index=0),
        Chunk(content="This is some text about AI.", chunk_index=1),
        Chunk(content="Different text about ML.", chunk_index=2),
    ]
    scorer = QualityScorer()
    score = scorer.score(chunks)
    assert score.duplicate_ratio > 0


def test_quality_scorer_clean_data():
    chunks = [
        Chunk(content="First unique paragraph about training.", chunk_index=0),
        Chunk(content="Second unique paragraph about evaluation.", chunk_index=1),
    ]
    scorer = QualityScorer()
    score = scorer.score(chunks)
    assert score.duplicate_ratio == 0.0
    assert score.overall > 0.5
