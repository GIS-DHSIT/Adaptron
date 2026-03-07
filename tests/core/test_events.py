from adaptron.core.events import EventBus, Event


def test_sync_listener():
    bus = EventBus()
    received = []
    bus.on("stage_start", lambda e: received.append(e))
    bus.emit("stage_start", Event(type="stage_start", data={"stage": "ingest"}))
    assert len(received) == 1
    assert received[0].data["stage"] == "ingest"


def test_multiple_listeners():
    bus = EventBus()
    count = {"a": 0, "b": 0}
    bus.on("progress", lambda e: count.__setitem__("a", count["a"] + 1))
    bus.on("progress", lambda e: count.__setitem__("b", count["b"] + 1))
    bus.emit("progress", Event(type="progress", data={}))
    assert count["a"] == 1
    assert count["b"] == 1


def test_no_listeners_no_error():
    bus = EventBus()
    bus.emit("unknown", Event(type="unknown", data={}))


def test_wildcard_listener():
    bus = EventBus()
    received = []
    bus.on("*", lambda e: received.append(e.type))
    bus.emit("stage_start", Event(type="stage_start", data={}))
    bus.emit("stage_end", Event(type="stage_end", data={}))
    assert received == ["stage_start", "stage_end"]
