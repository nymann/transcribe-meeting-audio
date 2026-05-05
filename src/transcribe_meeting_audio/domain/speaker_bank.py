"""Bank of voice profiles: name -> normalized speaker embedding."""
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class EnrolledSpeaker:
    name: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class SpeakerMatch:
    name: str
    similarity: float


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


class SpeakerBank:
    def __init__(self, speakers: Iterable[EnrolledSpeaker] = ()) -> None:
        self._speakers: list[EnrolledSpeaker] = list(speakers)

    @property
    def speakers(self) -> tuple[EnrolledSpeaker, ...]:
        return tuple(self._speakers)

    def add(self, speaker: EnrolledSpeaker) -> None:
        self._speakers = [s for s in self._speakers if s.name != speaker.name]
        self._speakers.append(speaker)

    def remove(self, name: str) -> None:
        self._speakers = [s for s in self._speakers if s.name != name]

    def best_match(self, embedding: tuple[float, ...]) -> SpeakerMatch | None:
        if not self._speakers:
            return None
        best: SpeakerMatch | None = None
        for s in self._speakers:
            sim = _dot(s.embedding, embedding)
            if best is None or sim > best.similarity:
                best = SpeakerMatch(name=s.name, similarity=sim)
        return best
