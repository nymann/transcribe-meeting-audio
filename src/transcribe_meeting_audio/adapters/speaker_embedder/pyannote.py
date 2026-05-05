"""Speaker embeddings via pyannote's wespeaker model.

Lazy-imports torch + pyannote.audio so the CLI can degrade gracefully if
the diarize extras aren't installed.
"""
from collections.abc import Sequence

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.diarization import SpeakerSegment


class PyannoteEmbedder:
    def __init__(
        self,
        model_id: str = "pyannote/wespeaker-voxceleb-resnet34-LM",
        device: str | None = None,
    ) -> None:
        import torch
        from pyannote.audio import Inference, Model

        model = Model.from_pretrained(model_id)
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        model.to(torch.device(device))
        self._inference = Inference(model, window="whole")

    def embed_clusters(
        self, track: AudioTrack, segments: Sequence[SpeakerSegment]
    ) -> dict[str, tuple[float, ...]]:
        import numpy as np
        from pyannote.core import Segment

        by_speaker: dict[str, list] = {}
        for seg in segments:
            try:
                emb = self._inference.crop(str(track.path), Segment(seg.start, seg.end))
            except Exception:
                continue  # segment too short or otherwise unusable
            by_speaker.setdefault(seg.speaker_id, []).append(np.asarray(emb).flatten())

        result: dict[str, tuple[float, ...]] = {}
        for speaker_id, embs in by_speaker.items():
            if not embs:
                continue
            centroid = np.mean(np.stack(embs), axis=0)
            norm = np.linalg.norm(centroid)
            if norm == 0:
                continue
            unit = centroid / norm
            result[speaker_id] = tuple(float(x) for x in unit.tolist())
        return result
