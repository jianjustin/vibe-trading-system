import json
from unittest.mock import MagicMock, patch

import pytest

from vts.loaders.sec_loader import SECDownloader


@pytest.fixture
def downloader():
    return SECDownloader(user_agent="test test@example.com")


def _mock_response(payload=None, status_code=200, content=b""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.content = content
    resp.raise_for_status.return_value = None
    return resp


CIK_PAYLOAD = {
    "0": {"ticker": "AAPL", "cik_str": 320193},
    "1": {"ticker": "TSLA", "cik_str": 1318605},
}

SUBMISSIONS_PAYLOAD = {
    "filings": {
        "recent": {
            "form": ["8-K", "10-Q", "8-K", "4"],
            "filingDate": ["2026-05-01", "2026-04-20", "2026-02-01", "2026-01-15"],
            "accessionNumber": ["0001-26-000001", "0001-26-000002", "0001-26-000003", "0001-26-000004"],
            "primaryDocument": ["a8k.htm", "a10q.htm", "b8k.htm", "form4.xml"],
        },
        "files": [],
    }
}


def test_get_cik_pads_to_ten_digits(downloader):
    with patch("vts.loaders.sec_loader.requests.get", return_value=_mock_response(CIK_PAYLOAD)):
        assert downloader.get_cik("aapl") == "0000320193"
        assert downloader.get_cik("TSLA") == "0001318605"


def test_get_cik_unknown_returns_none(downloader):
    with patch("vts.loaders.sec_loader.requests.get", return_value=_mock_response(CIK_PAYLOAD)):
        assert downloader.get_cik("NOPE") is None


def test_get_recent_filings_filters_form_and_limit(downloader):
    with patch("vts.loaders.sec_loader.requests.get", return_value=_mock_response(SUBMISSIONS_PAYLOAD)):
        filings = downloader.get_recent_filings("0000320193", form_type="8-K", limit=1)
        assert len(filings) == 1
        assert filings[0]["accession"] == "0001-26-000001"


def test_get_filings_since_filters_by_date_and_forms(downloader):
    with patch("vts.loaders.sec_loader.requests.get", return_value=_mock_response(SUBMISSIONS_PAYLOAD)):
        filings = downloader.get_filings_since("0000320193", ["8-K", "10-Q"], "2026-04-01")
        forms = {f["form"] for f in filings}
        assert forms == {"8-K", "10-Q"}
        assert all(f["date"] >= "2026-04-01" for f in filings)
        assert len(filings) == 2


def test_pick_best_document_prefers_exhibit_99_1(downloader):
    docs = [
        {"name": "main8k.htm", "type": "8-K", "description": "Form 8-K"},
        {"name": "ex99-1.htm", "type": "EX-99.1", "description": "Press Release"},
    ]
    assert downloader._pick_best_document(docs)["name"] == "ex99-1.htm"


def test_pick_best_document_falls_back_to_8k_then_html(downloader):
    docs = [{"name": "main8k.htm", "type": "8-K", "description": ""}]
    assert downloader._pick_best_document(docs)["name"] == "main8k.htm"
    docs = [{"name": "other.html", "type": "GRAPHIC", "description": ""}]
    assert downloader._pick_best_document(docs)["name"] == "other.html"
    assert downloader._pick_best_document([]) is None


def test_download_exhibit_writes_file(downloader, tmp_path):
    index_payload = {
        "documents": [{"name": "ex99-1.htm", "type": "EX-99.1", "description": "Press Release"}]
    }
    responses = [
        _mock_response(index_payload),  # filing index JSON
        _mock_response(content=b"<html>earnings</html>"),  # document download
    ]
    downloader.session.get = MagicMock(side_effect=responses)
    path = downloader.download_exhibit("0000320193", "0001-26-000001", tmp_path)
    assert path is not None
    assert path.read_bytes() == b"<html>earnings</html>"
    assert path.name == "0001-26-000001.htm"


def test_download_exhibit_uses_primary_document_fallback(downloader, tmp_path):
    responses = [
        _mock_response(status_code=404),  # index JSON miss
        _mock_response(status_code=404),  # index HTM miss
        _mock_response(content=b"<html>8k</html>"),  # primary document download
    ]
    downloader.session.get = MagicMock(side_effect=responses)
    path = downloader.download_exhibit(
        "0000320193", "0001-26-000001", tmp_path, primary_document="a8k.htm"
    )
    assert path is not None
    assert path.read_bytes() == b"<html>8k</html>"
