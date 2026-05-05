from typing import Protocol


class TranscriptPolisher(Protocol):
    def polish(self, markdown: str) -> str:
        """Take a markdown transcript and return a context-corrected version
        in the same format. Implementations must preserve speaker labels,
        timestamps, and segment count."""
