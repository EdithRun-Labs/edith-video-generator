from pathlib import Path

import pytest
import yaml

from edith.deps import load_manifest, platform_key, probe
from edith.spec import SpecError, load_project

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo" / "project.yaml"


def _spec(**overrides):
    raw = yaml.safe_load(DEMO.read_text())
    raw.update(overrides)
    return raw


def test_demo_project_loads():
    project = load_project(DEMO)
    assert len(project.scenes) == 4
    assert project.total_target_sec == 61
    assert project.style.palette.accent == "#2f6b4f"


def test_demo_has_no_warnings():
    assert load_project(DEMO).warnings(DEMO.parent) == []


def test_duplicate_scene_ids_rejected(tmp_path):
    raw = _spec()
    raw["scenes"][1]["id"] = raw["scenes"][0]["id"]
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(SpecError, match="duplicate scene id"):
        load_project(path)


def test_bad_colour_rejected(tmp_path):
    raw = _spec()
    raw["style"]["palette"]["accent"] = "green"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(SpecError, match="is not a #rrggbb colour"):
        load_project(path)


def test_unknown_key_rejected(tmp_path):
    raw = _spec()
    raw["style"]["font"] = {"body": {"family": "Inter"}}
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(SpecError, match="font"):
        load_project(path)


def test_missing_source_is_a_warning_not_an_error(tmp_path):
    raw = _spec()
    raw["source"]["file"] = "does-not-exist.md"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    project = load_project(path)
    assert any("does not exist" in w for w in project.warnings(tmp_path))


def test_duration_drift_warns(tmp_path):
    raw = _spec()
    raw["scenes"] = raw["scenes"][:1]
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    project = load_project(path)
    assert any("add up to" in w for w in project.warnings(DEMO.parent))


def test_avatar_defaults_are_ready_for_the_renderer():
    avatar = load_project(DEMO).avatar
    assert avatar.enabled is True
    assert avatar.position == "corner"
    assert avatar.size == pytest.approx(0.34)
    assert avatar.images is None


def test_avatar_accepts_every_position(tmp_path):
    for position in ("corner", "side", "full"):
        raw = _spec()
        raw["avatar"]["position"] = position
        path = tmp_path / f"{position}.yaml"
        path.write_text(yaml.safe_dump(raw))
        assert load_project(path).avatar.position == position


def test_avatar_rejects_an_unknown_position(tmp_path):
    raw = _spec()
    raw["avatar"]["position"] = "left"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(SpecError, match="avatar.position"):
        load_project(path)


def test_avatar_size_accepts_the_range_and_rejects_the_edges(tmp_path):
    raw = _spec()
    raw["avatar"]["size"] = 0.2
    small = tmp_path / "small.yaml"
    small.write_text(yaml.safe_dump(raw))
    assert load_project(small).avatar.size == pytest.approx(0.2)

    raw["avatar"]["size"] = 0.95
    too_big = tmp_path / "big.yaml"
    too_big.write_text(yaml.safe_dump(raw))
    with pytest.raises(SpecError, match="avatar.size"):
        load_project(too_big)


def test_avatar_missing_image_folder_warns(tmp_path):
    raw = _spec()
    raw["avatar"]["images"] = "art"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(raw))
    project = load_project(path)
    assert any("avatar.images" in warning and "art" in warning for warning in project.warnings(tmp_path))


def test_manifest_declares_the_heavy_externals():
    manifest = load_manifest()
    ids = {dep.id for dep in manifest.dependencies}
    assert {"ffmpeg", "node", "kokoro-model"} <= ids
    assert all(dep.home.startswith("https://") for dep in manifest.dependencies)


def test_every_dependency_has_a_hint_for_this_platform():
    manifest = load_manifest()
    assert platform_key() in {"darwin", "win32", "linux"}
    for dep in manifest.dependencies:
        assert dep.hint(platform_key()), f"{dep.id} has no install hint"


def test_probe_reports_missing_without_raising():
    manifest = load_manifest()
    fonts = next(dep for dep in manifest.dependencies if dep.id == "fonts")
    present, detail = probe(fonts, ROOT)
    assert present is False
    assert "missing" in detail
