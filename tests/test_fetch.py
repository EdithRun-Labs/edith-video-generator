import io

import pytest

from edith import fetch
from edith.deps import Manifest


def _manifest(tmp_path, size=8, url="https://example.invalid/weights.bin"):
    return Manifest.model_validate(
        {
            "schema": 1,
            "dependencies": [
                {
                    "id": "weights",
                    "why": "test",
                    "version": "1",
                    "home": "https://example.invalid",
                    "files": [{"path": "models/weights.bin", "url": url, "size": size}],
                }
            ],
        }
    )


class FakeResponse:
    def __init__(self, chunks, length=None):
        self.chunks = list(chunks)
        self.headers = {"Content-Length": str(sum(len(c) for c in chunks) if length is None else length)}

    def read(self, size):
        return self.chunks.pop(0) if self.chunks else b""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_human_sizes():
    assert fetch.human(28_214_398) == "28 MB"
    assert fetch.human(325_532_387) == "326 MB"
    assert fetch.human(1_500_000_000) == "1.5 GB"
    assert fetch.human(900) == "1 KB"


def test_planned_lists_only_missing_files(tmp_path):
    manifest = _manifest(tmp_path)
    assert [item.path for item in fetch.planned(manifest, tmp_path)] == ["models/weights.bin"]
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "weights.bin").write_bytes(b"x" * 8)
    assert fetch.planned(manifest, tmp_path) == []


def test_download_writes_and_verifies(monkeypatch, tmp_path):
    monkeypatch.setattr(
        fetch.urllib.request, "urlopen", lambda url, timeout: FakeResponse([b"abcd", b"efgh"])
    )
    item = fetch.Item("weights", "models/weights.bin", "https://example.invalid", 8)
    target = fetch.download(item, tmp_path, io.StringIO())

    assert target.read_bytes() == b"abcdefgh"
    assert not (tmp_path / "models" / "weights.bin.part").exists()


def test_truncated_download_is_removed(monkeypatch, tmp_path):
    monkeypatch.setattr(
        fetch.urllib.request, "urlopen", lambda url, timeout: FakeResponse([b"abcd"])
    )
    item = fetch.Item("weights", "models/weights.bin", "https://example.invalid", 8)
    with pytest.raises(fetch.FetchError, match="truncated"):
        fetch.download(item, tmp_path, io.StringIO())
    assert not (tmp_path / "models" / "weights.bin").exists()
    assert not (tmp_path / "models" / "weights.bin.part").exists()


def test_network_error_names_the_url(monkeypatch, tmp_path):
    def boom(url, timeout):
        raise OSError("connection reset")

    monkeypatch.setattr(fetch.urllib.request, "urlopen", boom)
    item = fetch.Item("weights", "models/weights.bin", "https://example.invalid/weights.bin", 8)
    with pytest.raises(fetch.FetchError, match="connection reset"):
        fetch.download(item, tmp_path, io.StringIO())


def test_run_declines_without_touching_disk(tmp_path):
    out = io.StringIO()
    code = fetch.run(
        tmp_path, ask=lambda question: "n", stream=out, manifest=_manifest(tmp_path)
    )
    assert code == 1
    assert "nothing downloaded" in out.getvalue()
    assert not (tmp_path / "models").exists()


def test_run_accepts_default_yes(monkeypatch, tmp_path):
    monkeypatch.setattr(
        fetch.urllib.request, "urlopen", lambda url, timeout: FakeResponse([b"abcdefgh"])
    )
    out = io.StringIO()
    code = fetch.run(tmp_path, ask=lambda question: "", stream=out, manifest=_manifest(tmp_path))
    assert code == 0
    assert (tmp_path / "models" / "weights.bin").read_bytes() == b"abcdefgh"


def test_run_reports_when_nothing_is_missing(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "weights.bin").write_bytes(b"x" * 8)
    out = io.StringIO()
    assert fetch.run(tmp_path, stream=out, manifest=_manifest(tmp_path)) == 0
    assert "already here" in out.getvalue()
