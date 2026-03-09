from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class LinkCreateRequest(BaseModel):
    original_url: HttpUrl
    custom_alias: str | None = None
    expires_at: datetime | None = None


class LinkCreateResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: HttpUrl
    expires_at: datetime | None


class LinkUpdateRequest(BaseModel):
    original_url: HttpUrl


class LinkInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_code: str
    original_url: HttpUrl
    created_at: datetime
    expires_at: datetime | None


class LinkStatsResponse(BaseModel):
    short_code: str
    original_url: HttpUrl
    created_at: datetime
    click_count: int
    last_accessed_at: datetime | None
    expires_at: datetime | None


class LinkSearchResponse(BaseModel):
    short_code: str
    original_url: HttpUrl
    created_at: datetime
    expires_at: datetime | None


class PublicShortenRequest(BaseModel):
    original_url: HttpUrl


class PublicShortenResponse(BaseModel):
    original_url: HttpUrl
    short_url: str
    short_code: str
