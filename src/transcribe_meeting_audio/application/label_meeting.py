"""Use case: enroll the speakers from a finished meeting into the bank.

Given a loopback track, its prior diarization output, and a mapping from
SPEAKER_NN clusters to friendly names, compute per-cluster embeddings and
add them to the enrolled-speakers bank. Returns the renames so the caller
can rewrite any existing transcript file.
"""
from collections.abc import Sequence

from transcribe_meeting_audio.domain.audio import AudioTrack
from transcribe_meeting_audio.domain.diarization import SpeakerSegment
from transcribe_meeting_audio.domain.speaker_bank import EnrolledSpeaker
from transcribe_meeting_audio.ports.speaker_bank_repository import SpeakerBankRepository
from transcribe_meeting_audio.ports.speaker_embedder import SpeakerEmbedder


class LabelMeeting:
    def __init__(
        self, embedder: SpeakerEmbedder, bank_repo: SpeakerBankRepository
    ) -> None:
        self._embedder = embedder
        self._bank_repo = bank_repo

    def label(
        self,
        loopback_track: AudioTrack,
        diarization: Sequence[SpeakerSegment],
        labels: dict[str, str],
    ) -> dict[str, str]:
        embeddings = self._embedder.embed_clusters(loopback_track, diarization)
        bank = self._bank_repo.load()
        applied: dict[str, str] = {}
        for speaker_id, name in labels.items():
            if speaker_id not in embeddings:
                raise ValueError(
                    f"no embedding could be computed for {speaker_id} — "
                    "either it isn't in the diarization or its segments are too short"
                )
            bank.add(EnrolledSpeaker(name=name, embedding=embeddings[speaker_id]))
            applied[speaker_id] = name
        self._bank_repo.save(bank)
        return applied
