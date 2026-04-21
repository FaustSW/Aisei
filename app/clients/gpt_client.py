"""
GPT Client

Thin wrapper around the LLM API.

Responsibilities:
- Send prompts to the configured model.
- Return the raw model response (text or structured JSON).

It is a transport layer only.
"""

from __future__ import annotations

import keyring
from openai import OpenAI

APP_ID = "SeniorCapstone_Anki"


class GPTClient:
    """Thin transport wrapper for OpenAI text generation."""

    DEFAULT_MODEL = "gpt-5.4-nano"
    DEFAULT_TEMPERATURE = 0

    def __init__(self, username: str) -> None:
        self.username = username

        api_key = keyring.get_password(APP_ID, f"{username}_openai")
        if not api_key:
            raise ValueError(f"No OpenAI key found for {username}")

        self.client = OpenAI(api_key=api_key)

    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        text_format: dict | None = None,
        temperature: float | None = DEFAULT_TEMPERATURE,
        max_output_tokens: int | None = None,
    ) -> str:
        """
        Send a prompt to the configured model and return the text output.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        input_parts = []

        if system_prompt and system_prompt.strip():
            input_parts.append({
                "role": "system",
                "content": system_prompt.strip(),
            })

        input_parts.append({
            "role": "user",
            "content": prompt.strip(),
        })

        try:
            request_args = {
                "model": model or self.DEFAULT_MODEL,
                "input": input_parts,
            }

            if text_format is not None:
                request_args["text"] = {"format": text_format}
            if temperature is not None:
                request_args["temperature"] = temperature
            if max_output_tokens is not None:
                request_args["max_output_tokens"] = max_output_tokens

            response = self.client.responses.create(**request_args)
            return response.output_text
        except Exception as e:
            raise RuntimeError(f"OpenAI text generation failed: {e}") from e
