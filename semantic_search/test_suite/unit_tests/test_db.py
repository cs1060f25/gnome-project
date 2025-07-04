# --------------------------------------------------------------
# Unit tests for Pinecone helper modules
# --------------------------------------------------------------
# Covers:
#   • pinecone_client.init_pinecone_idx
#   • semantic_search.semantic_search
#   • store_vectors.store_embeddings
# All external services are mocked so tests run offline.
# --------------------------------------------------------------

import os
import types
import sys
from unittest.mock import patch, MagicMock
import pytest

# -----------------------------------------------------------------
# pinecone_client tests -------------------------------------------
# -----------------------------------------------------------------
from backend_api.vector_database import pinecone_client

@patch.dict(os.environ, {"PINECONE_API_KEY": "k", "PINECONE_HOST": "h"})
@patch("backend_api.vector_database.pinecone_client.Pinecone")
def test_init_pinecone_success(mock_pc):
    mock_idx = MagicMock(name="idx")
    mock_pc.return_value.Index.return_value = mock_idx
    idx = pinecone_client.init_pinecone_idx()
    assert idx is mock_idx
    mock_pc.assert_called_once_with(api_key="k")
    mock_pc.return_value.Index.assert_called_once_with(host="h")

@patch.dict(os.environ, {}, clear=True)
def test_init_pinecone_missing_env():
    with pytest.raises(Exception):
        pinecone_client.init_pinecone_idx()

@patch.dict(os.environ, {"PINECONE_API_KEY": "k", "PINECONE_HOST": "h"})
@patch("backend_api.vector_database.pinecone_client.Pinecone", side_effect=RuntimeError("down"))
def test_init_pinecone_failure(_):
    with pytest.raises(Exception):
        pinecone_client.init_pinecone_idx()

# -----------------------------------------------------------------
# semantic_search tests -------------------------------------------
# -----------------------------------------------------------------
from backend_api.vector_database import semantic_search as sem_mod

# stub embed_query to return deterministic vector
@patch("backend_api.vector_database.semantic_search.embed_query", return_value=[0.1] * 1024)
def test_semantic_search_success(mock_embed):
    # build a fake match object similar to pinecone
    def _match(id_, score, filename):
        m = types.SimpleNamespace()
        m.id = id_
        m.score = score
        m.metadata = {"filename": filename}
        return m

    matches = [_match("a", 0.9, "file1"), _match("b", 0.8, "file1"), _match("c", 0.7, "file2")]
    query_resp = types.SimpleNamespace(matches=matches)

    idx = MagicMock(name="idx")
    idx.query.return_value = query_resp
    voyage = MagicMock(name="voyage")

    out = sem_mod.semantic_search("hello", idx, voyage, top_k=2, namespace="ns")
    # should keep highest per file: so 2 results (file1 highest + file2)
    assert len(out) == 2
    assert {m["id"] for m in out} == {"a", "c"}
    idx.query.assert_called_once()

@patch("backend_api.vector_database.semantic_search.embed_query", return_value=None)
def test_semantic_search_embed_fail(_):
    with pytest.raises(Exception):
        sem_mod.semantic_search("q", MagicMock(), MagicMock(), 3, "ns")

# -----------------------------------------------------------------
# store_vectors tests ---------------------------------------------
# -----------------------------------------------------------------
from backend_api.vector_database import store_vectors as store_mod

@patch("backend_api.vector_database.store_vectors.Pinecone")  # not actually used but ensures import
def test_store_embeddings_success(_dummy):
    idx = MagicMock(name="idx")
    embeddings = [[0.0] * 1024, [0.1] * 1024]
    count = store_mod.store_embeddings("fid", "name.pdf", idx, embeddings, "ns")
    assert count == 2
    idx.upsert.assert_called_once()
    upsert_args = idx.upsert.call_args.kwargs["vectors"]
    assert len(upsert_args) == 2
    assert upsert_args[0]["id"] == "page_0:fid"

@patch("backend_api.vector_database.store_vectors.Pinecone")
def test_store_embeddings_edge_cases(_dummy):
    idx = MagicMock()
    bad_dim = [[0.0] * 100]
    assert store_mod.store_embeddings("", "name", idx, bad_dim, "ns") == 0  # no id
    assert store_mod.store_embeddings("id", "", idx, bad_dim, "ns") == 0    # no filename
    assert store_mod.store_embeddings("id", "name", None, bad_dim, "ns") == 0  # no idx
    # wrong dim skipped -> returns 0 stored
    cnt = store_mod.store_embeddings("id", "name", idx, bad_dim, "ns")
    assert cnt == 0
    # upsert should be invoked but with an empty list of vectors
    idx.upsert.assert_called_once_with(vectors=[], namespace="ns")
