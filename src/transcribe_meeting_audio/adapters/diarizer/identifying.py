"""Diarizer decorator that renames clusters using an enrolled speaker bank.

Wraps another Diarizer. After diarization runs, computes a centroid embedding
per cluster, looks up the closest enrolled speaker, and renames the cluster
when similarity beats the threshold. Unknown clusters keep their SPEAKER_NN
label.
"""
from collections.abc import Sequence

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.diarization import SpeakerSegment
from transcribe_meeting_audio.domain.speaker_bank import SpeakerBank
from transcribe_meeting_audio.ports.diarizer import Diarizer
from transcribe_meeting_audio.ports.speaker_embedder import SpeakerEmbedder


class IdentifyingDiarizer:
    def __init__(
        self,
        base: Diarizer,
        embedder: SpeakerEmbedder,
        bank: SpeakerBank,
        threshold: float = 0.5,
    ) -> None:
        self._base = base
        self._embedder = embedder
        self._bank = bank
        self._threshold = threshold

    def diarize(
        self,
        track: AudioTrack,
        max_speakers: int | None = None,
    ) -> tuple[SpeakerSegment, ...]:
        raw = tuple(self._base.diarize(track, max_speakers=max_speakers))
        if not raw or not self._bank.speakers:
            return raw
        embeddings = self._embedder.embed_clusters(track, raw)
        renames: dict[str, str] = {}
        for speaker_id, emb in embeddings.items():
            match = self._bank.best_match(emb)
            if match is not None and match.similarity >= self._threshold:
                renames[speaker_id] = match.name
        if not renames:
            return raw
        return tuple(
            SpeakerSegment(
                start=s.start,
                end=s.end,
                speaker_id=renames.get(s.speaker_id, s.speaker_id),
            )
            for s in raw
        )
