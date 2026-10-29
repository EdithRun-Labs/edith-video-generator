"""Rhubarb Lip Sync: mouth-shape cues from a finished wav.

The binary is a release download the user places under tools/rhubarb/, never
something this repository ships. On Windows it is rhubarb.exe, which the
manifest resolution handles from the single name `tools/rhubarb/rhubarb`.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .deps import load_manifest, platform_key, resolve_binary
from .spec import MOUTH_SHAPES

PROGRAM = "tools/rhubarb/rhubarb"
SHAPES = MOUTH_SHAPES
TIMEOUT_SEC = 3600


class RhubarbError(RuntimeError):
    """Lip sync cannot run here, with a message that says what to do about it."""


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    shape: str


def find(root: Path, platform: str | None = None) -> Path | None:
    return resolve_binary(PROGRAM, root, platform or platform_key())


def _install_hint() -> str:
    dependency = next((d for d in load_manifest().dependencies if d.id == "rhubarb"), None)
    if dependency is None:
        return "see the rhubarb-lip-sync releases page"
    hint = dependency.hint(platform_key())
    return f"{hint} ({dependency.home})" if hint else dependency.home


def run(audio: Path, out: Path, root: Path, platform: str | None = None) -> list[Cue]:
    """Run Rhubarb over one wav and return the mouth cues."""
    binary = find(root, platform)
    if binary is None:
        raise RhubarbError(
            f"Rhubarb is not installed: {PROGRAM} was not found. {_install_hint()}"
        )
    audio = Path(audio)
    if not audio.exists():
        raise RhubarbError(f"no audio at {audio}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    command = [str(binary), "--exportFormat", "json", "--output", str(out.resolve()), str(audio.resolve())]
    try:
        completed = subprocess.run(
            command,
            cwd=str(binary.parent),  # Rhubarb looks for res/ next to itself
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RhubarbError(f"Rhubarb did not run: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RhubarbError(f"Rhubarb failed ({completed.returncode}): {detail[:400]}")
    if not out.exists():
        raise RhubarbError(f"Rhubarb reported success but wrote nothing to {out}")
    return parse(json.loads(out.read_text()))


def cues_for(
    audio: Path, out: Path, key: str, root: Path, platform: str | None = None, force: bool = False
) -> list[Cue]:
    """Mouth cues for one wav, reused from `out` while its key still matches.

    The key is the clip key: text, voice and speed. An unchanged paragraph is
    never sent through Rhubarb twice, which is what makes rebuilds cheap.
    """
    out = Path(out)
    if not force:
        cached = _cached(out, key)
        if cached is not None:
            return cached
    cues = run(audio, out, root, platform)
    payload = json.loads(out.read_text())
    payload["key"] = key
    out.write_text(json.dumps(payload))
    return cues


def _cached(out: Path, key: str) -> list[Cue] | None:
    if not out.exists():
        return None
    try:
        payload = json.loads(out.read_text())
        if not isinstance(payload, dict) or payload.get("key") != key:
            return None
        return parse(payload)
    except (OSError, json.JSONDecodeError, RhubarbError):
        return None


def parse(payload: dict) -> list[Cue]:
    """Read Rhubarb's own JSON shape into cues, rejecting anything unexpected."""
    cues = payload.get("mouthCues") if isinstance(payload, dict) else None
    if not isinstance(cues, list) or not cues:
        raise RhubarbError("Rhubarb output has no mouthCues")
    parsed: list[Cue] = []
    for item in cues:
        try:
            start, end = float(item["start"]), float(item["end"])
            shape = str(item["value"]).strip().upper()
        except (KeyError, TypeError, ValueError) as exc:
            raise RhubarbError(f"Rhubarb cue is malformed: {item!r}") from exc
        if shape not in SHAPES:
            raise RhubarbError(f"unknown mouth shape {shape!r}; expected one of {SHAPES}")
        parsed.append(Cue(start, end, shape))
    return parsed
