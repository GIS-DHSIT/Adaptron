from adaptron.synthesize.auto import AutoSynthesizer
from adaptron.core.registry import global_registry
from adaptron.connectors.models import DataSchema, CollectionSchema, FieldInfo
from adaptron.understand.models import Chunk


def test_auto_synthesizer_registered():
    cls = global_registry.get("synthesizer", "auto")
    assert cls is AutoSynthesizer


def test_auto_dispatches_to_qa():
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="faq",
            fields=[
                FieldInfo(name="question", data_type="string"),
                FieldInfo(name="answer", data_type="string"),
            ],
            source_type="table",
        )],
    )
    synth = AutoSynthesizer(schema=schema)
    chunks = [Chunk(content="Artificial intelligence is a field of computer science.")]
    results = synth.generate(chunks)
    assert len(results) > 0
    # QA format produces question/answer keys
    assert "question" in results[0] or "answer" in results[0]


def test_auto_fallback_to_instruction():
    synth = AutoSynthesizer()
    chunks = [Chunk(content="Machine learning is a subset of AI.")]
    results = synth.generate(chunks)
    assert len(results) > 0
    # Instruction format produces instruction/response keys
    assert "instruction" in results[0] or "response" in results[0]
