from typing import Protocol

from transcribe_meeting_audio.domain.meeting import CallApp


class CallContext(Protocol):
    def identify(self) -> CallApp: ...
