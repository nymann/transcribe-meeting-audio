from pathlib import Path

from transcribe_meeting_audio.domain.audio import AudioTrack


class RecordedLoopbackSession:
    """A test fake mirroring LoopbackSession; remembers its window for assertions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.start_at: float | None = None
        self.stop_at: float | None = None
        self.finalized: bool = False

    def start(self, at: float) -> None:
        self.start_at = at

    def stop(self, at: float) -> AudioTrack:
        assert self.start_at is not None
        self.stop_at = at
        self.finalized = True
        return AudioTrack(path=self._path, start_at=self.start_at, end_at=at)
