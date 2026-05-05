# transcribe-meeting-audio

Records meetings on macOS and ingests transcripts. Detects when any app opens the microphone, captures mic + system loopback as two tracks, survives device changes mid-meeting, and hands the result off to a transcription pipeline.

Round 1: ports, use case, BDD tests against fakes. Real adapters (CoreAudio, process detection, Parakeet, pyannote) come in round 2.

## Architecture

Hexagonal. The core use case is `RecordMeeting`, which consumes events from these ports:

- `EventSource` — meeting/device/time events as a single stream
- `CallContext` — best-effort identification of the active app (Teams, Discord, ...)
- `DeviceRegistry` — current input device, used at meeting start and after a disconnect
- `SessionFactory` — produces a fresh `MicSession` and `LoopbackSession` per meeting

Adapters live under `src/transcribe_meeting_audio/adapters/` (none yet).

## Run

```sh
uv sync
uv run pytest
```
