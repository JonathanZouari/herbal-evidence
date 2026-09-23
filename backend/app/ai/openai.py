"""OpenAI adapter over plain HTTPS (Responses API, strict JSON-schema output). No SDK: the SafeClient allowlist
applies and nothing is stored on the provider side (store=false)."""

import json

from pydantic import ValidationError

from app.ai import prompt
from app.ai.provider import DraftInput, ProviderError
from app.ai.schema import Analysis, HerbGuess, analysis_json_schema, herb_guess_json_schema
from app.research.http import FetchError, SafeClient

URL = "https://api.openai.com/v1/responses"
IDENTIFY_TIMEOUT = 60   # the user is waiting on the form


class OpenAIProvider:
    name = "openai"

    def __init__(self, client: SafeClient, api_key: str, model: str, timeout: float = 90):
        self._client, self._key, self.model, self._timeout = client, api_key, model, timeout

    def __repr__(self) -> str:   # never leak the key through logs/tracebacks
        return f"OpenAIProvider(model={self.model!r})"

    def _post(self, body: dict, timeout: float) -> bytes:
        try:
            r = self._client.post_json(URL, body, timeout=timeout, headers={"Authorization": f"Bearer {self._key}"})
        except FetchError as e:
            if e.code == "upstream_rejected" and e.detail in ("http 401", "http 403"):
                raise ProviderError("ai_auth_failed", False, e.detail) from None
            if e.retryable:
                raise ProviderError("ai_unavailable", True, e.code) from None
            raise ProviderError("ai_request_rejected", False, e.detail or e.code) from None
        return r.content

    def request_body(self, inp: DraftInput) -> dict:
        refs = [s.ref for s in inp.sources[:prompt.MAX_SOURCES]]
        return {
            "model": self.model,
            "instructions": prompt.INSTRUCTIONS,
            "input": prompt.build_input(inp),
            "text": {"format": {"type": "json_schema", "name": "evidence_draft_v1", "strict": True,
                                "schema": analysis_json_schema(refs)}},
            "store": False,
        }

    def generate(self, inp: DraftInput) -> Analysis:
        raw = self._post(self.request_body(inp), self._timeout)
        return parse_response(raw, {s.ref for s in inp.sources[:prompt.MAX_SOURCES]})

    def identify_request_body(self, image_data_url: str, herbs: list[dict]) -> dict:
        return {
            "model": self.model,
            "instructions": prompt.IDENTIFY_INSTRUCTIONS,
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": prompt.build_identify_input(herbs)},
                {"type": "input_image", "image_url": image_data_url},
            ]}],
            "text": {"format": {"type": "json_schema", "name": "herb_guess_v1", "strict": True,
                                "schema": herb_guess_json_schema([str(h["id"]) for h in herbs])}},
            "store": False,
        }

    def identify_herb(self, image_data_url: str, herbs: list[dict]) -> HerbGuess:
        raw = self._post(self.identify_request_body(image_data_url, herbs), min(self._timeout, IDENTIFY_TIMEOUT))
        return parse_identify_response(raw, {str(h["id"]) for h in herbs})


def _output_text(raw: bytes) -> str:
    try:
        data = json.loads(raw)
    except ValueError:
        raise ProviderError("ai_bad_output", True, "response is not json") from None
    if data.get("status") == "incomplete":
        raise ProviderError("ai_bad_output", True, "incomplete response")
    text = None
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") == "refusal":
                raise ProviderError("ai_refused", False)
            if part.get("type") == "output_text":
                text = part.get("text")
    if not text:
        raise ProviderError("ai_bad_output", True, "no output_text")
    return text


def parse_response(raw: bytes, refs: set[str]) -> Analysis:
    try:
        analysis = Analysis.model_validate_json(_output_text(raw))
    except ValidationError as e:
        raise ProviderError("ai_bad_output", True, f"{e.error_count()} schema errors") from None
    bad = {f.source_ref for f in (*analysis.appetite.findings, *(f for s in analysis.secondary for f in s.findings))} - refs
    if bad:
        raise ProviderError("ai_bad_output", True, "cites unknown sources")
    return analysis


def parse_identify_response(raw: bytes, ids: set[str]) -> HerbGuess:
    try:
        guess = HerbGuess.model_validate_json(_output_text(raw))
    except ValidationError as e:
        raise ProviderError("ai_bad_output", True, f"{e.error_count()} schema errors") from None
    if guess.match != "none" and guess.match not in ids:
        raise ProviderError("ai_bad_output", True, "unknown herb id")
    return guess
