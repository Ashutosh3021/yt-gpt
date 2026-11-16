"""Request models and small shared constants for the HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Grounding = Literal["strict", "interpretive"]
PersonaId = Literal["default", "skeptic", "lecturer", "editor", "custom"]

PERSONAS: dict[str, str] = {
    "default": "Be clear and direct. Lead with the answer, then the evidence. No preamble.",
    "skeptic": "Question the claim first. Separate what the sources support from what they assume.",
    "lecturer": "Build from first principles, one idea at a time, using concrete examples.",
    "editor": "Use tight sentences and active verbs. Remove filler and hedging.",
}


class SignUpBody(BaseModel):
    name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=320)
    password: str = Field(default="", max_length=512)


class SignInBody(BaseModel):
    email: str = Field(default="", max_length=320)
    password: str = Field(default="", max_length=512)


class WorkspaceCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class WorkspacePatchBody(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class LinksBody(BaseModel):
    links: str = Field(default="")


class SessionCreateBody(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class SessionSettingsPatch(BaseModel):
    grounding: Grounding | None = None
    personaId: PersonaId | None = None
    personaPrompt: str | None = None
    modelOverride: str | None = None
    useVisuals: bool | None = None


class SessionPatchBody(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    settings: SessionSettingsPatch | None = None


class ChatBody(BaseModel):
    content: str = Field(min_length=1)


class SourceCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str | None = None


class SourceUpdateBody(BaseModel):
    content: str = Field(default="")
    note: str | None = Field(default=None, max_length=200)


class LlmPatchBody(BaseModel):
    provider: Literal["openai", "anthropic", "google", "openrouter", "ollama", "custom"] | None = None
    baseUrl: str | None = None
    model: str | None = None
    embeddingModel: str | None = None
    apiKey: str | None = None
