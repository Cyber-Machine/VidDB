import pytest

from apps.indexing.embeddings import FastEmbedProvider, cosine_similarity


class FakeFastEmbedModel:
    def embed(self, texts: list[str]) -> list[list[float]]:
        assert texts == ["a football player scores"]
        return [[0.1, 0.2, 0.3]]

    def query_embed(self, texts: list[str]) -> list[list[float]]:
        assert texts == ["goal"]
        return [[0.3, 0.2, 0.1]]


def test_fastembed_provider_uses_document_and_query_encoders() -> None:
    provider = FastEmbedProvider()
    provider.__dict__["_model"] = FakeFastEmbedModel()

    assert provider.embed_document("a football player scores") == [0.1, 0.2, 0.3]
    assert provider.embed_query("goal") == [0.3, 0.2, 0.1]


def test_cosine_similarity_validates_vector_dimensions() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="equal dimensions"):
        cosine_similarity([1.0], [1.0, 0.0])
