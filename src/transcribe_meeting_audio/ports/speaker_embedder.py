from collections.abc import Sequence
from typing import Protocol

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.diarization import SpeakerSegment


class SpeakerEmbedder(Protocol):
    def embed_clusters(
        self, track: AudioTrack, segments: Sequence[SpeakerSegment]
    ) -> dict[str, tuple[float, ...]]:
        """Return {speaker_id: unit-length centroid embedding} per cluster."""
