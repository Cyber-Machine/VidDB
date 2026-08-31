from typing import Literal

from pydantic import BaseModel, Field


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


class EpisodeIndexRequest(BaseModel):
    source_index_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    max_gap_ms: int = Field(default=5_000, ge=0, le=3_600_000)
    min_similarity: float = Field(default=0.65, ge=-1.0, le=1.0)


class EpisodeIndexResponse(BaseModel):
    id: str
    version: str
    source_index_id: str
    episode_count: int


class SearchRequest(BaseModel):
    query: str
    collection_ids: list[str] | None = None
    asset_ids: list[str] | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    modalities: list[Literal["transcript", "visual", "episode"]] | None = None
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


class CustomIndexRequest(BaseModel):
    name: str
    prompt: str
    model: str
    sampling: dict[str, object] = {}


class CustomIndexResponse(BaseModel):
    id: str
    name: str
    version: str
    prompt_hash: str
    alias: str | None
