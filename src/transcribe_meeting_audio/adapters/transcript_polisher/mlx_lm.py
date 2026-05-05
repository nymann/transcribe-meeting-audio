"""Local LLM polish via mlx-lm. Default: Qwen 2.5 7B Instruct (4-bit MLX).

Picked empirically: on a real meeting transcript Qwen 2.5 7B was the only
model that cleanly preserved every segment AND fixed every stutter/filler.
Granite 4.1 8B over-merged segments against the prompt; Granite 4.1 3B
under-cleaned. See scripts/experiment_polish.py for the comparison.

Lazy-imports mlx-lm so the CLI can degrade if the polish extra isn't installed.
"""

_SYSTEM_PROMPT = """You are an expert proofreader for automatic speech recognition (ASR) transcripts of conversations.

Correct ASR errors in the transcript below while preserving:
- The exact markdown format (header, then `[HH:MM] speaker: text` lines)
- Every speaker label and timestamp, exactly as given
- The same number of segments and speaker turns
- The substance of what was said

Fix:
- Homophones used wrongly (their/there, write/right)
- Mishearings of proper nouns, names, technical or game terms (use surrounding context)
- Punctuation and obvious dropped/duplicated words

Do NOT:
- Paraphrase, summarise, or rewrite for style
- Add, remove, split, or merge segments
- Translate or "improve" word choice
- Add commentary, explanations, or metadata

Output ONLY the corrected transcript in the same markdown format."""


class MlxLmTranscriptPolisher:
    def __init__(
        self,
        model_id: str = "mlx-community/Qwen2.5-7B-Instruct-4bit",
        max_tokens: int = 8192,
    ) -> None:
        from mlx_lm import load

        self._model, self._tokenizer = load(model_id)
        self._max_tokens = max_tokens

    def polish(self, markdown: str) -> str:
        from mlx_lm import generate

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": markdown},
        ]
        prompt = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        result = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=self._max_tokens,
            verbose=False,
        )
        return result.strip()
