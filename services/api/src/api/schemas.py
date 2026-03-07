"""Pydantic models for FastAPI request/response serialization.

These are API infrastructure types — they mirror the proto-defined shapes from
packages/schema/proto/api/v1/portfolio.proto for FastAPI validation and serialization.
Field names and types are derived directly from the proto definitions.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PresignRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1)


class PresignResponse(BaseModel):
    upload_url: str
    key: str


class CreatePortfolioItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    file_keys: list[str] = Field(default_factory=list)
    external_url: str = ""
    tags: list[str] = Field(default_factory=list)
    verified_gig_id: str | None = None


class UpdatePortfolioItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    file_keys: list[str] = Field(default_factory=list)
    external_url: str = ""
    tags: list[str] = Field(default_factory=list)


class PortfolioItemResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    file_keys: list[str]
    external_url: str
    tags: list[str]
    verified_gig_id: str | None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioItemsResponse(BaseModel):
    items: list[PortfolioItemResponse]
