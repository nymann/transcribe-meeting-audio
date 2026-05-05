"""Manual event source for testing — driven by stdin lines.

  n / new / start  -> STARTED
  s / stop / end   -> ENDED (auto-advances past debounce so the meeting
                              finalizes immediately)

EOF (Ctrl+D) ends the stream and the CLI exits.
"""
import time
from collections.abc import Iterator

from transcribe_meeting_audio.domain.events import (
    Event,
    MeetingEvent,
    MeetingEventKind,
    TimePassed,
)


class KeyboardEventSource:
    def __init__(self, debounce_seconds: float = 2.0) -> None:
        self._debounce = debounce_seconds

    def watch(self) -> Iterator[Event]:
        print("manual mode: n=start  s=stop  Ctrl+D=quit")
        while True:
            try:
                line = input("> ").strip().lower()
            except EOFError:
                return
            now = time.monotonic()
            if line in ("n", "new", "start"):
                yield MeetingEvent(MeetingEventKind.STARTED, now)
            elif line in ("s", "stop", "end"):
                yield MeetingEvent(MeetingEventKind.ENDED, now)
                yield TimePassed(now + self._debounce + 0.1)
