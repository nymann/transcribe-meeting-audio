from dataclasses import dataclass
from enum import StrEnum

from transcribe_meeting_audio.domain.audio import InputDevice


class MeetingEventKind(StrEnum):
    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True)
class MeetingEvent:
    kind: MeetingEventKind
    at: float


@dataclass(frozen=True)
class DeviceChanged:
    device: InputDevice
    at: float


@dataclass(frozen=True)
class TimePassed:
    at: float


Event = MeetingEvent | DeviceChanged | TimePassed
