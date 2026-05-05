import re

import pytest
from pytest_bdd import given, parsers, then, when

from transcribe_meeting_audio.application.record_meeting import RecordMeeting
from transcribe_meeting_audio.domain.audio import InputDevice
from transcribe_meeting_audio.domain.events import (
    DeviceChanged,
    MeetingEvent,
    MeetingEventKind,
)
from transcribe_meeting_audio.domain.meeting import CallApp
from tests.fakes.recording_session_factory import RecordingSessionFactory
from tests.fakes.scripted_call_context import ScriptedCallContext
from tests.fakes.scripted_device_registry import ScriptedDeviceRegistry
from tests.fakes.scripted_event_source import ScriptedEventSource


@pytest.fixture
def context() -> dict:
    return {}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-system",
        action="store_true",
        default=False,
        help="run tests marked @pytest.mark.system (touch macOS APIs)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-system"):
        return
    skip = pytest.mark.skip(reason="needs --run-system")
    for item in items:
        if "system" in item.keywords:
            item.add_marker(skip)


def _device(name: str) -> InputDevice:
    return InputDevice(id=name.lower().replace(" ", "-"), name=name)


def _ensure_run(context: dict) -> None:
    if "meetings" in context:
        return
    use_case = RecordMeeting(
        events=context["events"],
        context=context["call_context"],
        registry=context["registry"],
        sessions=context["sessions"],
    )
    context["meetings"] = list(use_case.run())


@given("no recording is in progress")
def _idle(context: dict) -> None:
    context["events"] = ScriptedEventSource()
    context["call_context"] = ScriptedCallContext(CallApp.UNKNOWN)
    context["sessions"] = RecordingSessionFactory()


@given(parsers.parse('the input device is "{name}"'))
def _initial_device(context: dict, name: str) -> None:
    context["registry"] = ScriptedDeviceRegistry(_device(name))


@given(parsers.parse('"{app}" is the running call app'))
def _running_call_app(context: dict, app: str) -> None:
    context["call_context"].set(CallApp(app))


@given("no call app is running")
def _no_call_app(context: dict) -> None:
    context["call_context"].set(CallApp.UNKNOWN)


@when(parsers.parse(
    "the microphone-in-use detector reports started at time {at:f}"
))
def _started(context: dict, at: float) -> None:
    context["events"].emit(MeetingEvent(kind=MeetingEventKind.STARTED, at=at))


@when(parsers.parse(
    "the microphone-in-use detector reports ended at time {at:f}"
))
def _ended(context: dict, at: float) -> None:
    context["events"].emit(MeetingEvent(kind=MeetingEventKind.ENDED, at=at))


@when(parsers.parse(
    'the input device changes to "{name}" at time {at:f}'
))
def _input_changed(context: dict, name: str, at: float) -> None:
    context["events"].emit(DeviceChanged(device=_device(name), at=at))


@then(parsers.parse("{count:d} meeting is recorded"))
@then(parsers.parse("{count:d} meetings are recorded"))
def _count(context: dict, count: int) -> None:
    _ensure_run(context)
    assert len(context["meetings"]) == count, context["meetings"]


@then("the mic track is finalized")
def _mic_finalized(context: dict) -> None:
    _ensure_run(context)
    assert context["sessions"].mic_sessions[0].finalized


@then("the loopback track is finalized")
def _loopback_finalized(context: dict) -> None:
    _ensure_run(context)
    assert context["sessions"].loopback_sessions[0].finalized


@then(parsers.parse('meeting {index:d} is labelled "{label}"'))
def _labelled(context: dict, index: int, label: str) -> None:
    _ensure_run(context)
    assert context["meetings"][index - 1].label == CallApp(label)


@then(parsers.parse(
    "the mic track spans from {start:f} to {end:f} seconds"
))
def _mic_span(context: dict, start: float, end: float) -> None:
    _ensure_run(context)
    track = context["meetings"][0].mic_track
    assert track.start_at == start
    assert track.end_at == end


@then(parsers.parse(
    "the loopback track spans from {start:f} to {end:f} seconds"
))
def _loopback_span(context: dict, start: float, end: float) -> None:
    _ensure_run(context)
    track = context["meetings"][0].loopback_track
    assert track.start_at == start
    assert track.end_at == end


@then(parsers.re(r"the mic session used (?P<sequence>.+)"))
def _mic_session_devices(context: dict, sequence: str) -> None:
    _ensure_run(context)
    expected = re.findall(r'"([^"]+)"', sequence)
    actual = context["sessions"].mic_sessions[0].device_names()
    assert actual == expected, f"expected {expected}, got {actual}"
