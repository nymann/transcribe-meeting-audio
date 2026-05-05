"""Speaker diarization via pyannote.audio.

Requires:
  - HF token in HF_TOKEN, or run `huggingface-cli login` once.
  - Terms accepted at https://huggingface.co/pyannote/speaker-diarization-3.1
    and https://huggingface.co/pyannote/segmentation-3.0

Heavy deps (torch, pyannote.audio) are imported lazily so a missing install
fails inside __init__ rather than at module import time, letting the CLI
gracefully degrade.
"""
import os

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.diarization import SpeakerSegment


class PyannoteDiarizer:
    def __init__(
        self,
        model: str = "pyannote/speaker-diarization-3.1",
        device: str | None = None,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> None:
        import torch
        from pyannote.audio import Pipeline

        token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_HUB_TOKEN")
            or True
        )
        pipeline = Pipeline.from_pretrained(model, token=token)
        if pipeline is None:
            raise RuntimeError(
                f"Pipeline.from_pretrained({model!r}) returned None — "
                f"accept terms at https://huggingface.co/{model} and run "
                "`huggingface-cli login` (or set HF_TOKEN)."
            )
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        pipeline.to(torch.device(device))
        self._pipeline = pipeline
        self._default_kwargs: dict = {}
        if num_speakers is not None:
            self._default_kwargs["num_speakers"] = num_speakers
        else:
            # Without a ceiling, pyannote collapses short multi-speaker audio
            # into one cluster. 8 is a generous default; per-call max_speakers
            # overrides it. min=1 keeps solo recordings honest.
            self._default_kwargs["max_speakers"] = (
                max_speakers if max_speakers is not None else 8
            )
            self._default_kwargs["min_speakers"] = (
                min_speakers if min_speakers is not None else 1
            )

    def diarize(
        self,
        track: AudioTrack,
        max_speakers: int | None = None,
    ) -> tuple[SpeakerSegment, ...]:
        if max_speakers is not None:
            kwargs = {"max_speakers": max_speakers, "min_speakers": 1}
        else:
            kwargs = self._default_kwargs
        result = self._pipeline(str(track.path), **kwargs)
        # pyannote.audio 4.x wraps the Annotation in a DiarizeOutput; older
        # versions returned the Annotation directly.
        annotation = getattr(result, "speaker_diarization", result)
        return tuple(
            SpeakerSegment(start=turn.start, end=turn.end, speaker_id=speaker)
            for turn, _, speaker in annotation.itertracks(yield_label=True)
        )
