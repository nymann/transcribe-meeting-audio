from typing import Protocol

from transcribe_meeting_audio.domain.audio import AudioTrack


class LoopbackSession(Protocol):
    def start(self, at: float) -> None: ...
    def stop(self, at: float) -> AudioTrack: ...
