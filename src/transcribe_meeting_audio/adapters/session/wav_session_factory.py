"""Factory: real WAV mic session + CoreAudio process-tap loopback."""
from pathlib import Path

from transcribe_meeting_audio.adapters.session.process_tap_loopback_session import (
    ProcessTapLoopbackSession,
)
from transcribe_meeting_audio.adapters.session.wav_mic_session import WavMicSession


class WavSessionFactory:
    def __init__(self, output_dir: Path, sample_rate: int = 16000) -> None:
        self._dir = output_dir
        self._sample_rate = sample_rate
        self._dir.mkdir(parents=True, exist_ok=True)
        # Resume numbering from the highest meeting-N already on disk so we
        # don't overwrite previous recordings on each CLI invocation.
        existing = []
        for p in self._dir.glob("meeting-*-mic.wav"):
            parts = p.stem.split("-")
            if len(parts) >= 3 and parts[1].isdigit():
                existing.append(int(parts[1]))
        self._meetings = max(existing, default=0)
        self._mic_sessions: list[WavMicSession] = []
        self._loopback_sessions: list[ProcessTapLoopbackSession] = []

    def mic(self) -> WavMicSession:
        self._meetings += 1
        session = WavMicSession(
            path=self._dir / f"meeting-{self._meetings}-mic.wav",
            sample_rate=self._sample_rate,
        )
        self._mic_sessions.append(session)
        return session

    def loopback(self) -> ProcessTapLoopbackSession:
        session = ProcessTapLoopbackSession(
            path=self._dir / f"meeting-{self._meetings}-loopback.wav"
        )
        self._loopback_sessions.append(session)
        return session

    @property
    def active_mic(self) -> WavMicSession | None:
        if self._mic_sessions and self._mic_sessions[-1].is_recording:
            return self._mic_sessions[-1]
        return None

    @property
    def active_loopback(self) -> ProcessTapLoopbackSession | None:
        if self._loopback_sessions and self._loopback_sessions[-1].is_recording:
            return self._loopback_sessions[-1]
        return None
