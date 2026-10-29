"""Interactive setup: answers in, a valid project spec out.

The wizard never invents content. It asks, it splits the user's own source text
into a first-pass scene list, and it writes a spec the validator accepts. Every
palette and voice below is a starting point the user can edit, not a house style.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import yaml

from . import tts

SEED_PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "background": "#f7f4ee",
        "surface": "#ffffff",
        "text": "#1d2430",
        "text_muted": "#5c6673",
        "accent": "#2f6b4f",
        "on_accent": "#ffffff",
        "hairline": "#d9d3c7",
    },
    "dark": {
        "background": "#11151c",
        "surface": "#1a2029",
        "text": "#eef2f7",
        "text_muted": "#98a3b3",
        "accent": "#5ac8a0",
        "on_accent": "#0b0f14",
        "hairline": "#2a3340",
    },
    "warm": {
        "background": "#fdf6ec",
        "surface": "#fffdf8",
        "text": "#2a2018",
        "text_muted": "#6b5c4c",
        "accent": "#b4531f",
        "on_accent": "#ffffff",
        "hairline": "#e6d8c6",
    },
}

VOICES = tts.VOICES
LAYOUTS = ["screen", "fullbleed", "split"]
AVATAR_PRESETS = ["neutral", "workshop", "office"]
AVATAR_POSITIONS = ["corner", "side", "full"]
WORDS_PER_SECOND = 2.5
MIN_SCENE_SEC = 15
WORDS_PER_SCENE = 220

HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _paragraphs(text: str) -> list[str]:
    return [block.strip().replace("\n", " ") for block in re.split(r"\n\s*\n", text) if block.strip()]


def split_scenes(text: str, kind: str, duration_sec: int) -> list[dict]:
    """Split the user's text into scenes: headings for markdown, word budget for plain text."""
    blocks: list[tuple[str, list[str]]] = []

    if kind == "markdown":
        matches = list(HEADING.finditer(text))
        preamble = text[: matches[0].start()] if matches else text
        preamble = re.sub(r"^#\s+.*$", "", preamble, count=1, flags=re.MULTILINE)
        if _paragraphs(preamble):
            blocks.append(("Introduction", _paragraphs(preamble)))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = _paragraphs(text[match.end() : end])
            if body:
                blocks.append((match.group(1), body))
    if not blocks:
        chunk: list[str] = []
        words = 0
        for para in _paragraphs(text):
            chunk.append(para)
            words += len(para.split())
            if words >= WORDS_PER_SCENE:
                blocks.append(("", chunk))
                chunk, words = [], 0
        if chunk:
            blocks.append(("", chunk))
    if not blocks:
        raise ValueError("the source file has no usable text")

    counts = [sum(len(p.split()) for p in paras) for _, paras in blocks]
    total = sum(counts) or 1
    out = []
    for number, ((title, paras), words) in enumerate(zip(blocks, counts), start=1):
        out.append(
            {
                "id": f"S{number:02d}",
                "title": title or f"Scene {number}",
                "target_sec": max(MIN_SCENE_SEC, round(words / total * duration_sec)),
                "paragraphs": [{"text": para} for para in paras],
            }
        )
    return out


def build_spec(answers: dict) -> dict:
    """Turn a flat dict of answers into a project spec."""
    duration_sec = int(round(float(answers.get("duration_min", 5)) * 60))
    palette = answers.get("palette", "light")
    palette = SEED_PALETTES[palette] if isinstance(palette, str) else dict(palette)
    if answers.get("accent"):
        palette["accent"] = answers["accent"]
    body_font = answers.get("font_body", "Inter")
    return {
        "meta": {
            "title": answers["title"],
            "subtitle": answers.get("subtitle") or None,
            "branding": answers.get("branding") or None,
            "author": answers.get("author") or None,
            "date": answers.get("date") or datetime.date.today().isoformat(),
            "language": answers.get("language", "en"),
        },
        "source": {
            "file": answers["source_file"],
            "kind": answers.get("source_kind", "markdown"),
        },
        "target": {"duration_sec": duration_sec, "max_duration_sec": int(duration_sec * 1.2)},
        "voice": {
            "provider": answers.get("provider", "kokoro-onnx"),
            "voice": answers.get("voice", "af_sarah"),
            "speed": float(answers.get("speed", 1.0)),
            "disclosure": bool(answers.get("disclosure", True)),
        },
        "style": {
            "layout": answers.get("layout", "screen"),
            "palette": palette,
            "fonts": {
                "body": {"family": body_font},
                "heading": {"family": answers.get("font_heading", body_font)},
            },
            "captions": {
                "position": answers.get("captions_position", "bottom"),
                "max_chars_per_line": int(answers.get("max_chars_per_line", 42)),
                "burned_in": True,
                "srt": True,
            },
        },
        "avatar": {
            "enabled": bool(answers.get("avatar_enabled", False)),
            "name": answers.get("avatar_name", "Presenter"),
            "preset": answers.get("avatar_preset", "neutral"),
            "position": answers.get("avatar_position", "corner"),
            "size": float(answers.get("avatar_size", 0.34)),
            "images": answers.get("avatar_images") or None,
        },
        "scenes": answers["scenes"],
    }


def build_from_answers(answers: dict, base_dir: Path) -> dict:
    """Same, but reads the source file to generate a first-pass scene list."""
    answers = dict(answers)
    if not answers.get("scenes"):
        source = (base_dir / answers["source_file"]).resolve()
        if not source.exists():
            raise FileNotFoundError(f"source file not found: {source}")
        answers["scenes"] = split_scenes(
            source.read_text(),
            answers.get("source_kind", "markdown"),
            int(round(float(answers.get("duration_min", 5)) * 60)),
        )
    return build_spec(answers)


def save(spec: dict, path: Path, force: bool = False) -> Path:
    path = Path(path)
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
    return path


def _ask(ask, label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = ask(f"{label}{suffix}: ").strip()
    return answer or default


def run(out: Path, ask=input, tell=print, *, force: bool = False) -> dict:
    """Ask the questions in order, build the spec, write it, print a summary."""
    tell("A few questions. Press enter to accept the value in brackets.\n")

    answers: dict = {}
    answers["title"] = _ask(ask, "Title of the video")
    answers["subtitle"] = _ask(ask, "Subtitle (optional)")
    answers["branding"] = _ask(ask, "Course or branding line (optional)")
    answers["author"] = _ask(ask, "Your name (optional)")
    answers["source_file"] = _ask(ask, "Source text file", "sources/text.md")
    answers["source_kind"] = "text" if answers["source_file"].endswith(".txt") else "markdown"
    answers["duration_min"] = _ask(ask, "Target length in minutes", "5")
    answers["layout"] = _ask(ask, f"Layout {LAYOUTS}", "screen")
    answers["palette"] = _ask(ask, f"Palette {list(SEED_PALETTES)}", "light")
    answers["accent"] = _ask(ask, "Accent colour override, #rrggbb (optional)")
    answers["font_body"] = _ask(ask, "Body font family", "Inter")
    answers["captions_position"] = _ask(ask, "Captions bottom|top", "bottom")
    answers["voice"] = _ask(ask, f"Voice {VOICES}", "af_sarah")
    answers["speed"] = _ask(ask, "Speaking speed", "1.0")
    answers["avatar_enabled"] = _ask(ask, "Show a presenter? yes|no", "no").lower().startswith("y")
    if answers["avatar_enabled"]:
        answers["avatar_name"] = _ask(ask, "Presenter name", "Presenter")
        answers["avatar_preset"] = _ask(ask, f"Presenter preset {AVATAR_PRESETS}", "neutral")
        answers["avatar_position"] = _ask(ask, f"Presenter position {AVATAR_POSITIONS}", "corner")
        answers["avatar_size"] = _ask(ask, "Presenter height, fraction of the frame", "0.34")
        answers["avatar_images"] = _ask(ask, "Mouth-shape PNG folder (optional)")

    base_dir = out.parent.resolve()
    try:
        spec = build_from_answers(answers, base_dir)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"\n{exc}\nPut your text there, or run again with the right path.")

    path = save(spec, out, force=force)
    tell(f"\nwrote {path}")
    tell(f"scenes {len(spec['scenes'])}, planned {spec['target']['duration_sec']} s")
    tell("next: edith validate " + str(path))
    return spec
