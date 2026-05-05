from transcribe_meeting_audio.domain.audio import InputDevice


class ScriptedDeviceRegistry:
    """A test fake whose current input device can be set imperatively."""

    def __init__(self, initial: InputDevice) -> None:
        self._current = initial

    def set(self, device: InputDevice) -> None:
        self._current = device

    def current_input(self) -> InputDevice:
        return self._current
