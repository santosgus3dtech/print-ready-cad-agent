import pytest


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("PRINTREADY_DATA_DIR", str(tmp_path / "data"))
