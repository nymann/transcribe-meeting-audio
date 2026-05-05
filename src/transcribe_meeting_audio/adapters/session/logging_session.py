from pathlib import Path

from transcribe_meeting_audio.domain.audio import AudioTrack, InputDevice


class LoggingMicSession:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._start_at: float | None = None

    def start(self, device: InputDevice, at: float) -> None:
        self._start_at = at
        print(f"[{at:8.2f}] mic    start    {device.name!r}")

    def switch_to(self, device: InputDevice, at: float) -> None:
        print(f"[{at:8.2f}] mic    switch   {device.name!r}")

    def stop(self, at: float) -> AudioTrack:
        assert self._start_at is not None
        print(f"[{at:8.2f}] mic    stop     -> {self._path}")
        return AudioTrack(path=self._path, start_at=self._start_at, end_at=at)


class LoggingLoopbackSession:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._start_at: float | None = None

    def start(self, at: float) -> None:
        self._start_at = at
        print(f"[{at:8.2f}] loop   start")

    def stop(self, at: float) -> AudioTrack:
        assert self._start_at is not None
        print(f"[{at:8.2f}] loop   stop     -> {self._path}")
        return AudioTrack(path=self._path, start_at=self._start_at, end_at=at)


class LoggingSessionFactory:
    def __init__(self) -> None:
        self._meetings = 0

    def mic(self) -> LoggingMicSession:
        self._meetings += 1
        return LoggingMicSession(Path(f"meeting-{self._meetings}-mic.wav"))

    def loopback(self) -> LoggingLoopbackSession:
        return LoggingLoopbackSession(Path(f"meeting-{self._meetings}-loopback.wav"))
