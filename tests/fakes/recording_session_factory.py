from pathlib import Path

from tests.fakes.recorded_loopback_session import RecordedLoopbackSession
from tests.fakes.recorded_mic_session import RecordedMicSession


class RecordingSessionFactory:
    """A test fake factory that hands out fresh recorded sessions and remembers them."""

    def __init__(self) -> None:
        self.mic_sessions: list[RecordedMicSession] = []
        self.loopback_sessions: list[RecordedLoopbackSession] = []

    def mic(self) -> RecordedMicSession:
        index = len(self.mic_sessions)
        session = RecordedMicSession(path=Path(f"mic-{index}.wav"))
        self.mic_sessions.append(session)
        return session

    def loopback(self) -> RecordedLoopbackSession:
        index = len(self.loopback_sessions)
        session = RecordedLoopbackSession(path=Path(f"loopback-{index}.wav"))
        self.loopback_sessions.append(session)
        return session
