"""Try different prompts (and optionally models) on an existing transcript.

Reads ~/Recordings/transcribe-meeting/meeting-1-transcript.md, runs each
(model, prompt) pair, writes outputs to ~/Recordings/transcribe-meeting/experiments/.
"""
import gc
from pathlib import Path

from mlx_lm import generate, load

INPUT_PATH = Path.home() / "Recordings/transcribe-meeting/meeting-1-transcript.md"
OUTPUT_DIR = Path.home() / "Recordings/transcribe-meeting/experiments"


_FORMAT_RULES = """Preserve:
- The markdown format (the `# ...` header line, then `[HH:MM] speaker: text` lines)
- Every speaker label and timestamp, exactly as given
- The same number of segments and speaker turns
- The substance and intent of what was said"""


PROMPTS = {
    "light-cleanup": """You are an expert proofreader cleaning up an ASR transcript of a real conversation.

Preserve:
- The markdown format (the `# ...` header line, then `[HH:MM] speaker: text` lines)
- Every speaker label and timestamp, exactly as given
- The same number of segments and speaker turns
- The substance and intent of what was said

Clean up:
- Filler words: "uh", "um", "you know" (when truly meaningless)
- Stuttered repetitions: "I I think" -> "I think", "he does have he does" -> "he does"
- Homophones, mishearings, and missing punctuation
- Proper-noun capitalization where context makes the name clear

Keep:
- Substantive repetitions and emphasis intact
- Conversational tone — do NOT make it formal
- The original wording for anything you're not actively fixing

Do NOT:
- Paraphrase, summarise, or rewrite for style
- Add, remove, split, or merge segments
- Drop substantive words even if they seem unnecessary
- Add commentary, headers, or metadata

Output ONLY the cleaned transcript in the same markdown format.""",
    "merge-friendly": """You are preparing an ASR transcript for ingestion into a knowledge wiki. The text is a real meeting with stutters, filler words, and minor ASR errors. The reader of the polished output is the meeting participant looking up what was discussed.

Format rules:
- Keep the markdown `# ...` header exactly as given.
- Each output line is `[HH:MM] speaker: text`.
- You MAY merge consecutive segments from the SAME speaker into one segment, using the timestamp of the first merged segment.
- Segments from DIFFERENT speakers must remain as separate segments in time order.
- Never change speaker labels.

Clean up:
- Filler ("uh", "um", "like" as filler, "you know" as filler)
- Stuttered repetitions ("I I" -> "I", "he does have he does" -> "he does")
- Homophones, mishearings, and missing punctuation
- Proper-noun capitalization where context makes the name clear

Keep:
- Substantive repetitions and emphasis intact
- Conversational tone — do NOT make it formal
- Original word choice for everything you're not actively fixing

Do NOT:
- Paraphrase or summarise beyond the cleanup rules above
- Drop substantive words
- Reorder anything
- Add commentary, headers, or metadata

Output ONLY the cleaned transcript.""",
}


MODELS: list[str] = [
    "mlx-community/granite-4.1-3b-8bit",
    "mlx-community/granite-4.1-8b-5bit",
    "mlx-community/Qwen2.5-7B-Instruct-4bit",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_PATH.exists():
        raise SystemExit(f"input not found: {INPUT_PATH}")
    transcript = INPUT_PATH.read_text()
    print(f"input: {INPUT_PATH} ({len(transcript)} chars)")

    for model_id in MODELS:
        slug_model = model_id.split("/")[-1]
        print(f"\n=== loading {model_id} ===")
        model, tokenizer = load(model_id)
        for prompt_name, prompt in PROMPTS.items():
            print(f"  running {prompt_name}...", flush=True)
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript},
            ]
            formatted = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            output = generate(
                model, tokenizer, prompt=formatted, max_tokens=8192, verbose=False
            ).strip()
            out_path = OUTPUT_DIR / f"{slug_model}__{prompt_name}.md"
            out_path.write_text(output + "\n")
            print(f"    -> {out_path}")
        del model, tokenizer
        gc.collect()


if __name__ == "__main__":
    main()
