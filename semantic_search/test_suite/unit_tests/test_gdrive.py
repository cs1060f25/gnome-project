# --------------------------------------------------------------
# Unit tests for backend.google_drive_helpers modules
# --------------------------------------------------------------
# Covers:
#   • download_file.py (Drive file download helper)
#   • quickstart.py    (OAuth / Drive bootstrap)
# All external Google libs are stubbed so tests run offline.
# --------------------------------------------------------------

import io
import pytest
from unittest.mock import MagicMock, patch

# --------------------------------------------------
# download_file tests --------------------------------------------------------
# --------------------------------------------------
from backend.google_drive_helpers.download_file import download_file

_FAKE_BYTES = b"%PDF-1.4 FAKE PDF BYTES%"


def _build_service_mock(fake_bytes: bytes, name: str):
    """Return (service_mock, downloader_factory).

    downloader_factory receives the BytesIO handle that download_file
    passes into MediaIoBaseDownload. It writes *fake_bytes* into that handle
    on the first call to next_chunk() and then signals done=True.
    """

    service_mock = MagicMock(name="service")
    files = service_mock.files.return_value

    # metadata query → filename
    files.get.return_value.execute.return_value = {"name": name}

    # media download request placeholder
    files.get_media.return_value = MagicMock(name="request")

    class _Status:
        def __init__(self, done):
            self.done = done

    def downloader_factory(file_handle, _request):
        def _next_chunk():
            file_handle.write(fake_bytes)
            return None, _Status(done=True)

        d = MagicMock(name="downloader")
        d.next_chunk.side_effect = _next_chunk
        return d

    return service_mock, downloader_factory


@patch("backend.google_drive_helpers.download_file.MediaIoBaseDownload")
@patch("backend.google_drive_helpers.download_file.build")
@patch("backend.google_drive_helpers.download_file.Credentials")
def test_download_success(mock_creds_cls, mock_build, mock_downloader_cls):
    """Happy path: bytes and filename returned."""
    mock_creds_cls.from_authorized_user_info.return_value = MagicMock(name="creds")

    service, factory = _build_service_mock(_FAKE_BYTES, "doc.pdf")
    mock_build.return_value = service
    mock_downloader_cls.side_effect = factory

    content, fname = download_file("file123", {"access_token": "a"})

    assert content == _FAKE_BYTES
    assert fname == "doc.pdf"


@patch("backend.google_drive_helpers.download_file.Credentials")
def test_download_creds_error(mock_creds_cls):
    mock_creds_cls.from_authorized_user_info.side_effect = ValueError("bad creds")
    with pytest.raises(ValueError):
        download_file("id", {})


@patch("backend.google_drive_helpers.download_file.MediaIoBaseDownload")
@patch("backend.google_drive_helpers.download_file.build")
@patch("backend.google_drive_helpers.download_file.Credentials")
def test_download_failure(mock_creds_cls, mock_build, mock_downloader_cls):
    mock_creds_cls.from_authorized_user_info.return_value = MagicMock()

    service, _ = _build_service_mock(_FAKE_BYTES, "x.pdf")
    mock_build.return_value = service

    def err_factory(_fh, _req):
        d = MagicMock()
        d.next_chunk.side_effect = RuntimeError("network")
        return d

    mock_downloader_cls.side_effect = err_factory

    with pytest.raises(RuntimeError):
        download_file("id", {"t": "x"})


# --------------------------------------------------
# quickstart tests -----------------------------------------------------------
# --------------------------------------------------
from backend.google_drive_helpers import quickstart

# -------- valid existing token ---------------------------------------------

@patch("backend.google_drive_helpers.quickstart.os.path.exists", return_value=True)
@patch("backend.google_drive_helpers.quickstart.Credentials")
@patch("backend.google_drive_helpers.quickstart.build")
@patch("backend.google_drive_helpers.quickstart.jwt.decode")
@patch("backend.google_drive_helpers.quickstart.InstalledAppFlow")
def test_quickstart_token_present(mock_flow_cls, mock_jwt, mock_build, mock_creds_cls, _exists):
    """Token file exists and creds valid → skip OAuth flow."""
    creds = MagicMock(valid=True, id_token=None)
    mock_creds_cls.from_authorized_user_file.return_value = creds

    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    mock_build.return_value = service

    quickstart.main()

    mock_creds_cls.from_authorized_user_file.assert_called_once()
    mock_build.assert_called_once()
    mock_flow_cls.from_client_secrets_file.assert_not_called()


# -------- no token → run OAuth flow ---------------------------------------- → run OAuth flow ----------------------------------------

@patch("backend.google_drive_helpers.quickstart.os.path.exists", return_value=False)
@patch("backend.google_drive_helpers.quickstart.open", create=True)
@patch("backend.google_drive_helpers.quickstart.jwt.decode", return_value={"sub": "user123"})
@patch("backend.google_drive_helpers.quickstart.build")
@patch("backend.google_drive_helpers.quickstart.InstalledAppFlow")
def test_quickstart_flow(mock_flow_cls, mock_build, _decode, _open, _exists, monkeypatch):
    """No token file → quickstart should perform OAuth and save creds."""
    creds = MagicMock(valid=True, id_token="TOK")
    flow = MagicMock()
    flow.run_local_server.return_value = creds
    mock_flow_cls.from_client_secrets_file.return_value = flow

    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = {"files": []}
    mock_build.return_value = service

    # Ensure Credentials class is not used in this branch
    monkeypatch.setattr(quickstart, "Credentials", MagicMock())

    quickstart.main()

    mock_flow_cls.from_client_secrets_file.assert_called_once()
    flow.run_local_server.assert_called_once()
    mock_build.assert_called_once()
