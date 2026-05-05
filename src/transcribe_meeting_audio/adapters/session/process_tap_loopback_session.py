"""Loopback capture via CoreAudio process tap (macOS 14.4+).

Creates a stereo global tap of all system audio output, wraps it in a private
aggregate device, and reads samples directly with AudioDeviceIOProcID. No
BlackHole or other virtual-driver install required — the tap is created and
destroyed within the process's lifetime.

Pyobjc is used for the parts that need an Obj-C class (CATapDescription) or
CFDictionary inputs. ctypes is used for the property reads and the IOProc
callback, where pyobjc's auto-wrapping struggles with variable-size out arrays.
"""
import ctypes
import ctypes.util
import threading
import uuid
from pathlib import Path

import CoreAudio
import numpy as np
import objc
import soundfile as sf

from transcribe_meeting_audio.domain.audio import AudioTrack


def _fcc(s: str) -> int:
    return int.from_bytes(s.encode(), "big")


_GLOBAL = _fcc("glob")
_NOMINAL_SAMPLE_RATE = _fcc("nsrt")
_TAP_UID = _fcc("tuid")
_CFSTRING_UTF8 = 0x08000100


class _Address(ctypes.Structure):
    _fields_ = [("sel", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("element", ctypes.c_uint32)]


class _AudioBuffer(ctypes.Structure):
    _fields_ = [
        ("mNumberChannels", ctypes.c_uint32),
        ("mDataByteSize", ctypes.c_uint32),
        ("mData", ctypes.c_void_p),
    ]


class _AudioBufferList(ctypes.Structure):
    _fields_ = [
        ("mNumberBuffers", ctypes.c_uint32),
        ("mBuffers", _AudioBuffer * 1),
    ]


class _AudioTimeStamp(ctypes.Structure):
    _fields_ = [
        ("mSampleTime", ctypes.c_double),
        ("mHostTime", ctypes.c_uint64),
        ("mRateScalar", ctypes.c_double),
        ("mWordClockTime", ctypes.c_uint64),
        ("mSMPTETime", ctypes.c_uint8 * 24),
        ("mFlags", ctypes.c_uint32),
        ("mReserved", ctypes.c_uint32),
    ]


_ca = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
_cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))

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

_IOProcType = ctypes.CFUNCTYPE(
    ctypes.c_int32,
    ctypes.c_uint32,
    ctypes.POINTER(_AudioTimeStamp),
    ctypes.POINTER(_AudioBufferList),
    ctypes.POINTER(_AudioTimeStamp),
    ctypes.POINTER(_AudioBufferList),
    ctypes.POINTER(_AudioTimeStamp),
    ctypes.c_void_p,
)
_ca.AudioDeviceCreateIOProcID.restype = ctypes.c_int32
_ca.AudioDeviceCreateIOProcID.argtypes = [
    ctypes.c_uint32,
    _IOProcType,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
]
_ca.AudioDeviceStart.restype = ctypes.c_int32
_ca.AudioDeviceStart.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
_ca.AudioDeviceStop.restype = ctypes.c_int32
_ca.AudioDeviceStop.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
_ca.AudioDeviceDestroyIOProcID.restype = ctypes.c_int32
_ca.AudioDeviceDestroyIOProcID.argtypes = [ctypes.c_uint32, ctypes.c_void_p]


def _read_cfstring(obj_id: int, selector: int) -> str | None:
    addr = _Address(selector, _GLOBAL, 0)
    cfstr = ctypes.c_void_p(0)
    size = ctypes.c_uint32(8)
    if _ca.AudioObjectGetPropertyData(
        obj_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(cfstr)
    ) != 0 or not cfstr.value:
        return None
    buf = ctypes.create_string_buffer(512)
    if not _cf.CFStringGetCString(cfstr.value, buf, 512, _CFSTRING_UTF8):
        return None
    return buf.value.decode("utf-8")


def _read_sample_rate(obj_id: int) -> float:
    addr = _Address(_NOMINAL_SAMPLE_RATE, _GLOBAL, 0)
    sr = ctypes.c_double(0)
    size = ctypes.c_uint32(8)
    if _ca.AudioObjectGetPropertyData(
        obj_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(sr)
    ) != 0:
        return 48000.0
    return sr.value


class ProcessTapLoopbackSession:
    """Records all non-self system audio output to a mono WAV at the tap's native rate."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._start_at: float | None = None
        self._tap_id: int | None = None
        self._agg_id: int | None = None
        self._proc_id: ctypes.c_void_p | None = None
        self._callback = None  # keep CFUNCTYPE wrapper alive
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._sample_rate: float = 48000.0
        self.is_recording: bool = False

    @property
    def seconds_captured(self) -> float:
        with self._lock:
            total = sum(c.shape[0] for c in self._chunks)
        # stereo interleaved: two samples per frame
        return total / 2 / self._sample_rate

    def start(self, at: float) -> None:
        self._start_at = at
        self.is_recording = True
        CATapDescription = objc.lookUpClass("CATapDescription")
        desc = CATapDescription.alloc().initStereoGlobalTapButExcludeProcesses_([])
        status, tap_id = CoreAudio.AudioHardwareCreateProcessTap(desc, None)
        if status != 0:
            raise RuntimeError(f"AudioHardwareCreateProcessTap failed: {status}")
        self._tap_id = tap_id

        tap_uid = _read_cfstring(tap_id, _TAP_UID)
        if tap_uid is None:
            self._teardown()
            raise RuntimeError("could not read tap UID")

        agg_dict = {
            "name": "Transcribe Meeting Loopback",
            "uid": f"com.nymann.transcribe-meeting.{uuid.uuid4()}",
            "private": 1,
            "taps": [{"uid": tap_uid, "drift": 0}],
        }
        status, agg_id = CoreAudio.AudioHardwareCreateAggregateDevice(agg_dict, None)
        if status != 0:
            self._teardown()
            raise RuntimeError(f"AudioHardwareCreateAggregateDevice failed: {status}")
        self._agg_id = agg_id
        self._sample_rate = _read_sample_rate(agg_id)

        def io_proc(in_dev, in_now, in_data, in_time, out_data, out_time, client):
            abl = in_data.contents
            if abl.mNumberBuffers == 0:
                return 0
            buf0 = abl.mBuffers[0]
            if buf0.mData == 0 or buf0.mDataByteSize == 0:
                return 0
            n = buf0.mDataByteSize // 4
            arr = (ctypes.c_float * n).from_address(buf0.mData)
            chunk = np.frombuffer(arr, dtype=np.float32).copy()
            with self._lock:
                self._chunks.append(chunk)
            return 0

        self._callback = _IOProcType(io_proc)
        proc_id = ctypes.c_void_p(0)
        status = _ca.AudioDeviceCreateIOProcID(
            agg_id, self._callback, None, ctypes.byref(proc_id)
        )
        if status != 0:
            self._teardown()
            raise RuntimeError(f"AudioDeviceCreateIOProcID failed: {status}")
        self._proc_id = proc_id

        status = _ca.AudioDeviceStart(agg_id, proc_id)
        if status != 0:
            self._teardown()
            raise RuntimeError(f"AudioDeviceStart failed: {status}")

    def stop(self, at: float) -> AudioTrack:
        assert self._start_at is not None
        self.is_recording = False
        if self._agg_id is not None and self._proc_id is not None:
            _ca.AudioDeviceStop(self._agg_id, self._proc_id)
        self._teardown()

        with self._lock:
            chunks = self._chunks
            self._chunks = []

        if chunks:
            interleaved = np.concatenate(chunks)
            pairs = interleaved.size // 2
            stereo = interleaved[: pairs * 2].reshape(-1, 2)
            mono = stereo.mean(axis=1).astype(np.float32)
        else:
            mono = np.zeros(0, dtype=np.float32)

        if mono.size == 0:
            mono = np.zeros(max(1, int(self._sample_rate * 0.1)), dtype=np.float32)
        sf.write(str(self._path), mono, int(self._sample_rate))
        print(f"    loopback: wrote {mono.shape[0]} frames -> {self._path.name}")
        return AudioTrack(path=self._path, start_at=self._start_at, end_at=at)

    def _teardown(self) -> None:
        if self._agg_id is not None and self._proc_id is not None:
            _ca.AudioDeviceDestroyIOProcID(self._agg_id, self._proc_id)
        if self._agg_id is not None:
            CoreAudio.AudioHardwareDestroyAggregateDevice(self._agg_id)
        if self._tap_id is not None:
            CoreAudio.AudioHardwareDestroyProcessTap(self._tap_id)
        self._tap_id = None
        self._agg_id = None
        self._proc_id = None
        self._callback = None
