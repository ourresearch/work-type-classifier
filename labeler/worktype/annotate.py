"""Annotate a work's type with Claude (Opus 4.8), constrained to the canonical taxonomy via structured outputs."""
import json

import anthropic

from .taxonomy import OUTPUT_SCHEMA, system_prompt

DEFAULT_MODEL = "claude-opus-4-8"


def make_client(max_retries: int = 8) -> anthropic.Anthropic:
    """One shared, thread-safe client. Reads ANTHROPIC_API_KEY (or an `ant auth login` profile) from the env.
    High max_retries so the SDK rides out 429/5xx under heavy concurrency with exponential backoff."""
    return anthropic.Anthropic(max_retries=max_retries)


class Annotator:
    def __init__(self, client: anthropic.Anthropic, *, model: str = DEFAULT_MODEL,
                 effort: str = "medium", max_tokens: int = 4096):
        self.client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        # Build the (large, static) taxonomy system prompt once; cache it so concurrent calls reuse the prefix.
        self._system = [{
            "type": "text",
            "text": system_prompt(),
            "cache_control": {"type": "ephemeral"},
        }]

    def annotate(self, signals: dict) -> dict:
        """Return {type, is_broken, confidence, reason} (+ _meta on error). Never raises for ordinary API errors."""
        user = (
            "Classify this Crossref work. Signals (JSON; some fields may be null):\n\n"
            + json.dumps(signals, ensure_ascii=False, indent=1)
        )
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                thinking={"type": "adaptive"},
                output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
                               "effort": self.effort},
                system=self._system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as e:
            return {"type": None, "is_broken": None, "confidence": None,
                    "reason": None, "_error": f"{type(e).__name__}: {getattr(e, 'message', e)}"}

        if resp.stop_reason == "refusal":
            return {"type": None, "is_broken": None, "confidence": None,
                    "reason": None, "_error": "refusal"}

        text = next((b.text for b in resp.content if b.type == "text"), None)
        if not text:
            return {"type": None, "is_broken": None, "confidence": None,
                    "reason": None, "_error": "no-text-block"}
        try:
            out = json.loads(text)
        except json.JSONDecodeError:
            return {"type": None, "is_broken": None, "confidence": None,
                    "reason": None, "_error": "bad-json", "_raw": text[:300]}
        out["_request_id"] = resp._request_id
        u = resp.usage
        out["_usage"] = {
            "in": u.input_tokens or 0,
            "out": u.output_tokens or 0,
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
        }
        return out
