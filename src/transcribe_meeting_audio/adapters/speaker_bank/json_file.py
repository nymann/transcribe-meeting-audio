import json
from pathlib import Path

from transcribe_meeting_audio.domain.speaker_bank import EnrolledSpeaker, SpeakerBank


class JsonFileSpeakerBank:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> SpeakerBank:
        if not self._path.exists():
            return SpeakerBank()
        data = json.loads(self._path.read_text())
        return SpeakerBank(
            EnrolledSpeaker(name=s["name"], embedding=tuple(s["embedding"]))
            for s in data.get("speakers", [])
        )

    def save(self, bank: SpeakerBank) -> None:
        payload = {
            "speakers": [
                {"name": s.name, "embedding": list(s.embedding)} for s in bank.speakers
            ]
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2))
