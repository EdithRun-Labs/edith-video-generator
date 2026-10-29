import json

import pytest

from edith import build
from edith.spec import Project
from edith.tts import Clip


def _project(tmp_path, scenes=2, paragraphs=2, author="Ada"):
    (tmp_path / "source.md").write_text("Text.\n")
    return Project.model_validate(
        {
            "meta": {"title": "Timing test", "author": author},
            "source": {"file": "source.md"},
            "target": {"duration_sec": 10},
            "style": {
                "palette": {"background": "#ffffff", "text": "#111111", "accent": "#2255aa"},
                "fonts": {"body": {"family": "Inter"}},
            },
            "scenes": [
                {
                    "id": f"S{number:02d}",
                    "title": f"Scene {number}",
                    "target_sec": 5,
                    "paragraphs": [
                        {"text": f"Scene {number} paragraph {index}. " + "word " * 8}
                        for index in range(1, paragraphs + 1)
                    ],
                }
                for number in range(1, scenes + 1)
            ],
        }
    )


def _clips(tmp_path, project, seconds=2.0):
    (tmp_path / "audio").mkdir(exist_ok=True)
    clips = []
    for scene in project.scenes:
        for number in range(1, len(scene.paragraphs) + 1):
            path = tmp_path / "audio" / f"{scene.id}-{number:02d}.wav"
            path.write_bytes(b"RIFF")
            clips.append(Clip(scene.id, number, path, seconds))
    return clips


def test_wrap_and_cues_follow_word_boundaries():
    text = "one two three four five six seven eight"
    lines = build.wrap(text, 12)
    assert all(len(line) <= 12 for line in lines)
    assert " ".join(lines).split() == text.split()

    parts = build.cue_texts(text, 12)
    assert all(part.count("\n") <= 1 for part in parts)
    assert " ".join(parts).split() == text.split()


def test_cues_cover_the_paragraph_in_order():
    text = " ".join(["word"] * 40)
    timed = build.cues(text, start=2.5, duration=6.0, fps=30, width=30)
    assert timed[0]["startFrame"] == 75
    assert all(a["endFrame"] <= b["startFrame"] for a, b in zip(timed, timed[1:]))
    assert timed[-1]["endFrame"] == 75 + 180
    assert all(cue["endFrame"] > cue["startFrame"] for cue in timed)


def test_srt_time_and_body():
    assert build.srt_time(0) == "00:00:00,000"
    assert build.srt_time(3661.5) == "01:01:01,500"
    body = build.to_srt(
        [{"startFrame": 30, "endFrame": 60, "text": "hello\nthere"}], fps=30
    )
    assert body.startswith("1\n00:00:01,000 --> 00:00:02,000\nhello there")


def test_props_use_measured_clip_times(tmp_path):
    project = _project(tmp_path)
    props, frames, flat = build.build_props(project, _clips(tmp_path, project), tmp_path, tmp_path)

    assert props["canvas"] == {"width": 1920, "height": 1080, "fps": 30}
    # title 2.5 s + two scenes of 4 s + 0.5 s pad each + credits 2.5 s
    assert frames == round(14.0 * 30)
    first, second = props["scenes"]
    assert first["startFrame"] == 75
    assert first["durationInFrames"] == round(4.5 * 30)
    assert second["startFrame"] == first["startFrame"] + first["durationInFrames"]
    assert first["paragraphs"][1]["startFrame"] == first["startFrame"] + 60
    assert first["paragraphs"][0]["audio"] == "audio/S01-01.wav"
    assert props["durationInFrames"] == frames


def test_each_scene_keeps_only_its_own_captions(tmp_path):
    project = _project(tmp_path, scenes=2, paragraphs=2)
    props, _, flat = build.build_props(project, _clips(tmp_path, project), tmp_path, tmp_path)
    for scene in props["scenes"]:
        end = scene["startFrame"] + scene["durationInFrames"]
        assert scene["captions"], "a scene should have captions"
        assert all(scene["startFrame"] <= cue["startFrame"] < end for cue in scene["captions"])
    assert sum(len(scene["captions"]) for scene in props["scenes"]) == len(flat)


def test_no_credits_without_author(tmp_path):
    project = _project(tmp_path, author=None)
    project.meta.date = None
    props, frames, _ = build.build_props(project, _clips(tmp_path, project), tmp_path, tmp_path)
    assert props["cards"]["creditsFrames"] == 0
    assert frames == round(11.5 * 30)


def test_missing_clip_is_an_error(tmp_path):
    project = _project(tmp_path)
    clips = _clips(tmp_path, project)[:-1]
    with pytest.raises(ValueError, match="run `edith voice --project` first"):
        build.build_props(project, clips, tmp_path, tmp_path)


def test_build_writes_props_audio_and_srt(tmp_path):
    project = _project(tmp_path)
    clips = _clips(tmp_path, project)
    video = tmp_path / "video"
    out = tmp_path / "build"
    render = build.build(project, clips, tmp_path, video, out)

    assert render.props == out / "props.json"
    assert render.srt == out / "captions.srt"
    assert json.loads(render.props.read_text())["durationInFrames"] == render.frames
    assert render.cues > 0
    assert (video / "public" / "audio" / "S01-01.wav").exists()
    assert render.srt.read_text().startswith("1\n")
