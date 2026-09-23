"""Replaceable AI provider (D-008). No key/model -> NullProvider, which fails the job; it never invents content."""

from dataclasses import dataclass
from typing import Protocol

from app.ai.schema import Analysis, HerbGuess
from app.research.http import SafeClient
from app.research.sources import Source
from app.settings import Settings


class ProviderNotConfigured(Exception):
    code = "ai_not_configured"
    retryable = False


class ProviderError(Exception):
    def __init__(self, code: str, retryable: bool, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.retryable, self.detail = code, retryable, detail


@dataclass(frozen=True)
class DraftInput:
    herb: dict                       # name_he / name_en / latin_name
    request: dict                    # preparation / cancer_type / treatment (None = "I don't know")
    sources: list[Source]


class AIProvider(Protocol):
    name: str
    model: str

    def generate(self, inp: DraftInput) -> Analysis: ...

    def identify_herb(self, image_data_url: str, herbs: list[dict]) -> HerbGuess: ...


class NullProvider:
    name, model = "none", ""

    def generate(self, inp: DraftInput) -> Analysis:
        raise ProviderNotConfigured()

    def identify_herb(self, image_data_url: str, herbs: list[dict]) -> HerbGuess:
        raise ProviderNotConfigured()


def get_provider(s: Settings, client: SafeClient) -> AIProvider:
    key = s.ai_api_key.get_secret_value() if s.ai_api_key else ""
    if s.ai_provider == "openai" and key and s.ai_model:
        from app.ai.openai import OpenAIProvider
        return OpenAIProvider(client, key, s.ai_model, s.ai_timeout_seconds)
    return NullProvider()
