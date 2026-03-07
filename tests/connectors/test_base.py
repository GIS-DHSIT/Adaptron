import pytest
from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery


def test_base_connector_is_abstract():
    with pytest.raises(TypeError):
        BaseConnector()


def test_base_connector_supports_streaming_default():
    class DummyConnector(BaseConnector):
        async def connect(self, config): pass
        async def disconnect(self): pass
        async def fetch(self, query): return []
        async def discover_schema(self): return DataSchema(connector_type="test", database="test")

    c = DummyConnector()
    assert c.supports_streaming() is False


@pytest.mark.asyncio
async def test_base_connector_stream_raises_by_default():
    class DummyConnector(BaseConnector):
        async def connect(self, config): pass
        async def disconnect(self): pass
        async def fetch(self, query): return []
        async def discover_schema(self): return DataSchema(connector_type="test", database="test")

    c = DummyConnector()
    with pytest.raises(NotImplementedError):
        async for _ in c.stream(FetchQuery(collection="test")):
            pass
