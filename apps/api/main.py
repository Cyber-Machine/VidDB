from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.dependencies import get_session
from apps.api.schemas import (
    AssetCreateRequest,
    AssetResponse,
    CollectionCreateRequest,
    CollectionResponse,
    MultipartUploadRequest,
    MultipartUploadResponse,
    UploadCompletionRequest,
)
from apps.ingestion import (
    create_asset,
    create_collection,
    create_multipart_upload,
    get_asset,
    list_collections,
)
from apps.persistence.models import MediaAsset


class HealthResponse(BaseModel):
    status: Literal["ok"]


class AssetStatusResponse(BaseModel):
    status: str


app = FastAPI(title="VideoDB")


@app.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection_endpoint(
    request: CollectionCreateRequest,
    session: Session = Depends(get_session),
    tenant_id: str = Header(alias="X-Tenant-ID"),
) -> CollectionResponse:
    collection = create_collection(session, tenant_id, request.name)
    return CollectionResponse(id=collection.id, name=collection.name)


@app.get("/collections", response_model=list[CollectionResponse])
async def list_collections_endpoint(
    session: Session = Depends(get_session),
    tenant_id: str = Header(alias="X-Tenant-ID"),
) -> list[CollectionResponse]:
    return [
        CollectionResponse(id=collection.id, name=collection.name)
        for collection in list_collections(session, tenant_id)
    ]


@app.post("/assets", response_model=AssetResponse, status_code=201)
async def create_asset_endpoint(
    request: AssetCreateRequest,
    session: Session = Depends(get_session),
    tenant_id: str = Header(alias="X-Tenant-ID"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AssetResponse:
    try:
        asset = create_asset(
            session,
            tenant_id,
            request.collection_id,
            request.source_uri,
            request.source_type,
            idempotency_key,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _asset_response(asset)


@app.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset_endpoint(
    asset_id: str,
    session: Session = Depends(get_session),
    tenant_id: str = Header(alias="X-Tenant-ID"),
) -> AssetResponse:
    asset = get_asset(session, tenant_id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return _asset_response(asset)


@app.get("/assets/{asset_id}/status", response_model=AssetStatusResponse)
async def asset_status_endpoint(
    asset_id: str,
    session: Session = Depends(get_session),
    tenant_id: str = Header(alias="X-Tenant-ID"),
) -> AssetStatusResponse:
    asset = get_asset(session, tenant_id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return AssetStatusResponse(status=asset.processing_state.value)


@app.post("/uploads/multipart", response_model=MultipartUploadResponse, status_code=201)
async def create_multipart_upload_endpoint(
    request: MultipartUploadRequest,
    tenant_id: str = Header(alias="X-Tenant-ID"),
) -> MultipartUploadResponse:
    upload = create_multipart_upload(
        tenant_id,
        request.collection_id,
        request.filename,
        request.part_count,
    )
    return MultipartUploadResponse.model_validate(upload)


@app.post("/uploads/complete", response_model=AssetResponse, status_code=201)
async def complete_upload_endpoint(
    request: UploadCompletionRequest,
    session: Session = Depends(get_session),
    tenant_id: str = Header(alias="X-Tenant-ID"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AssetResponse:
    asset = create_asset(
        session,
        tenant_id,
        request.collection_id,
        request.object_uri,
        "object",
        idempotency_key,
    )
    return _asset_response(asset)


def _asset_response(asset: MediaAsset) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        collection_id=asset.collection_id,
        source_uri=asset.source_uri,
        source_type=asset.source_type,
        processing_state=asset.processing_state.value,
        metadata=asset.metadata_,
    )
