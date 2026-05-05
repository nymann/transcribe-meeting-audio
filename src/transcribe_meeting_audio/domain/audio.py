from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InputDevice:
    id: str
    name: str


@dataclass(frozen=True)
class AudioTrack:
    path: Path
    start_at: float
    end_at: float
