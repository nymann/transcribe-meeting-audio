from typing import Protocol

from transcribe_meeting_audio.ports.loopback_session import LoopbackSession
from transcribe_meeting_audio.ports.mic_session import MicSession


class SessionFactory(Protocol):
    def mic(self) -> MicSession: ...
    def loopback(self) -> LoopbackSession: ...
