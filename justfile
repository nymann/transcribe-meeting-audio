default: help

help:
    @just --list

# Install deps and register `transcribe-meeting` globally, then check HF auth
install:
    uv sync --extra all
    uv tool install --force .
    @just hf-check

# Verify that a Hugging Face token is available; explain how to set one if not
hf-check:
    #!/usr/bin/env sh
    if [ -n "$HF_TOKEN" ] || [ -n "$HUGGINGFACE_HUB_TOKEN" ] || [ -f "$HOME/.cache/huggingface/token" ]; then
        echo "HF auth: OK"
        exit 0
    fi
    echo "HF token not found. Diarization needs a Hugging Face token."
    if command -v hf >/dev/null 2>&1; then
        echo "  Run: hf auth login"
    elif command -v huggingface-cli >/dev/null 2>&1; then
        echo "  Run: huggingface-cli login"
    else
        echo "  Set HF_TOKEN in your shell, or install the HF CLI (pip install huggingface_hub)."
    fi
    echo "Then accept terms at:"
    echo "  https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "  https://huggingface.co/pyannote/segmentation-3.0"
    echo "  https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM"

test:
    uv run pytest
