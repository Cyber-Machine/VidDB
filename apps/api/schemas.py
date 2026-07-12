from typing import Literal

from pydantic import BaseModel


class CollectionCreateRequest(BaseModel):
    name: str


class CollectionResponse(BaseModel):
    id: str
    name: str


class AssetCreateRequest(BaseModel):
    collection_id: str
    source_uri: str
    source_type: Literal["object", "url"] = "object"


class AssetResponse(BaseModel):
    id: str
    collection_id: str
    source_uri: str
    source_type: str
    processing_state: str
    metadata: dict[str, object]


class MultipartUploadRequest(BaseModel):
    collection_id: str
    filename: str
    part_count: int


class MultipartUploadResponse(BaseModel):
    upload_id: str
    object_uri: str
    part_urls: list[str]


class UploadCompletionRequest(BaseModel):
    collection_id: str
    object_uri: str


class SearchRequest(BaseModel):
    query: str
    collection_ids: list[str] | None = None
    asset_ids: list[str] | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    modalities: list[Literal["transcript", "visual"]] | None = None
    index_versions: list[str] | None = None
    vector_weight: float = 0.7
    full_text_weight: float = 0.3
    pre_roll_ms: int = 0
    post_roll_ms: int = 0
    cursor: str | None = None
    limit: int = 10


class SearchResultResponse(BaseModel):
    asset_id: str
    start_ms: int
    end_ms: int
    score: float
    evidence: list[str]
    modalities: list[str]
    source_frame_uris: list[str]


class SearchResponse(BaseModel):
    results: list[SearchResultResponse]
    next_cursor: str | None


class ClipSegmentRequest(BaseModel):
    asset_id: str
    start_ms: int
    end_ms: int


class ClipCreateRequest(BaseModel):
    name: str
    segments: list[ClipSegmentRequest]


class ClipResponse(BaseModel):
    id: str
    name: str
    manifest: dict[str, object]


class ClipManifestResponse(BaseModel):
    clip_id: str
    manifest: str
    playback_url: str


class DeletionStatusResponse(BaseModel):
    asset_id: str
    status: str
    deleted_objects: list[str]


class MetricsResponse(BaseModel):
    counters: dict[str, int]
