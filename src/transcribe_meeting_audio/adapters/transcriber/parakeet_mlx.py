"""Parakeet ASR via parakeet-mlx. Returns sentence-level timestamped segments."""
from parakeet_mlx import from_pretrained

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.transcript import Transcript, TranscriptSegment


class ParakeetTranscriber:
    def __init__(self, model_id: str = "mlx-community/parakeet-tdt-0.6b-v3") -> None:
        self._model = from_pretrained(model_id)

    def transcribe(self, track: AudioTrack) -> Transcript:
        result = self._model.transcribe(str(track.path))
        segments = tuple(
            TranscriptSegment(start=s.start, end=s.end, text=s.text.strip())
            for s in result.sentences
            if s.text.strip()
        )
        return Transcript(segments=segments)
