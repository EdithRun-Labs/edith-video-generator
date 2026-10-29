"""The dependency manifest: what the tool needs, without shipping any of it."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

MANIFEST = Path(__file__).resolve().parents[1] / "deps.yaml"


class Check(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: list[str] | None = None
    expect: str | None = None
    path: str | list[str] | None = None


class Download(BaseModel):
    """A file the tool may fetch for you, pinned to a size it can verify."""

    model_config = ConfigDict(extra="forbid")

    path: str
    url: str
    size: int = Field(gt=0)


class Dependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    why: str
    required: bool = True
    version: str
    home: str
    check: Check | None = None
    install: dict[str, str] = Field(default_factory=dict)
    files: list[Download] = Field(default_factory=list)
    note: str | None = None

    def hint(self, platform: str) -> str | None:
        return self.install.get(platform) or self.install.get("linux")


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = Field(alias="schema")
    dependencies: list[Dependency]


def load_manifest(path: Path = MANIFEST) -> Manifest:
    return Manifest.model_validate(yaml.safe_load(path.read_text()))


def platform_key() -> str:
    if sys.platform.startswith("darwin"):
        return "darwin"
    if sys.platform.startswith("win"):
        return "win32"
    return "linux"


def probe(dep: Dependency, root: Path, platform: str | None = None) -> tuple[bool, str]:
    """Return (present, detail) for one dependency, without installing anything."""
    platform = platform or platform_key()
    check = dep.check
    if check is None:
        return False, "no check declared"
    if check.path:
        wanted = [check.path] if isinstance(check.path, str) else check.path
        missing = [name for name in wanted if not (root / name).exists()]
        if missing:
            return False, f"missing {', '.join(missing)}"
        return True, f"found {', '.join(wanted)}"
    if check.command:
        binary = check.command[0]
        resolved = resolve_binary(binary, root, platform)
        if not resolved:
            return False, f"{binary} not found"
        try:
            out = subprocess.run(
                [str(resolved), *check.command[1:]],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"{binary} found but did not run: {exc}"
        text = (out.stdout or "") + (out.stderr or "")
        if check.expect and check.expect not in text:
            return False, f"{binary} found but does not report {check.expect!r}"
        return True, f"{binary} ok"
    return False, "check has neither command nor path"


def resolve_binary(binary: str, root: Path, platform: str) -> Path | None:
    """Find a program declared in the manifest.

    Windows executables carry a .exe suffix, so a manifest can name `rhubarb`
    once and still resolve `tools/rhubarb/rhubarb.exe`. A path is resolved
    against the repository root and nowhere else; only a bare name falls back
    to PATH, so a project folder cannot pick up a binary that is not its own.
    """
    candidate = Path(binary)
    if not candidate.is_absolute():
        candidate = root / candidate
    names = [candidate]
    if platform == "win32":
        names.append(candidate.with_name(candidate.name + ".exe"))
    for path in names:
        if path.is_file():
            return path
    if len(Path(binary).parts) > 1:
        return None
    found = shutil.which(binary)
    return Path(found) if found else None
