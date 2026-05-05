"""Detects mic-in-use per-process via CoreAudio's audio process objects (macOS 14+).

For each tick:
  1. Enumerate kAudioHardwarePropertyProcessObjectList.
  2. For each process object, query kAudioProcessPropertyIsRunningInput.
  3. Read its bundle ID (CFString).
  4. Drop bundles in the ignored set (system speech services, dictation tools).
  5. STARTED on rising edge of the remaining set being non-empty; ENDED on falling edge.

The detector remembers which bundles triggered the most recent meeting on
self.last_trigger_bundles, so a sibling CallContext can label the meeting.
"""
import ctypes
import ctypes.util
import time
from collections.abc import Iterator

from transcribe_meeting_audio.domain.events import (
    Event,
    MeetingEvent,
    MeetingEventKind,
    TimePassed,
)


def _fcc(s: str) -> int:
    return int.from_bytes(s.encode(), "big")


_SYSTEM_OBJECT = 1
_SCOPE_GLOBAL = _fcc("glob")
_ELEMENT_MAIN = 0
_PROCESS_OBJECT_LIST = _fcc("prs#")
_PROCESS_IS_RUNNING_INPUT = _fcc("piri")
_PROCESS_BUNDLE_ID = _fcc("pbid")
_CFSTRING_ENCODING_UTF8 = 0x08000100


class _Address(ctypes.Structure):
    _fields_ = [
        ("mSelector", ctypes.c_uint32),
        ("mScope", ctypes.c_uint32),
        ("mElement", ctypes.c_uint32),
    ]


_ca = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
_cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))

_ca.AudioObjectGetPropertyDataSize.restype = ctypes.c_int32
_ca.AudioObjectGetPropertyDataSize.argtypes = [
    ctypes.c_uint32,
    ctypes.POINTER(_Address),
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint32),
]
_ca.AudioObjectGetPropertyData.restype = ctypes.c_int32
_ca.AudioObjectGetPropertyData.argtypes = [
    ctypes.c_uint32,
    ctypes.POINTER(_Address),
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_void_p,
]
_cf.CFStringGetCString.restype = ctypes.c_bool
_cf.CFStringGetCString.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_long,
    ctypes.c_uint32,
]
_cf.CFRelease.argtypes = [ctypes.c_void_p]


DEFAULT_IGNORED_BUNDLES: frozenset[str] = frozenset({
    # Dictation / one-shot voice tools
    "com.pais.handy",
    # macOS speech / accessibility services
    "com.apple.CoreSpeech",
    "com.apple.corespeechd_system",
    "com.apple.accessibility.heard",
    "com.apple.universalaccessd",
    "com.apple.controlcenter",
    # Audio plumbing & continuity that opens the mic without being a meeting
    "com.apple.audiomxd",
    "com.apple.mediaremoted",
    "com.apple.replayd",
    "com.apple.cmio.ContinuityCaptureAgent",
    "com.apple.TelephonyUtilities",
})


def _enumerate_process_objects() -> list[int]:
    addr = _Address(_PROCESS_OBJECT_LIST, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    size = ctypes.c_uint32(0)
    if _ca.AudioObjectGetPropertyDataSize(
        _SYSTEM_OBJECT, ctypes.byref(addr), 0, None, ctypes.byref(size)
    ) != 0 or size.value == 0:
        return []
    n = size.value // 4
    buf = (ctypes.c_uint32 * n)()
    if _ca.AudioObjectGetPropertyData(
        _SYSTEM_OBJECT, ctypes.byref(addr), 0, None, ctypes.byref(size), buf
    ) != 0:
        return []
    return list(buf)


def _process_input_running(obj_id: int) -> bool:
    addr = _Address(_PROCESS_IS_RUNNING_INPUT, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    running = ctypes.c_uint32(0)
    size = ctypes.c_uint32(4)
    if _ca.AudioObjectGetPropertyData(
        obj_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(running)
    ) != 0:
        return False
    return running.value != 0


def _process_bundle_id(obj_id: int) -> str | None:
    addr = _Address(_PROCESS_BUNDLE_ID, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    cfstr = ctypes.c_void_p(0)
    size = ctypes.c_uint32(8)
    if _ca.AudioObjectGetPropertyData(
        obj_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(cfstr)
    ) != 0 or not cfstr.value:
        return None
    try:
        buf = ctypes.create_string_buffer(512)
        if not _cf.CFStringGetCString(cfstr.value, buf, 512, _CFSTRING_ENCODING_UTF8):
            return None
        s = buf.value.decode("utf-8", errors="replace")
        return s or None
    finally:
        _cf.CFRelease(cfstr.value)


def active_input_bundles(
    ignored: frozenset[str] = DEFAULT_IGNORED_BUNDLES,
) -> frozenset[str]:
    out: set[str] = set()
    for obj in _enumerate_process_objects():
        if not _process_input_running(obj):
            continue
        bid = _process_bundle_id(obj)
        if bid is None or bid in ignored:
            continue
        out.add(bid)
    return frozenset(out)


class CoreAudioMicDetector:
    """Per-tick: which non-ignored process bundles are using the mic right now.

    STARTED when that set goes from empty to non-empty; ENDED on the inverse.
    `last_trigger_bundles` exposes the set captured at the most recent STARTED
    so a sibling CallContext can label the meeting.
    """

    def __init__(
        self,
        poll_interval: float = 0.5,
        ignored_bundles: frozenset[str] = DEFAULT_IGNORED_BUNDLES,
    ) -> None:
        self._poll = poll_interval
        self._ignored = ignored_bundles
        self.last_trigger_bundles: frozenset[str] = frozenset()

    def watch(self) -> Iterator[Event]:
        active = False
        while True:
            now = time.monotonic()
            bundles = active_input_bundles(self._ignored)
            now_active = bool(bundles)
            if now_active and not active:
                self.last_trigger_bundles = bundles
                yield MeetingEvent(MeetingEventKind.STARTED, now)
                active = True
            elif not now_active and active:
                yield MeetingEvent(MeetingEventKind.ENDED, now)
                active = False
            yield TimePassed(now)
            time.sleep(self._poll)
