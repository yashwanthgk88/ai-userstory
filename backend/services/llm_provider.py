"""LLM Provider abstraction layer. Supports Anthropic, OpenAI, Azure OpenAI, Gemini, and any OpenAI-compatible endpoint."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PROVIDER_MODELS = {
    "anthropic": ["claude-sonnet-4-20250514", "claude-haiku-4-20250414", "claude-opus-4-20250514"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"],
    "azure_openai": [],  # user-configured deployment names
    "gemini": ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-1.5-pro"],
    "openai_compatible": [],  # user-entered model names
}

PROVIDER_DEFAULTS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "azure_openai": "",
    "gemini": "gemini-2.0-flash",
    "openai_compatible": "",
}


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class BaseLLMProvider:
    async def chat(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> LLMResponse:
        raise NotImplementedError


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> LLMResponse:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return LLMResponse(
            text=message.content[0].text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=model,
        )


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    async def chat(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> LLMResponse:
        from openai import AsyncOpenAI
        kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = AsyncOpenAI(**kwargs)
        resp = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=model,
        )


class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint: str, deployment: str, api_version: str = "2024-06-01"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment = deployment
        self.api_version = api_version

    async def chat(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> LLMResponse:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )
        resp = await client.chat.completions.create(
            model=self.deployment,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=self.deployment,
        )


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> LLMResponse:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        gen_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
        )
        response = gen_model.generate_content(user_prompt)
        return LLMResponse(
            text=response.text,
            input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") else 0,
            output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, "usage_metadata") else 0,
            model=model,
        )


def get_provider(
    provider_name: str,
    api_key: str = "",
    base_url: str = "",
    azure_endpoint: str = "",
    azure_deployment: str = "",
) -> BaseLLMProvider:
    """Factory: create an LLM provider instance."""
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    elif provider_name == "openai_compatible":
        return OpenAIProvider(api_key=api_key, base_url=base_url)
    elif provider_name == "azure_openai":
        return AzureOpenAIProvider(api_key=api_key, endpoint=azure_endpoint, deployment=azure_deployment)
    elif provider_name == "gemini":
        return GeminiProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def get_default_provider():
    """Create provider from application settings."""
    from config import settings
    provider = settings.llm_provider

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return get_provider("anthropic", api_key=settings.anthropic_api_key)
    elif provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        return get_provider("openai", api_key=settings.openai_api_key)
    elif provider == "openai_compatible":
        return get_provider("openai_compatible", api_key=settings.openai_compatible_api_key, base_url=settings.openai_compatible_url)
    elif provider == "azure_openai":
        return get_provider("azure_openai", api_key=settings.azure_openai_api_key, azure_endpoint=settings.azure_openai_endpoint, azure_deployment=settings.azure_openai_deployment)
    elif provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        return get_provider("gemini", api_key=settings.gemini_api_key)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
