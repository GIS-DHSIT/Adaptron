"""Plugin registry for extensible pipeline components."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for discovering and resolving pipeline plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, dict[str, type]] = {}

    def register(self, category: str, name: str):
        """Decorator to register a plugin class under category/name."""
        def decorator(cls: type) -> type:
            if category not in self._plugins:
                self._plugins[category] = {}
            if name in self._plugins[category]:
                logger.warning(
                    "Overwriting plugin %s/%s: %s -> %s",
                    category, name,
                    self._plugins[category][name].__name__, cls.__name__,
                )
            self._plugins[category][name] = cls
            return cls
        return decorator

    def get(self, category: str, name: str) -> type:
        """Resolve a plugin by category and name. Raises KeyError if not found."""
        try:
            return self._plugins[category][name]
        except KeyError:
            available = self.list_plugins(category)
            raise KeyError(
                f"Plugin '{name}' not found in category '{category}'. "
                f"Available: {available}"
            )

    def list_plugins(self, category: str) -> list[str]:
        """List all registered plugin names in a category."""
        return list(self._plugins.get(category, {}).keys())


# Global registry instance
global_registry = PluginRegistry()


def register_plugin(category: str, name: str):
    """Register a plugin in the global registry."""
    return global_registry.register(category, name)
