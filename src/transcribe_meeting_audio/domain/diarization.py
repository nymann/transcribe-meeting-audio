from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerSegment:
    start: float
    end: float
    speaker_id: str
