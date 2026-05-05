from typing import Protocol

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.transcript import Transcript


class Transcriber(Protocol):
    def transcribe(self, track: AudioTrack) -> Transcript: ...
