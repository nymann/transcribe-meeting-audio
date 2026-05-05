from transcribe_meeting_audio.domain.audio import InputDevice


class StaticDeviceRegistry:
    """Stub: returns a fixed device until a CoreAudio-backed registry lands."""

    def __init__(self, device: InputDevice) -> None:
        self._device = device

    def current_input(self) -> InputDevice:
        return self._device
