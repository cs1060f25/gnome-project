# --------------------------------------------------------------
# Test suite for backend_api.embedding_engine
# --------------------------------------------------------------
# We stub heavy / native deps so these unit tests run without the real
# libraries or network access.
# --------------------------------------------------------------
import sys, types, builtins

# --- stub voyageai ---------------------------------------------------------
_fake_voyage = types.ModuleType("voyageai")
class _DummyResponse:
    def __init__(self, embeddings):
        self.embeddings = embeddings
class _DummyClient:
    def __init__(self, api_key="fake"):  # signature similar to real one
        self._key = api_key
    def multimodal_embed(self, *, inputs, model, input_type):  # very loose match
        # Return predictable vectors: len(inputs) * [index+0.1, 0.2, ...] ×1024
        outs = []
        for i, _ in enumerate(inputs):
            outs.append([float(i)] * 1024)
        return _DummyResponse(outs)
_fake_voyage.Client = _DummyClient
sys.modules["voyageai"] = _fake_voyage

# --- stub PIL.Image --------------------------------------------------------
# Real code does: `from PIL import Image` then uses `Image.Image` in type hints.
_pil_mod = types.ModuleType("PIL")
_image_sub = types.ModuleType("PIL.Image")
class _StubImage:  # minimal stand‑in
    pass
_image_sub.Image = _StubImage
_pil_mod.Image = _image_sub  # so `from PIL import Image` gets sub‑module
sys.modules["PIL"] = _pil_mod = _pil_mod
sys.modules["PIL.Image"] = _image_sub

# --------------------------------------------------------------
# Import the modules under test *after* stubbing
# --------------------------------------------------------------
from backend_api.embedding_engine.embed_pdf import embed_pdf_by_page
from backend_api.embedding_engine.embed_query import embed_query
from backend_api.embedding_engine.voyage_client import init_voyage

import os
import pytest
from unittest.mock import patch, MagicMock

# --------------------------------------------------
# Fixtures
# --------------------------------------------------
@pytest.fixture
def voyage_client():
    # our stubbed voyageai.Client
    from voyageai import Client  # picks up stub
    return Client(api_key="test")

# Helper: produce fake PIL images (just sentinel objects)
def _fake_image(n=1):
    from PIL import Image as PILImage
    return [PILImage.Image() for _ in range(n)]

# --------------------------------------------------
# embed_pdf_by_page ----------------------------------------------------------
# --------------------------------------------------

def test_embed_pdf_by_page_success(voyage_client):
    imgs = _fake_image(3)
    result = embed_pdf_by_page(imgs, voyage_client)
    # Should get one embedding per page
    assert len(result) == 3
    # Each embedding should be 1024‑d vectors of floats
    assert all(len(vec) == 1024 for vec in result)


def test_embed_pdf_by_page_client_error(monkeypatch, voyage_client):
    def boom(*a, **kw):
        raise RuntimeError("API failure")
    monkeypatch.setattr(voyage_client, "multimodal_embed", boom)
    with pytest.raises(RuntimeError):
        embed_pdf_by_page(_fake_image(1), voyage_client)

# --------------------------------------------------
# embed_query ----------------------------------------------------------------
# --------------------------------------------------

def test_embed_query_success(voyage_client):
    vec = embed_query("hello world", voyage_client)
    assert len(vec) == 1024
    assert all(isinstance(v, float) for v in vec)


def test_embed_query_error(monkeypatch, voyage_client):
    def boom(*a, **kw):
        raise ValueError("bad")
    # Replace voyage_client.multimodal_embed with a stub that errors
    monkeypatch.setattr(voyage_client, "multimodal_embed", boom)
    with pytest.raises(ValueError):
        embed_query("oops", voyage_client)

# --------------------------------------------------
# init_voyage ----------------------------------------------------------------
# --------------------------------------------------

def test_init_voyage_success(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "xyz")
    client = init_voyage()
    from voyageai import Client
    assert isinstance(client, Client)


def test_init_voyage_missing_key(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(Exception):
        init_voyage()
