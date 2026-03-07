from adaptron.core.registry import global_registry
from adaptron.synthesize.qa import QAPairSynthesizer
from adaptron.understand.models import Chunk


def test_qa_synthesizer_registered():
    cls = global_registry.get("synthesizer", "qa")
    assert cls is QAPairSynthesizer


def test_generate_returns_qa_pairs():
    chunks = [
        Chunk(content="Machine learning is a subset of AI.", source_ref="test", chunk_index=0),
        Chunk(content="Fine-tuning adapts a model to a task.", source_ref="test", chunk_index=1),
    ]
    synth = QAPairSynthesizer()
    results = synth.generate(chunks)
    assert len(results) == 2
    for item in results:
        assert "question" in item
        assert "answer" in item
        assert len(item["question"]) > 0
        assert len(item["answer"]) > 0
