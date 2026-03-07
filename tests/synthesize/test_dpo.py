from adaptron.core.registry import global_registry
from adaptron.synthesize.dpo import DPOPreferenceSynthesizer
from adaptron.understand.models import Chunk


def test_dpo_synthesizer_registered():
    cls = global_registry.get("synthesizer", "dpo")
    assert cls is DPOPreferenceSynthesizer


def test_generate_returns_dpo_format():
    chunks = [
        Chunk(content="Transformers use self-attention mechanisms.", source_ref="test", chunk_index=0),
        Chunk(content="RLHF aligns language models with human preferences.", source_ref="test", chunk_index=1),
    ]
    synth = DPOPreferenceSynthesizer()
    results = synth.generate(chunks)
    assert len(results) == 2
    for item in results:
        assert "prompt" in item
        assert "chosen" in item
        assert "rejected" in item
        assert len(item["prompt"]) > 0
        assert len(item["chosen"]) > 0
        assert len(item["rejected"]) > 0
