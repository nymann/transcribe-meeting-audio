from collections.abc import Sequence
from typing import Protocol

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.diarization import SpeakerSegment


class Diarizer(Protocol):
    def diarize(
        self,
        track: AudioTrack,
        max_speakers: int | None = None,
    ) -> Sequence[SpeakerSegment]: ...
