from adaptron.core.registry import global_registry
from adaptron.synthesize.corpus import CorpusSynthesizer
from adaptron.understand.models import Chunk


def test_corpus_synthesizer_registered():
    cls = global_registry.get("synthesizer", "corpus")
    assert cls is CorpusSynthesizer


def test_generate_returns_corpus_format():
    chunks = [
        Chunk(content="First paragraph of text.", source_ref="test", chunk_index=0),
        Chunk(content="Second paragraph of text.", source_ref="test", chunk_index=1),
    ]
    synth = CorpusSynthesizer()
    results = synth.generate(chunks)
    assert len(results) == 1
    item = results[0]
    assert "text" in item
    assert "First paragraph" in item["text"]
    assert "Second paragraph" in item["text"]
