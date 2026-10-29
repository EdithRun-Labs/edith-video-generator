"""Local text-to-speech: one small adapter per engine, one file per paragraph.

Two engines, neither of them paid:

  kokoro-onnx   CPU through onnxruntime, runs on Windows, macOS and Linux
  kokoro-mlx    Apple silicon only; pip installs its own weights

Both take (text, voice, speed) and return mono float samples, so everything
downstream — the runtime budget, caption timing, lip sync — is engine-agnostic.
Nothing is vendored: the model files are fetched by the user and found by path.

Synthesis is cached per paragraph by a key over (text, provider, voice, speed),
so changing one paragraph re-renders one paragraph, not the whole script.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

import yaml

from .spec import Project, Voice

# A starting menu, not the full set: voices-v1.0.bin holds 54. Once the model is
# present the engine reports the real list and this is only a fallback.
VOICES = ["af_sarah", "af_heart", "af_bella", "af_nicole", "am_michael", "bf_emma", "bm_george"]

EXTRAS = {"kokoro-onnx": "tts-onnx", "kokoro-mlx": "tts-mlx"}
MODULES = {"kokoro-onnx": "kokoro_onnx", "kokoro-mlx": "mlx_audio"}
MODEL_FILES = {"kokoro-onnx": ["models/kokoro-v1.0.onnx", "models/voices-v1.0.bin"]}
MLX_REPO = "mlx-community/Kokoro-82M-bf16"

# Kokoro degrades past roughly 500 phonemes, so text is fed in sentence-sized
# pieces. The gaps make the joins sound deliberate rather than clipped.
CHUNK_CHARS = 380
GAP_SEC = 0.18
HEAD_SEC = 0.08
TAIL_SEC = 0.30
SAMPLE_RATE = 24000

INDEX = "clips.yaml"
LANG = {"en": "en-us", "en-gb": "en-gb", "en-us": "en-us"}

SENTENCE = re.compile(r"(?<=[.!?])\s+")


class EngineMissing(RuntimeError):
    """The engine cannot run yet, with a message that says what to do about it."""


@dataclass(frozen=True)
class Clip:
    scene_id: str
    index: int
    path: Path
    duration_sec: float
    reused: bool = False


def _sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def clip_key(text: str, voice: Voice) -> str:
    return _sha("\x1f".join([text, voice.provider, voice.voice, f"{voice.speed:.3f}"]))


def chunk_text(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Split at sentence ends into pieces under `limit` characters."""
    pieces: list[str] = []
    current = ""
    for sentence in SENTENCE.split(" ".join(text.split())):
        if len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_hard_split(sentence, limit))
            continue
        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= limit:
            current = f"{current} {sentence}"
        else:
            pieces.append(current)
            current = sentence
    if current:
        pieces.append(current)
    return pieces


def _hard_split(sentence: str, limit: int) -> list[str]:
    out: list[str] = []
    rest = sentence
    while len(rest) > limit:
        cut = rest.rfind(" ", 0, limit)
        cut = cut if cut > 0 else limit
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        out.append(rest)
    return out


def _flatten(samples) -> list[float]:
    """Accept a flat list, a nested list or an array object; return flat floats."""
    if hasattr(samples, "tolist"):
        samples = samples.tolist()
    if samples and isinstance(samples[0], (list, tuple)):
        flat: list[float] = []
        for row in samples:
            flat.extend(row)
        return [float(x) for x in flat]
    return [float(x) for x in samples]


def write_wav(path: Path, samples, sample_rate: int) -> float:
    """Write mono 16-bit PCM and return the duration in seconds."""
    flat = _flatten(samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in flat))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return len(flat) / sample_rate if sample_rate else 0.0


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
    return frames / rate if rate else 0.0


def _silence(seconds: float, sample_rate: int) -> list[float]:
    return [0.0] * int(seconds * sample_rate)


def language(project_language: str) -> str:
    return LANG.get(project_language, project_language)


class _Engine:
    """Shared behaviour: build spoken samples for a piece of text."""

    provider = ""

    def say(self, text: str, voice: Voice, lang: str) -> tuple[list[float], int]:
        raise NotImplementedError

    def voices(self) -> list[str]:
        return list(VOICES)


class OnnxEngine(_Engine):
    provider = "kokoro-onnx"

    def __init__(self, root: Path) -> None:
        if importlib.util.find_spec(MODULES[self.provider]) is None:
            raise EngineMissing(
                f"{self.provider} is not installed. Run: python -m pip install -e \".[{EXTRAS[self.provider]}]\""
            )
        missing = [name for name in MODEL_FILES[self.provider] if not (root / name).exists()]
        if missing:
            raise EngineMissing(
                f"the {self.provider} weights are missing ({', '.join(missing)}). "
                "Fetch them from https://github.com/thewh1teagle/kokoro-onnx/releases into models/ "
                "(edith doctor shows the per-platform instruction)."
            )
        from kokoro_onnx import Kokoro  # imported late so the module works without it

        onnx, bins = (root / name for name in MODEL_FILES[self.provider])
        self._kokoro = Kokoro(str(onnx), str(bins))

    def say(self, text: str, voice: Voice, lang: str) -> tuple[list[float], int]:
        samples, rate = self._kokoro.create(text, voice=voice.voice, speed=voice.speed, lang=lang)
        return _flatten(samples), int(rate)

    def voices(self) -> list[str]:
        try:
            found = self._kokoro.get_voices()
        except Exception:  # the engine's own list is a nicety, not a requirement
            return list(VOICES)
        return sorted(found) or list(VOICES)


class MlxEngine(_Engine):
    provider = "kokoro-mlx"

    def __init__(self, root: Path) -> None:
        if importlib.util.find_spec(MODULES[self.provider]) is None:
            raise EngineMissing(
                f"{self.provider} is not installed. Run: python -m pip install -e \".[{EXTRAS[self.provider]}]\""
            )
        from mlx_audio.tts.utils import load_model

        self._model = load_model(MLX_REPO)

    def say(self, text: str, voice: Voice, lang: str) -> tuple[list[float], int]:
        clips = list(self._model.generate(text=text, voice=voice.voice, speed=voice.speed))
        samples: list[float] = []
        rate = SAMPLE_RATE
        for clip in clips:
            samples.extend(_flatten(getattr(clip, "audio", clip)))
            rate = int(getattr(clip, "sample_rate", rate))
        return samples, rate


ENGINES = {"kokoro-onnx": OnnxEngine, "kokoro-mlx": MlxEngine}


def make_engine(voice: Voice, root: Path) -> _Engine:
    engine = ENGINES.get(voice.provider)
    if engine is None:
        raise EngineMissing(f"unknown voice provider {voice.provider!r}; choose one of {', '.join(ENGINES)}")
    return engine(root)


def engine_status(provider: str, root: Path) -> tuple[bool, str]:
    """Whether an engine could run here, without loading a model."""
    module = MODULES.get(provider)
    if module is None:
        return False, f"unknown provider {provider!r}"
    if importlib.util.find_spec(module) is None:
        return False, f'not installed: python -m pip install -e ".[{EXTRAS[provider]}]"'
    missing = [name for name in MODEL_FILES.get(provider, []) if not (root / name).exists()]
    if missing:
        return False, f"weights missing: {', '.join(missing)}"
    return True, "ready"


def list_voices(provider: str, root: Path) -> tuple[list[str], str]:
    """The engine's own voice list when it can be loaded, else the curated menu."""
    try:
        voice = Voice(provider=provider)  # type: ignore[arg-type]
    except ValueError:
        return list(VOICES), f"unknown provider {provider!r}; showing the curated list"
    try:
        engine = make_engine(voice, root)
    except EngineMissing:
        return list(VOICES), "curated list; install the weights to see all 54"
    return engine.voices(), "reported by the engine"


def speak(
    text: str,
    out: Path,
    voice: Voice,
    root: Path,
    lang: str = "en-us",
    engine: _Engine | None = None,
) -> float:
    """One piece of text to one wav file; returns the duration."""
    samples, rate = (engine or make_engine(voice, root)).say(text, voice, lang)
    padded = _silence(HEAD_SEC, rate) + samples + _silence(TAIL_SEC, rate)
    return write_wav(out, padded, rate)


def _load_index(out_dir: Path) -> dict:
    path = out_dir / INDEX
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_index(out_dir: Path, index: dict) -> None:
    (out_dir / INDEX).write_text(
        yaml.safe_dump(index, sort_keys=True, allow_unicode=True, default_flow_style=False)
    )


def synthesize_project(
    project: Project, out_dir: Path, root: Path, force: bool = False
) -> list[Clip]:
    """Render every paragraph of a project to its own wav, reusing unchanged ones."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = _load_index(out_dir)
    voice = project.voice
    lang = language(project.meta.language)
    engine: _Engine | None = None
    clips: list[Clip] = []

    for scene in project.scenes:
        for number, paragraph in enumerate(scene.paragraphs, start=1):
            key = clip_key(paragraph.text, voice)
            name = f"{scene.id}-{number:02d}.wav"
            path = out_dir / name
            entry = index.get(name) or {}
            if not force and path.exists() and entry.get("key") == key:
                clips.append(Clip(scene.id, number, path, wav_duration(path), reused=True))
                continue
            if engine is None:
                engine = make_engine(voice, root)
            samples, rate = engine.say(paragraph.text, voice, lang)
            padded = _silence(HEAD_SEC, rate) + samples + _silence(TAIL_SEC, rate)
            duration = write_wav(path, padded, rate)
            index[name] = {
                "key": key,
                "voice": voice.voice,
                "speed": voice.speed,
                "provider": voice.provider,
                "duration_sec": round(duration, 3),
                "words": len(paragraph.text.split()),
            }
            clips.append(Clip(scene.id, number, path, duration))

    _save_index(out_dir, index)
    return clips


def total_seconds(clips: list[Clip]) -> float:
    return sum(clip.duration_sec for clip in clips)
