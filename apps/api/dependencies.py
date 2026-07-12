import os
from collections.abc import Iterator

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from apps.persistence.database import create_database_engine, create_session_factory

engine = create_database_engine()
SessionFactory = create_session_factory(engine)


def get_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session


def authenticate_request(
    api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    expected_api_key = os.environ.get("VIDEODB_API_KEY")
    if expected_api_key is not None and api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="invalid api key")
