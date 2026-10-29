import importlib.util
import wave

import pytest

from edith import rhubarb, tts
from edith.spec import Project, Voice


def _project(tmp_path, texts):
    (tmp_path / "source.md").write_text("# Source\n\nText.\n")
    return Project.model_validate(
        {
            "meta": {"title": "Test"},
            "source": {"file": "source.md"},
            "target": {"duration_sec": 60},
            "style": {
                "palette": {"background": "#ffffff", "text": "#111111", "accent": "#2255aa"},
                "fonts": {"body": {"family": "Inter"}},
            },
            "scenes": [
                {
                    "id": f"S{number:02d}",
                    "title": "Scene",
                    "target_sec": 30,
                    "paragraphs": [{"text": text}],
                }
                for number, text in enumerate(texts, start=1)
            ],
        }
    )


class StubEngine:
    def __init__(self):
        self.calls = []

    def say(self, text, voice, lang):
        self.calls.append(text)
        return [0.0] * 24000, 24000


def test_write_wav_round_trips_duration(tmp_path):
    path = tmp_path / "one.wav"
    duration = tts.write_wav(path, [0.0] * 24000, 24000)
    assert duration == pytest.approx(1.0)
    assert tts.wav_duration(path) == pytest.approx(1.0)
    with wave.open(str(path), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2


def test_write_wav_clips_samples_outside_range(tmp_path):
    path = tmp_path / "loud.wav"
    tts.write_wav(path, [4.0, -4.0] * 100, 1000)
    with wave.open(str(path), "rb") as handle:
        frames = handle.readframes(2)
    assert frames == b"\xff\x7f\x01\x80"


def test_chunk_text_keeps_short_text_whole():
    assert tts.chunk_text("One short sentence.") == ["One short sentence."]


def test_chunk_text_splits_at_sentence_ends_under_limit():
    sentences = [f"Sentence {n} is here." for n in range(80)]
    chunks = tts.chunk_text(" ".join(sentences), limit=200)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert " ".join(chunks).split() == " ".join(sentences).split()


def test_chunk_text_hard_splits_one_runaway_sentence():
    chunks = tts.chunk_text("word " * 300, limit=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_flatten_accepts_nested_and_array_like():
    class Wrapped:
        def tolist(self):
            return [[0.1, 0.2], [0.3]]

    assert tts._flatten([0.1, 0.2]) == [0.1, 0.2]
    assert tts._flatten([[0.1], [0.2, 0.3]]) == [0.1, 0.2, 0.3]
    assert tts._flatten(Wrapped()) == pytest.approx([0.1, 0.2, 0.3])


def test_clip_key_tracks_text_and_voice():
    voice = Voice()
    faster = voice.model_copy(update={"speed": 1.1})
    other = voice.model_copy(update={"voice": "bf_emma"})
    assert tts.clip_key("a b", voice) != tts.clip_key("a c", voice)
    assert tts.clip_key("a b", voice) != tts.clip_key("a b", faster)
    assert tts.clip_key("a b", voice) != tts.clip_key("a b", other)


def test_missing_engine_names_the_extra(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    with pytest.raises(tts.EngineMissing) as caught:
        tts.make_engine(Voice(), None)
    assert "tts-onnx" in str(caught.value)


def test_missing_weights_lists_both_files(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    with pytest.raises(tts.EngineMissing) as caught:
        tts.make_engine(Voice(), tmp_path)
    message = str(caught.value)
    assert "kokoro-v1.0.onnx" in message and "voices-v1.0.bin" in message


def test_engine_status_reports_weights_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    ready, detail = tts.engine_status("kokoro-onnx", tmp_path)
    assert ready is False
    assert "weights missing" in detail


def test_synthesize_project_reuses_unchanged_paragraphs(monkeypatch, tmp_path):
    engine = StubEngine()
    monkeypatch.setattr(tts, "make_engine", lambda voice, root: engine)
    project = _project(tmp_path, ["First paragraph.", "Second paragraph."])
    out = tmp_path / "audio"

    first = tts.synthesize_project(project, out, tmp_path)
    assert len(first) == 2
    assert [clip.reused for clip in first] == [False, False]
    assert len(engine.calls) == 2
    assert all(clip.path.exists() for clip in first)
    # 1 s of audio plus 0.08 s head and 0.30 s tail
    assert first[0].duration_sec == pytest.approx(1.38, abs=0.01)

    again = tts.synthesize_project(project, out, tmp_path)
    assert [clip.reused for clip in again] == [True, True]
    assert len(engine.calls) == 2

    edited = _project(tmp_path, ["First paragraph.", "Second one changed."])
    third = tts.synthesize_project(edited, out, tmp_path)
    assert [clip.reused for clip in third] == [True, False]
    assert engine.calls[-1] == "Second one changed."
    assert (out / tts.INDEX).exists()


def test_synthesize_project_force_rerenders(monkeypatch, tmp_path):
    engine = StubEngine()
    monkeypatch.setattr(tts, "make_engine", lambda voice, root: engine)
    project = _project(tmp_path, ["Only paragraph."])
    out = tmp_path / "audio"
    tts.synthesize_project(project, out, tmp_path)
    forced = tts.synthesize_project(project, out, tmp_path, force=True)
    assert [clip.reused for clip in forced] == [False]
    assert len(engine.calls) == 2


def test_find_rhubarb_resolves_exe_on_windows_only(tmp_path):
    binary = tmp_path / "tools" / "rhubarb" / "rhubarb.exe"
    binary.parent.mkdir(parents=True)
    binary.write_text("")
    assert rhubarb.find(tmp_path, "win32") == binary
    assert rhubarb.find(tmp_path, "darwin") is None


def test_parse_cues_reads_rhubarb_output():
    cues = rhubarb.parse(
        {
            "metadata": {"soundFile": "a.wav"},
            "mouthCues": [
                {"start": 0.0, "end": 0.12, "value": "X"},
                {"start": 0.12, "end": 0.4, "value": "b"},
            ],
        }
    )
    assert [(cue.start, cue.shape) for cue in cues] == [(0.0, "X"), (0.12, "B")]


@pytest.mark.parametrize(
    "payload",
    [{}, {"mouthCues": []}, {"mouthCues": [{"start": 0, "end": 1, "value": "Z"}]}, {"mouthCues": [{}]}],
)
def test_parse_rejects_bad_output(payload):
    with pytest.raises(rhubarb.RhubarbError):
        rhubarb.parse(payload)


def test_run_without_binary_explains_how_to_get_it(tmp_path):
    with pytest.raises(rhubarb.RhubarbError) as caught:
        rhubarb.run(tmp_path / "a.wav", tmp_path / "a.json", tmp_path)
    assert "tools/rhubarb/rhubarb" in str(caught.value)
