# tests/core/test_registry.py
from adaptron.core.registry import PluginRegistry, register_plugin


class DummyBase:
    pass


def test_register_and_get_plugin():
    registry = PluginRegistry()

    @registry.register("trainer", "qlora")
    class QLoRATrainer(DummyBase):
        name = "qlora"

    plugin = registry.get("trainer", "qlora")
    assert plugin is QLoRATrainer


def test_get_missing_plugin_raises():
    registry = PluginRegistry()
    try:
        registry.get("trainer", "nonexistent")
        assert False, "Should have raised"
    except KeyError:
        pass


def test_list_plugins():
    registry = PluginRegistry()

    @registry.register("trainer", "qlora")
    class A(DummyBase):
        pass

    @registry.register("trainer", "full_ft")
    class B(DummyBase):
        pass

    plugins = registry.list_plugins("trainer")
    assert set(plugins) == {"qlora", "full_ft"}


def test_list_plugins_empty_category():
    registry = PluginRegistry()
    assert registry.list_plugins("unknown") == []


def test_register_duplicate_warns(caplog):
    import logging
    registry = PluginRegistry()

    @registry.register("trainer", "qlora")
    class A(DummyBase):
        pass

    with caplog.at_level(logging.WARNING):
        @registry.register("trainer", "qlora")
        class B(DummyBase):
            pass

    assert "Overwriting" in caplog.text
    assert registry.get("trainer", "qlora") is B
