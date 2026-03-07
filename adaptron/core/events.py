"""Event bus for pipeline progress and hook notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import time


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Event], None]]] = {}

    def on(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event_type: str, event: Event) -> None:
        for cb in self._listeners.get(event_type, []):
            cb(event)
        if event_type != "*":
            for cb in self._listeners.get("*", []):
                cb(event)

    def off(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb is not callback
            ]
