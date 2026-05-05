# transcribe-meeting-audio

Records meetings on macOS and ingests transcripts. Detects when any app opens the microphone, captures mic + system loopback as two tracks, survives device changes mid-meeting, transcribes with Parakeet, diarizes with pyannote, and (optionally) polishes the transcript with a local MLX LLM.

## Prerequisites

- macOS 14.4+ on Apple Silicon. Loopback uses CoreAudio Process Tap (14.4+); transcription and the polish step run on MLX.
- Permissions for your terminal: **Microphone** and **System Audio Recording** (System Settings → Privacy & Security). Without these, mic detection and loopback capture fail silently or with a permission error.
- For diarization, a Hugging Face account:
  - `export HF_TOKEN=...` (or run `huggingface-cli login` once)
  - Accept the gated-model terms while signed in to HF:
    - https://huggingface.co/pyannote/speaker-diarization-3.1
    - https://huggingface.co/pyannote/segmentation-3.0
    - https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM
  - Without these, the CLI keeps running but writes transcripts without speaker labels.
- Parakeet (ASR) and the polish model download on first run with no token.

## Install

```sh
just install
```

That installs the dependencies, registers `transcribe-meeting` as a global `uv tool` (so you can run it from anywhere), and prints how to set up Hugging Face auth if it isn't already.

If you don't want everything, install manually with the extras you need (`record`, `transcribe`, `diarize`, `polish`) — for example, drop `polish` if you don't want a 7B model on disk:

```sh
uv sync --extra record --extra transcribe --extra diarize
uv tool install --force .
```

## Usage

### `record` — watch for meetings and transcribe them

The default subcommand. Watches CoreAudio for any process opening the mic, then captures **two** tracks for the duration of the meeting:

- `meeting-N-mic.wav` — your microphone
- `meeting-N-loopback.wav` — everything the system played back (i.e. the other participants)

Two tracks instead of one because diarization on a mixed track is much harder and because it lets the transcriber attribute "you" vs. "them" cleanly. Output lands in `~/Recordings/transcribe-meeting/` along with a `meeting-N-transcript.md`.

```sh
transcribe-meeting record
```

Flags:

- `--manual` — skip mic detection; press `n` to start a meeting, `s` to stop. Useful when you want to record something that isn't routed through a normal app.
- `--speakers N` / `--max-speakers N` — pin or cap the diarizer's speaker count when you know it (much more accurate than letting pyannote guess).
- `--no-ask` — don't prompt for the headcount after each meeting.
- `--polish` — run a local LLM pass over the transcript (see below).

### `label` — put real names on speakers

Diarization gives you `SPEAKER_00`, `SPEAKER_01`, etc. `label` enrolls those speakers from a finished meeting into a local speaker bank (`~/.config/transcribe-meeting/speakers.json`), rewrites the transcript with the real names, and uses the embeddings to recognize the same people automatically in future meetings.

```sh
transcribe-meeting label 1 SPEAKER_00=alex SPEAKER_01=jamie
```

Manage the bank:

```sh
transcribe-meeting speakers list
transcribe-meeting speakers forget alex
```

### `--polish` — clean up ASR errors with a local LLM

ASR output is usually right but has the occasional homophone, dropped word, or mangled name. `--polish` runs the raw transcript through a local MLX-LM model (default `mlx-community/Qwen2.5-7B-Instruct-4bit`) to fix those using surrounding context, and writes a separate `meeting-N-transcript-polished.md` so you always keep the raw version.

```sh
transcribe-meeting record --polish
transcribe-meeting record --polish --polish-model mlx-community/<other-model>
```

It's a separate file, not in-place, because the polisher can occasionally hallucinate — keeping the raw transcript means you can always diff.

## Tests

```sh
just test
```
