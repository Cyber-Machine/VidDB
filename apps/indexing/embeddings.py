import os
from functools import cached_property, lru_cache
from math import sqrt
from typing import Any, Protocol

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str:
        ...

    def embed_document(self, text: str) -> list[float]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class FastEmbedProvider:
    """Generate semantic text embeddings locally with an ONNX model."""

    def __init__(
        self,
        model_id: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.cache_dir = cache_dir

    @cached_property
    def _model(self) -> Any:
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=self.model_id, cache_dir=self.cache_dir)

    def embed_document(self, text: str) -> list[float]:
        return _first_vector(self._model.embed([_validated_text(text)]))

    def embed_query(self, text: str) -> list[float]:
        query_embed = getattr(self._model, "query_embed", None)
        if callable(query_embed):
            return _first_vector(query_embed([_validated_text(text)]))
        return self.embed_document(text)


@lru_cache(maxsize=1)
def default_embedding_provider() -> FastEmbedProvider:
    return FastEmbedProvider(
        model_id=os.environ.get(
            "VIDEODB_EMBEDDING_MODEL",
            DEFAULT_EMBEDDING_MODEL,
        ),
        cache_dir=os.environ.get("VIDEODB_EMBEDDING_CACHE_DIR"),
    )


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError(
            "embedding vectors must be non-empty and have equal dimensions"
        )
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _validated_text(text: str) -> str:
    value = text.strip()
    if not value:
        raise ValueError("cannot embed empty text")
    return value


def _first_vector(vectors: Any) -> list[float]:
    try:
        vector = next(iter(vectors))
    except StopIteration as error:
        raise RuntimeError("embedding model returned no vector") from error
    values = [float(value) for value in vector]
    if not values:
        raise RuntimeError("embedding model returned an empty vector")
    return values
