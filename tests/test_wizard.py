import shutil
from pathlib import Path

import pytest
import yaml

from edith import wizard
from edith.deps import load_manifest, resolve_binary
from edith.spec import load_project

ROOT = Path(__file__).resolve().parents[1]
DEMO_SOURCE = ROOT / "examples" / "demo" / "source.md"


def test_markdown_splits_on_headings():
    scenes = wizard.split_scenes(DEMO_SOURCE.read_text(), "markdown", 180)
    assert [s["id"] for s in scenes] == ["S01", "S02", "S03", "S04", "S05"]
    assert scenes[0]["title"] == "Introduction"
    assert scenes[1]["title"] == "The problem"
    assert all(s["target_sec"] >= wizard.MIN_SCENE_SEC for s in scenes)


def test_duration_is_distributed_by_words():
    scenes = wizard.split_scenes(DEMO_SOURCE.read_text(), "markdown", 300)
    total = sum(s["target_sec"] for s in scenes)
    assert abs(total - 300) <= 300 * 0.15


def test_plain_text_splits_by_word_budget():
    text = "\n\n".join(f"Sentence {i} " + "word " * 60 for i in range(10))
    scenes = wizard.split_scenes(text, "text", 120)
    assert len(scenes) > 1
    assert all(s["paragraphs"] for s in scenes)


def test_empty_source_is_rejected():
    with pytest.raises(ValueError, match="no usable text"):
        wizard.split_scenes("   \n\n  ", "text", 60)


def test_build_from_answers_produces_a_valid_spec(tmp_path):
    answers = {
        "title": "A test video",
        "source_file": "source.md",
        "duration_min": "3",
        "palette": "dark",
        "avatar_enabled": True,
        "avatar_name": "Kim",
    }
    shutil.copy(DEMO_SOURCE, tmp_path / "source.md")
    spec = wizard.build_from_answers(answers, tmp_path)
    path = wizard.save(spec, tmp_path / "project.yaml")
    project = load_project(path)
    assert project.meta.title == "A test video"
    assert project.style.palette.background == "#11151c"
    assert project.avatar.enabled and project.avatar.name == "Kim"
    assert len(project.scenes) == 5


def test_wizard_run_writes_a_valid_spec(tmp_path):
    shutil.copy(DEMO_SOURCE, tmp_path / "source.md")
    replies = iter(
        [
            "Bakery operations",
            "",
            "DEMO 101",
            "Kulkarni",
            "source.md",
            "3",
            "split",
            "warm",
            "#b4531f",
            "Inter",
            "bottom",
            "bf_emma",
            "1.05",
            "no",
        ]
    )
    lines: list[str] = []
    out = tmp_path / "project.yaml"
    wizard.run(out, ask=lambda _prompt: next(replies), tell=lines.append, force=False)

    project = load_project(out)
    assert project.meta.title == "Bakery operations"
    assert project.style.layout == "split"
    assert project.voice.voice == "bf_emma"
    assert project.voice.speed == pytest.approx(1.05)
    assert project.avatar.enabled is False
    assert any("wrote" in line for line in lines)


def test_save_refuses_to_overwrite(tmp_path):
    path = tmp_path / "project.yaml"
    path.write_text("existing")
    with pytest.raises(FileExistsError):
        wizard.save({"meta": {}}, path)
    wizard.save({"meta": {}}, path, force=True)
    assert yaml.safe_load(path.read_text()) == {"meta": {}}


def test_windows_binary_resolution_finds_exe(tmp_path):
    tools = tmp_path / "tools" / "rhubarb"
    tools.mkdir(parents=True)
    (tools / "rhubarb.exe").write_text("")
    assert resolve_binary("tools/rhubarb/rhubarb", tmp_path, "win32") == tools / "rhubarb.exe"
    assert resolve_binary("tools/rhubarb/rhubarb", tmp_path, "darwin") is None


def test_manifest_checks_both_kokoro_files():
    manifest = load_manifest()
    kokoro = next(dep for dep in manifest.dependencies if dep.id == "kokoro-model")
    assert isinstance(kokoro.check.path, list)
    assert any("voices" in name for name in kokoro.check.path)
