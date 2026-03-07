from adaptron.core.registry import global_registry
from adaptron.synthesize.chat import ChatConversationSynthesizer
from adaptron.understand.models import Chunk


def test_chat_synthesizer_registered():
    cls = global_registry.get("synthesizer", "chat")
    assert cls is ChatConversationSynthesizer


def test_generate_returns_conversation_format():
    chunks = [
        Chunk(content="Neural networks are inspired by the brain.", source_ref="test", chunk_index=0),
    ]
    synth = ChatConversationSynthesizer()
    results = synth.generate(chunks)
    assert len(results) == 1
    item = results[0]
    assert "messages" in item
    messages = item["messages"]
    assert len(messages) == 3
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant"]
    for m in messages:
        assert "content" in m
        assert len(m["content"]) > 0
