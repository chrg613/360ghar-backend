"""
Abstract base classes for AI provider integration.

This module provides a unified interface for different AI providers (Gemini, GLM, OpenAI, etc.)
enabling easy switching between providers and reuse across different AI-powered features.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class AIRole(str, Enum):
    """Message roles for AI conversations."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class AIMessage(BaseModel):
    """A message in an AI conversation."""
    role: AIRole
    content: str


class VisionInput(BaseModel):
    """Input for vision-capable AI models."""
    image_base64: str = Field(..., description="Base64-encoded image data")
    mime_type: str = Field(..., description="Image MIME type (image/jpeg, image/png, image/webp)")


class AIProviderConfig(BaseModel):
    """Configuration for an AI provider."""
    api_key: str = Field(..., description="API key for the provider")
    model: str = Field(..., description="Model name/ID to use")
    max_tokens: int = Field(default=4000, description="Maximum tokens in response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    timeout: int = Field(default=120, description="Request timeout in seconds")


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI providers (Gemini, GLM, OpenAI, Anthropic, etc.) should implement this interface
    to ensure consistent behavior across the application.

    Example usage:
        provider = get_ai_provider(AIProviderType.GEMINI)
        response = await provider.complete(messages, vision_input)
    """

    def __init__(self, config: AIProviderConfig):
        self.config = config

    def _extract_balanced_json_object(self, text: str) -> Optional[str]:
        """Return the first balanced JSON object embedded in text."""
        start = text.find("{")
        while start != -1:
            depth = 0
            in_string = False
            escape = False

            for index in range(start, len(text)):
                char = text[index]

                if in_string:
                    if escape:
                        escape = False
                    elif char == "\\":
                        escape = True
                    elif char == '"':
                        in_string = False
                    continue

                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : index + 1]

            start = text.find("{", start + 1)

        return None

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response text.

        Tries, in order:
        1. Direct ``json.loads``
        2. Extraction from markdown code fences (```json ... ```)
        3. The first balanced JSON object embedded in the text
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Markdown code block
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # First balanced-brace JSON object
        json_object = self._extract_balanced_json_object(text)
        if json_object:
            try:
                return json.loads(json_object)
            except json.JSONDecodeError:
                pass

        raise AIProviderError(
            message="Failed to parse JSON from response",
            provider=self.name,
            response_body=text[:1000],
        )

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the provider."""
        pass

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this provider supports vision/image inputs."""
        pass

    @property
    @abstractmethod
    def supports_json_mode(self) -> bool:
        """Whether this provider supports structured JSON output mode."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[AIMessage],
        vision_input: Optional[VisionInput] = None,
    ) -> str:
        """
        Generate a text completion from the AI model.

        Args:
            messages: List of conversation messages
            vision_input: Optional image input for vision models

        Returns:
            Generated text response

        Raises:
            AIProviderError: If the API call fails
        """
        pass

    @abstractmethod
    async def complete_json(
        self,
        messages: List[AIMessage],
        vision_input: Optional[VisionInput] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON completion from the AI model.

        Args:
            messages: List of conversation messages
            vision_input: Optional image input for vision models
            json_schema: Optional JSON schema for structured output

        Returns:
            Parsed JSON response as a dictionary

        Raises:
            AIProviderError: If the API call fails or JSON parsing fails
        """
        pass


class AIProviderError(Exception):
    """Base exception for AI provider errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        base = f"[{self.provider}] {super().__str__()}"
        if self.status_code:
            base += f" (status: {self.status_code})"
        return base
