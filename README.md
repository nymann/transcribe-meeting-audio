# transcribe-meeting-audio

Records meetings on macOS and ingests transcripts. Detects when any app opens the microphone, captures mic + system loopback as two tracks, survives device changes mid-meeting, transcribes with Parakeet, diarizes with pyannote, and (optionally) polishes the transcript with a local MLX LLM.

## Architecture

Hexagonal. Three use cases under `application/`:

- `RecordMeeting` — drives the capture loop from an event stream
- `TranscribeMeeting` — turns finished tracks + diarization into a `MeetingTranscript`
- `LabelMeeting` — enrolls speakers from a finished meeting into the speaker bank

Ports (`ports/`) and their current adapters (`adapters/`):

- `EventSource` — `CoreAudioMicDetector` (auto), `KeyboardEventSource` (`--manual`)
- `CallContext` — `BundleIdCallContext`, `UnknownCallContext`
- `DeviceRegistry` — `StaticDeviceRegistry`
- `SessionFactory` / `MicSession` / `LoopbackSession` — `WavSessionFactory` writes both tracks as WAV
- `Transcriber` — `ParakeetTranscriber` (parakeet-mlx)
- `Diarizer` / `SpeakerEmbedder` / `SpeakerBankRepository` — `PyannoteDiarizer` + `IdentifyingDiarizer` against a `JsonFileSpeakerBank`
- `TranscriptPolisher` — `MlxLmTranscriptPolisher` (optional, behind `--polish`)

BDD specs in `tests/features/` exercise the use cases against fakes in `tests/fakes/`.

## Run

Install with the optional extras you need (record / transcribe / diarize / polish, or `all`):

```sh
uv sync --extra all
```

Watch for meetings — auto-detects when an app opens the mic, records mic + system loopback, and writes a transcript per meeting to `~/Recordings/transcribe-meeting/`:

```sh
uv run transcribe-meeting record
```

Useful flags:

- `--manual` — drive meetings from stdin (`n` = start, `s` = stop) instead of mic auto-detection
- `--speakers N` / `--max-speakers N` — pin or cap the diarizer's speaker count
- `--polish` — run an MLX-LM pass over the transcript (override model with `--polish-model`)
- `--no-ask` — skip the post-meeting headcount prompt

Enroll speakers from a finished meeting (transcript and future meetings get the real names):

```sh
uv run transcribe-meeting label 1 SPEAKER_00=alex SPEAKER_01=jamie
```

Manage the enrolled-speaker bank (stored at `~/.config/transcribe-meeting/speakers.json`):

```sh
uv run transcribe-meeting speakers list
uv run transcribe-meeting speakers forget alex
```

Tests:

```sh
uv run pytest
```
