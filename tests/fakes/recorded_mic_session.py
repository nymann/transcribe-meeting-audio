from pathlib import Path

from transcribe_meeting_audio.domain.audio import AudioTrack, InputDevice


class RecordedMicSession:
    """A test fake that records every device change for later assertions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.start_at: float | None = None
        self.stop_at: float | None = None
        self.devices: list[tuple[float, InputDevice]] = []
        self.finalized: bool = False

    def start(self, device: InputDevice, at: float) -> None:
        self.start_at = at
        self.devices.append((at, device))

    def switch_to(self, device: InputDevice, at: float) -> None:
        self.devices.append((at, device))

    def stop(self, at: float) -> AudioTrack:
        assert self.start_at is not None
        self.stop_at = at
        self.finalized = True
        return AudioTrack(path=self._path, start_at=self.start_at, end_at=at)

    def device_names(self) -> list[str]:
        return [d.name for _, d in self.devices]
