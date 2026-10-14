import pytest

from agent import storage


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point storage at a temporary folder so tests never touch your real plants."""
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "PLANTS_PATH", tmp_path / "plants.json")
    return tmp_path
