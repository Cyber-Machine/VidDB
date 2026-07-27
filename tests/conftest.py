from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.persistence.migrations import run_migrations


class TestSemanticEmbeddingProvider:
    model_id = "test-semantic-embedding-v1"

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        lowered = text.lower()
        return [
            float(any(word in lowered for word in ("goal", "scored", "net"))),
            float(any(word in lowered for word in ("crowd", "celebration", "replay"))),
            float(
                any(word in lowered for word in ("frame", "visual", "representative"))
            ),
            1.0,
        ]


@pytest.fixture(autouse=True)
def use_test_embedding_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = TestSemanticEmbeddingProvider()
    monkeypatch.setattr(
        "apps.indexing.transcript.default_embedding_provider",
        lambda: provider,
    )
    monkeypatch.setattr(
        "apps.indexing.visual.default_embedding_provider",
        lambda: provider,
    )
    monkeypatch.setattr(
        "apps.search.default_embedding_provider",
        lambda: provider,
    )


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: Any,
        connection_record: object,
    ) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    run_migrations(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
