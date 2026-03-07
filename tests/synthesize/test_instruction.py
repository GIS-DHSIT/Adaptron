from adaptron.synthesize.instruction import TemplateInstructionGenerator
from adaptron.understand.models import Chunk


def test_generates_instruction_pairs():
    chunks = [
        Chunk(content="Machine learning is a subset of AI that learns from data.", chunk_index=0),
        Chunk(content="Fine-tuning adapts a pre-trained model to a specific task.", chunk_index=1),
    ]
    generator = TemplateInstructionGenerator()
    pairs = generator.generate(chunks)
    assert len(pairs) >= 2
    for pair in pairs:
        assert "instruction" in pair
        assert "response" in pair
        assert len(pair["instruction"]) > 0
        assert len(pair["response"]) > 0


def test_generates_from_empty_chunks():
    generator = TemplateInstructionGenerator()
    pairs = generator.generate([])
    assert pairs == []
