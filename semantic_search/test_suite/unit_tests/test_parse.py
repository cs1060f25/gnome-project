# --------------------------------------------------------------
# Unit tests for parsing_engine.parse_pdf module
# --------------------------------------------------------------
# We stub fitz & Pillow so no native libs are required, and stub urlopen
# to avoid network traffic. All three public helpers are covered for
# happy‑path and key failure flows.
# --------------------------------------------------------------

import io
import types
import sys
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------
# Inject lightweight stubs for fitz and PIL.Image BEFORE importing module
# ---------------------------------------------------------------------

# --- fitz stub --------------------------------------------------------
fitz_stub = types.ModuleType("fitz")

class _DummyMatrix:  # used but irrelevant
    def __init__(self, *a, **kw):
        pass

class _DummyPixmap:
    width = 100
    height = 200
    samples = b"PIXELDATA"

    def __init__(self, page_no):
        self.page_no = page_no

class _DummyPage:
    def __init__(self, idx):
        self.idx = idx
    def get_pixmap(self, matrix=None):
        return _DummyPixmap(self.idx)

class _DummyDoc:
    def __init__(self, pages):
        self.page_count = pages
    def __getitem__(self, idx):
        return _DummyPage(idx)
    def close(self):
        pass

# open(path) or open(stream=..., filetype="pdf") -> _DummyDoc
open_calls = {}

def fake_open(*a, **kw):
    # allow tests to inject desired page counts via open_calls marker
    pages = open_calls.get("pages", 1)
    return _DummyDoc(pages)

fitz_stub.open = fake_open
fitz_stub.Matrix = _DummyMatrix
sys.modules["fitz"] = fitz_stub

# --- PIL.Image stub ---------------------------------------------------
image_mod = types.ModuleType("PIL.Image")

def fake_frombytes(mode, size, samples):
    # Return a predictable tuple so tests can assert equality
    return (mode, size, samples)

image_mod.frombytes = fake_frombytes
pil_mod = types.ModuleType("PIL")
pil_mod.Image = image_mod
sys.modules["PIL"] = pil_mod
sys.modules["PIL.Image"] = image_mod

# ---------------------------------------------------------------------
# Now import the module under test
# ---------------------------------------------------------------------
from backend_api.parsing_engine import parse_pdf

# Helpers --------------------------------------------------------------

def _set_page_count(n):
    """Configure the next fitz.open call to return a doc with *n* pages."""
    open_calls["pages"] = n

# ---------------------------------------------------------------------
# pdf_url_to_screenshots ------------------------------------------------
# ---------------------------------------------------------------------

@patch("backend_api.parsing_engine.parse_pdf.urlopen")
def test_url_invalid(mock_urlopen):
    with pytest.raises(ValueError):
        parse_pdf.pdf_url_to_screenshots("file:///bad.pdf")
    mock_urlopen.assert_not_called()

@patch("backend_api.parsing_engine.parse_pdf.urlopen")
def test_url_happy_path(mock_urlopen):
    # Stub urlopen to return BytesIO for any URL
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = b"%PDF-1.4 DUMMY"  # minimal bytes
    mock_urlopen.return_value = mock_resp

    _set_page_count(2)
    imgs = parse_pdf.pdf_url_to_screenshots("http://example.com/file.pdf", zoom=1.0)

    assert len(imgs) == 2
    # Validate one of the returned tuples comes from our fake_frombytes
    assert imgs[0][0] == "RGB" and imgs[0][1] == [100, 200]

# ---------------------------------------------------------------------
# pdf_path_to_screenshots ----------------------------------------------
# ---------------------------------------------------------------------

def test_path_invalid():
    with pytest.raises(ValueError):
        parse_pdf.pdf_path_to_screenshots("/tmp/not_pdf.txt")

@patch("backend_api.parsing_engine.parse_pdf.open", side_effect=fake_open)
def test_path_happy(_, tmp_path):
    dummy_path = tmp_path / "doc.pdf"
    dummy_path.write_bytes(b"%PDF-1.4")

    _set_page_count(3)
    imgs = parse_pdf.pdf_path_to_screenshots(str(dummy_path), zoom=1.5)
    assert len(imgs) == 3

# ---------------------------------------------------------------------
# bytesio_to_screenshots ------------------------------------------------
# ---------------------------------------------------------------------

@patch("backend_api.parsing_engine.parse_pdf.open", side_effect=fake_open)
def test_bytesio_zero_pages(_):
    _set_page_count(0)
    imgs = parse_pdf.bytesio_to_screenshots(io.BytesIO(b"%PDF-1.4"))
    assert imgs == []

@patch("backend_api.parsing_engine.parse_pdf.open", side_effect=fake_open)
def test_bytesio_happy(_):
    _set_page_count(1)
    imgs = parse_pdf.bytesio_to_screenshots(io.BytesIO(b"%PDF-1.4"))
    assert len(imgs) == 1
    assert imgs[0][2] == b"PIXELDATA"
