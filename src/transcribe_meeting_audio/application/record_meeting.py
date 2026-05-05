from collections.abc import Iterator
from dataclasses import dataclass

from transcribe_meeting_audio.domain.events import (
    DeviceChanged,
    MeetingEvent,
    MeetingEventKind,
    TimePassed,
)
from transcribe_meeting_audio.domain.meeting import CallApp, Meeting
from transcribe_meeting_audio.ports.call_context import CallContext
from transcribe_meeting_audio.ports.device_registry import DeviceRegistry
from transcribe_meeting_audio.ports.event_source import EventSource
from transcribe_meeting_audio.ports.loopback_session import LoopbackSession
from transcribe_meeting_audio.ports.mic_session import MicSession
from transcribe_meeting_audio.ports.session_factory import SessionFactory


@dataclass
class _Active:
    mic: MicSession
    loopback: LoopbackSession
    label: CallApp
    pending_stop_at: float | None = None


class RecordMeeting:
    def __init__(
        self,
        events: EventSource,
        context: CallContext,
        registry: DeviceRegistry,
        sessions: SessionFactory,
        debounce_seconds: float = 2.0,
    ) -> None:
        self._events = events
        self._context = context
        self._registry = registry
        self._sessions = sessions
        self._debounce = debounce_seconds

    def run(self) -> Iterator[Meeting]:
        active: _Active | None = None
        last_at: float = 0.0

        for event in self._events.watch():
            last_at = event.at
            match event:
                case MeetingEvent(kind=MeetingEventKind.STARTED, at=at):
                    if active is not None and active.pending_stop_at is not None:
                        gap = at - active.pending_stop_at
                        if gap < self._debounce:
                            print("  resuming meeting (debounce)")
                            active.pending_stop_at = None
                            continue
                        print("  finalizing previous meeting (new one starting)")
                        yield self._finalize(active, active.pending_stop_at)
                        active = None
                    if active is None:
                        print(f"  starting meeting at t={at:.1f}")
                        active = self._begin(at)
                case MeetingEvent(kind=MeetingEventKind.ENDED, at=at):
                    if active is not None:
                        print(f"  pausing meeting at t={at:.1f} (awaiting debounce)")
                        active.pending_stop_at = at
                case DeviceChanged(device=d, at=at):
                    if active is not None:
                        print(f"  switching mic to {d.name!r} at t={at:.1f}")
                        active.mic.switch_to(d, at)
                case TimePassed(at=at):
                    if (
                        active is not None
                        and active.pending_stop_at is not None
                        and at - active.pending_stop_at >= self._debounce
                    ):
                        print(f"  finalizing meeting at t={active.pending_stop_at:.1f}")
                        yield self._finalize(active, active.pending_stop_at)
                        active = None

        if active is not None:
            stop_at = active.pending_stop_at if active.pending_stop_at is not None else last_at
            print(f"  finalizing meeting (stream ended) at t={stop_at:.1f}")
            yield self._finalize(active, stop_at)

    def _begin(self, at: float) -> _Active:
        label = self._context.identify()
        device = self._registry.current_input()
        mic = self._sessions.mic()
        mic.start(device, at)
        loopback = self._sessions.loopback()
        loopback.start(at)
        return _Active(mic=mic, loopback=loopback, label=label)

    def _finalize(self, active: _Active, at: float) -> Meeting:
        return Meeting(
            label=active.label,
            mic_track=active.mic.stop(at),
            loopback_track=active.loopback.stop(at),
        )
