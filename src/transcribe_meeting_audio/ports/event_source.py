from collections.abc import Iterator
from typing import Protocol

from transcribe_meeting_audio.domain.events import Event


class EventSource(Protocol):
    def watch(self) -> Iterator[Event]: ...
