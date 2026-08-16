"""Typed working scope for a bounded policy-coherence investigation."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkingScope(BaseModel):
    """The explicit, revisable applicability interpretation for one investigation."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    populations: list[str] = Field(min_length=1)
    access_types: list[str] = Field(min_length=1)
    geography: str = Field(min_length=1)
    as_of_date: date

    @field_validator("topic", "geography")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("populations", "access_types")
    @classmethod
    def normalize_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("scope values must be unique")
        if not normalized:
            raise ValueError("scope values must not be blank")
        return normalized

    @model_validator(mode="after")
    def topic_is_not_blank(self) -> WorkingScope:
        if not self.topic:
            raise ValueError("topic must not be blank")
        return self
