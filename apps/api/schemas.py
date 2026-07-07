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

