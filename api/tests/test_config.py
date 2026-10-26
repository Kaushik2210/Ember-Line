from pathlib import Path

from emberline.config import API_DIR, Settings


def test_relative_data_dir_is_relative_to_the_api_folder() -> None:
    s = Settings(data_dir=Path("./data"), firms_map_key="x")
    assert s.data_dir == (API_DIR / "data").resolve()


def test_absolute_data_dir_is_kept(tmp_path: Path) -> None:
    assert Settings(data_dir=tmp_path).data_dir == tmp_path


def test_default_does_not_depend_on_the_working_directory(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    assert Settings().data_dir.is_absolute()
