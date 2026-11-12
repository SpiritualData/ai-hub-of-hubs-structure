"""Base model for the public protocol models. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/app_server/_model.py); modified from upstream: only ProtocolModel kept; validate_wire and validate_backend_wire cut (the screen does no wire parsing)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ProtocolModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        defer_build=True,
    )

