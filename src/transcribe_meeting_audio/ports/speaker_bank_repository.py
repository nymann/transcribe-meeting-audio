from typing import Protocol

from transcribe_meeting_audio.domain.speaker_bank import SpeakerBank


class SpeakerBankRepository(Protocol):
    def load(self) -> SpeakerBank: ...
    def save(self, bank: SpeakerBank) -> None: ...
