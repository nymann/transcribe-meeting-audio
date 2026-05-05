from typing import Protocol

from transcribe_meeting_audio.domain.audio import InputDevice


class DeviceRegistry(Protocol):
    def current_input(self) -> InputDevice: ...
