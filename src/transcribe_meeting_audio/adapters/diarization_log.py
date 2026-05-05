"""Persist a sequence of SpeakerSegments as JSON next to the audio file."""
import json
from collections.abc import Sequence
from pathlib import Path

from transcribe_meeting_audio.domain.diarization import SpeakerSegment


def save_diarization(path: Path, segments: Sequence[SpeakerSegment]) -> None:
    payload = {
        "segments": [
            {"start": s.start, "end": s.end, "speaker_id": s.speaker_id}
            for s in segments
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_diarization(path: Path) -> tuple[SpeakerSegment, ...]:
    data = json.loads(path.read_text())
    return tuple(
        SpeakerSegment(start=s["start"], end=s["end"], speaker_id=s["speaker_id"])
        for s in data.get("segments", [])
    )
