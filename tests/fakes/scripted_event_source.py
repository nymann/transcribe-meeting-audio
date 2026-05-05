from collections.abc import Iterator

from transcribe_meeting_audio.domain.events import Event


class ScriptedEventSource:
    """A test fake that yields pre-scripted events in order."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def emit(self, event: Event) -> None:
        self._events.append(event)

    def watch(self) -> Iterator[Event]:
        for event in self._events:
            yield event
