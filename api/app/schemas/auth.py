from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthSessionResponse(BaseModel):
    subject: str = ""
    scope: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    claims: dict[str, Any] = Field(default_factory=dict)
