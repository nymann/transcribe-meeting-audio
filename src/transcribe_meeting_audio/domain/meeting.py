from dataclasses import dataclass
from enum import StrEnum

from transcribe_meeting_audio.domain.audio import AudioTrack


class CallApp(StrEnum):
    TEAMS = "Teams"
    DISCORD = "Discord"
    ZOOM = "Zoom"
    SLACK = "Slack"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class Meeting:
    label: CallApp
    mic_track: AudioTrack
    loopback_track: AudioTrack


@dataclass(frozen=True)
class AttributedSegment:
    start: float  # seconds since the meeting started
    end: float
    speaker: str
    text: str


@dataclass(frozen=True)
class MeetingTranscript:
    label: CallApp
    duration: float
    segments: tuple[AttributedSegment, ...]
