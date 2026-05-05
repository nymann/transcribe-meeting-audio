"""CLI: detect → record → diarize → identify-from-bank → transcribe → write file.

Default subcommand `record` (run with no args) keeps watching for meetings.
`label <meeting-id> SPEAKER_00=alex ...` enrolls speakers from a finished meeting.
"""
import argparse
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from transcribe_meeting_audio.adapters.call_context.bundle_id import (
    BundleIdCallContext,
)
from transcribe_meeting_audio.adapters.call_context.unknown import UnknownCallContext
from transcribe_meeting_audio.adapters.device_registry.static import (
    StaticDeviceRegistry,
)
from transcribe_meeting_audio.adapters.diarization_log import (
    load_diarization,
    save_diarization,
)
from transcribe_meeting_audio.adapters.diarizer.identifying import IdentifyingDiarizer
from transcribe_meeting_audio.adapters.diarizer.pyannote import PyannoteDiarizer
from transcribe_meeting_audio.adapters.event_source.coreaudio_mic import (
    CoreAudioMicDetector,
)
from transcribe_meeting_audio.adapters.event_source.keyboard import KeyboardEventSource
from transcribe_meeting_audio.adapters.session.wav_session_factory import (
    WavSessionFactory,
)
from transcribe_meeting_audio.adapters.speaker_bank.json_file import JsonFileSpeakerBank
from transcribe_meeting_audio.adapters.speaker_embedder.pyannote import PyannoteEmbedder
from transcribe_meeting_audio.adapters.transcriber.parakeet_mlx import (
    ParakeetTranscriber,
)
from transcribe_meeting_audio.adapters.transcript_polisher.mlx_lm import (
    MlxLmTranscriptPolisher,
)
from transcribe_meeting_audio.application.label_meeting import LabelMeeting
from transcribe_meeting_audio.application.record_meeting import RecordMeeting
from transcribe_meeting_audio.application.transcribe_meeting import TranscribeMeeting
from transcribe_meeting_audio.domain.audio import AudioTrack, InputDevice
from transcribe_meeting_audio.domain.meeting import MeetingTranscript

OUTPUT_DIR = Path.home() / "Recordings" / "transcribe-meeting"
BANK_PATH = Path.home() / ".config" / "transcribe-meeting" / "speakers.json"


def _format_ts(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"


def _format_markdown(transcript: MeetingTranscript, started_at: datetime) -> str:
    header = (
        f"# {transcript.label} — {started_at:%Y-%m-%d %H:%M} "
        f"({transcript.duration:.0f}s)\n\n"
    )
    body = "\n".join(
        f"[{_format_ts(s.start)}] {s.speaker}: {s.text}"
        for s in transcript.segments
    )
    return header + body + "\n"


def _rewrite_transcript(transcript_path: Path, renames: dict[str, str]) -> None:
    if not transcript_path.exists():
        return
    text = transcript_path.read_text()
    for old, new in renames.items():
        text = text.replace(f"] {old}: ", f"] {new}: ")
    transcript_path.write_text(text)


def _meeting_paths(meeting_id: str) -> tuple[Path, Path, Path]:
    """Return (loopback_wav, diarization_json, transcript_md) for a meeting id."""
    if meeting_id.isdigit():
        stem = f"meeting-{meeting_id}"
    else:
        stem = meeting_id  # full stem like "meeting-1"
    return (
        OUTPUT_DIR / f"{stem}-loopback.wav",
        OUTPUT_DIR / f"{stem}-diarization.json",
        OUTPUT_DIR / f"{stem}-transcript.md",
    )


def _status_loop(sessions, stop: threading.Event, interval: float = 3.0) -> None:
    """Print a single overwriting status line while a meeting is being recorded."""
    started_at: float | None = None
    while not stop.wait(timeout=interval):
        mic = sessions.active_mic
        loop = sessions.active_loopback
        if mic is None or loop is None:
            started_at = None
            continue
        if started_at is None:
            started_at = time.monotonic()
        elapsed = time.monotonic() - started_at
        print(
            f"\r  recording {elapsed:5.0f}s | mic {mic.seconds_captured:5.1f}s "
            f"| loopback {loop.seconds_captured:5.1f}s",
            end="",
            flush=True,
        )


def _ask_headcount(skip: bool) -> int | None:
    if skip:
        return None
    try:
        response = input("How many people were in the call? [Enter to skip]: ").strip()
    except EOFError:
        return None
    if not response:
        return None
    try:
        n = int(response)
    except ValueError:
        print(f"  '{response}' isn't a number — using auto-detect")
        return None
    return max(1, n)


def _record(args: argparse.Namespace) -> int:
    print("Loading Parakeet model...")
    transcriber = ParakeetTranscriber()
    transcribe_meeting = TranscribeMeeting(
        transcriber=transcriber, self_speaker="kristian", other_speaker="other"
    )

    polisher = None
    if args.polish:
        print(f"Loading polish model {args.polish_model}...")
        try:
            polisher = MlxLmTranscriptPolisher(model_id=args.polish_model)
        except Exception as e:
            print(f"  Polish unavailable: {e}")
            polisher = None

    diarizer = None
    embedder = None
    bank_repo = JsonFileSpeakerBank(BANK_PATH)
    bank = bank_repo.load()
    print(f"Loaded {len(bank.speakers)} enrolled speaker(s) from {BANK_PATH}")

    print("Loading pyannote diarization pipeline...")
    try:
        base_diarizer = PyannoteDiarizer(
            num_speakers=args.speakers, max_speakers=args.max_speakers
        )
    except Exception as e:
        print(f"  Diarization unavailable: {e}")
        print("  Continuing without speaker labels.")
        base_diarizer = None

    if base_diarizer is not None:
        try:
            embedder = PyannoteEmbedder()
        except Exception as e:
            print(f"  Embedder unavailable ({e}); enrollment-based identification disabled.")
            embedder = None
        if embedder is not None:
            diarizer = IdentifyingDiarizer(base=base_diarizer, embedder=embedder, bank=bank)
        else:
            diarizer = base_diarizer

    if args.manual:
        events = KeyboardEventSource()
        context = UnknownCallContext()
    else:
        detector = CoreAudioMicDetector(poll_interval=0.5)
        events = detector
        context = BundleIdCallContext(detector)

    sessions = WavSessionFactory(output_dir=OUTPUT_DIR)
    recorder = RecordMeeting(
        events=events,
        context=context,
        registry=StaticDeviceRegistry(InputDevice(id="default", name="Default Input")),
        sessions=sessions,
    )
    if not args.manual:
        print(f"Watching microphone... recordings -> {OUTPUT_DIR}. Ctrl+C to stop.")

    status_stop = threading.Event()
    status_thread = threading.Thread(
        target=_status_loop, args=(sessions, status_stop), daemon=True
    )
    status_thread.start()

    try:
        for meeting in recorder.run():
            print()  # finalize the in-progress status line
            wall_clock = datetime.now()
            print(f"=== meeting finalized: label={meeting.label} ===")

            speaker_turns: tuple = ()
            if diarizer is not None:
                headcount = _ask_headcount(args.no_ask)
                hint = f" (max={headcount})" if headcount else ""
                print(f"Diarizing loopback{hint}...")
                speaker_turns = tuple(
                    diarizer.diarize(meeting.loopback_track, max_speakers=headcount)
                )
                stem = meeting.mic_track.path.stem.removesuffix("-mic")
                save_diarization(OUTPUT_DIR / f"{stem}-diarization.json", speaker_turns)

            print("Transcribing both tracks...")
            transcript = transcribe_meeting.transcribe(meeting, speaker_turns)
            stem = meeting.mic_track.path.stem.removesuffix("-mic")
            out_path = OUTPUT_DIR / f"{stem}-transcript.md"
            raw_markdown = _format_markdown(transcript, wall_clock)
            out_path.write_text(raw_markdown)
            print(f"Wrote {out_path}")

            if polisher is not None:
                print("Polishing transcript...")
                try:
                    polished = polisher.polish(raw_markdown)
                    polished_path = OUTPUT_DIR / f"{stem}-transcript-polished.md"
                    polished_path.write_text(polished)
                    print(f"Wrote {polished_path}")
                except Exception as e:
                    print(f"  Polish failed: {e}")

            print()
            for s in transcript.segments:
                print(f"[{_format_ts(s.start)}] {s.speaker}: {s.text}")
            print()
    except KeyboardInterrupt:
        print()
    finally:
        status_stop.set()
    return 0


def _label(args: argparse.Namespace) -> int:
    loopback_path, diarization_path, transcript_path = _meeting_paths(args.meeting_id)
    if not loopback_path.exists():
        print(f"loopback wav not found: {loopback_path}")
        return 1
    if not diarization_path.exists():
        print(f"diarization json not found: {diarization_path}")
        return 1

    labels: dict[str, str] = {}
    for pair in args.labels:
        if "=" not in pair:
            print(f"bad label '{pair}', expected SPEAKER_NN=name")
            return 2
        key, value = pair.split("=", 1)
        labels[key.strip()] = value.strip()

    diarization = load_diarization(diarization_path)
    track = AudioTrack(path=loopback_path, start_at=0.0, end_at=0.0)

    print("Loading pyannote embedder...")
    embedder = PyannoteEmbedder()
    bank_repo = JsonFileSpeakerBank(BANK_PATH)
    label_meeting = LabelMeeting(embedder=embedder, bank_repo=bank_repo)

    applied = label_meeting.label(track, diarization, labels)
    print(f"Enrolled {len(applied)} speaker(s) -> {BANK_PATH}")
    for speaker_id, name in applied.items():
        print(f"  {speaker_id} -> {name}")

    _rewrite_transcript(transcript_path, applied)
    if transcript_path.exists():
        print(f"Updated {transcript_path}")
    return 0


def _speakers(args: argparse.Namespace) -> int:
    bank_repo = JsonFileSpeakerBank(BANK_PATH)
    bank = bank_repo.load()
    if args.action == "list":
        if not bank.speakers:
            print("No enrolled speakers.")
        for s in bank.speakers:
            print(s.name)
        return 0
    if args.action == "forget":
        bank.remove(args.name)
        bank_repo.save(bank)
        print(f"Forgot {args.name}")
        return 0
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(prog="transcribe-meeting")
    sub = parser.add_subparsers(dest="command")

    p_record = sub.add_parser("record", help="watch for meetings and transcribe them")
    p_record.add_argument("--manual", action="store_true",
                          help="drive meetings from stdin (n=start, s=stop)")
    p_record.add_argument("--speakers", type=int, default=None,
                          help="exact number of remote speakers")
    p_record.add_argument("--max-speakers", type=int, default=None,
                          help="upper bound on auto-detected speakers (default 8)")
    p_record.add_argument("--polish", action="store_true",
                          help="run an LLM pass to fix ASR errors using context")
    p_record.add_argument("--polish-model", default="mlx-community/Qwen2.5-7B-Instruct-4bit",
                          help="MLX-LM model id for the polish step")
    p_record.add_argument("--no-ask", action="store_true",
                          help="don't prompt for headcount after each meeting")
    p_record.set_defaults(func=_record)

    p_label = sub.add_parser("label", help="enroll speakers from a finished meeting")
    p_label.add_argument("meeting_id", help="e.g. '1' or 'meeting-1'")
    p_label.add_argument("labels", nargs="+", help="SPEAKER_00=alex SPEAKER_01=jamie ...")
    p_label.set_defaults(func=_label)

    p_speakers = sub.add_parser("speakers", help="manage the enrolled-speakers bank")
    sp_sub = p_speakers.add_subparsers(dest="action", required=True)
    sp_sub.add_parser("list", help="list enrolled speakers")
    p_forget = sp_sub.add_parser("forget", help="remove a speaker")
    p_forget.add_argument("name")
    p_speakers.set_defaults(func=_speakers)

    # Default to "record" if no subcommand given (keeps the old `transcribe-meeting` invocation working).
    args = parser.parse_args()
    if args.command is None:
        args = parser.parse_args(["record", *sys.argv[1:]])

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
