"""Mic capture via sounddevice; writes a 16 kHz mono WAV at stop."""
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from transcribe_meeting_audio.domain.audio import AudioTrack, InputDevice


class WavMicSession:
    def __init__(self, path: Path, sample_rate: int = 16000) -> None:
        self._path = path
        self._sample_rate = sample_rate
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._start_at: float | None = None
        self.is_recording: bool = False

    def _open(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            callback=self._on_audio,
        )
        self._stream.start()

    def _close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _on_audio(self, indata, frames, time_info, status) -> None:
        self._chunks.append(indata.copy())

    @property
    def seconds_captured(self) -> float:
        return sum(c.shape[0] for c in self._chunks) / self._sample_rate

    def start(self, device: InputDevice, at: float) -> None:
        self._start_at = at
        self.is_recording = True
        self._open()

    def switch_to(self, device: InputDevice, at: float) -> None:
        # macOS' default input is followed automatically when sd.InputStream uses
        # the system default; we just reopen so a removed device's stream is closed.
        self._close()
        self._open()

    def stop(self, at: float) -> AudioTrack:
        assert self._start_at is not None
        self.is_recording = False
        self._close()
        if self._chunks:
            audio = np.concatenate(self._chunks, axis=0)
        else:
            audio = np.zeros((0, 1), dtype=np.float32)
        # soundfile chokes on truly empty arrays; write at least one frame so
        # downstream paths (transcription) don't fall over either.
        if audio.size == 0:
            audio = np.zeros((max(1, int(self._sample_rate * 0.1)), 1), dtype=np.float32)
        sf.write(str(self._path), audio, self._sample_rate)
        print(f"    mic: wrote {audio.shape[0]} frames -> {self._path.name}")
        return AudioTrack(path=self._path, start_at=self._start_at, end_at=at)
