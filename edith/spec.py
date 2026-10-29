"""The project spec: one YAML file describing everything about a video.

Nothing about style, subject or length is baked into this package. A spec either
validates or it doesn't; warnings are things worth looking at, never blockers.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
SCENE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,15}$")
DURATION_TOLERANCE = 0.10
MOUTH_SHAPES = "ABCDEFGHX"


def _hex(value: str) -> str:
    if not HEX.match(value):
        raise ValueError(f"{value!r} is not a #rrggbb colour")
    return value.lower()


def avatar_image(folder: Path, shape: str) -> Path | None:
    """The PNG for one mouth shape, matched without caring about file-name case."""
    if not folder.is_dir():
        return None
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and entry.suffix.lower() == ".png" and entry.stem.upper() == shape:
            return entry
    return None


Hex = Annotated[str, AfterValidator(_hex)]
Layout = Literal["screen", "fullbleed", "split"]
DiagramType = Literal["flow", "timeline", "comparison", "bar", "table", "cycle", "list"]
Provider = Literal["kokoro-onnx", "kokoro-mlx"]


class SpecError(Exception):
    """A spec that cannot be used, with a message meant for a human."""


class Font(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str = Field(min_length=1)
    file: str | None = Field(default=None, description="path to a font file, relative to the spec")


class Fonts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: Font
    heading: Font | None = None


class Palette(BaseModel):
    model_config = ConfigDict(extra="forbid")

    background: Hex
    text: Hex
    accent: Hex
    surface: Hex | None = None
    text_muted: Hex | None = None
    on_accent: Hex | None = None
    hairline: Hex | None = None


class Captions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: Literal["bottom", "top"] = "bottom"
    max_chars_per_line: int = Field(default=42, ge=20, le=90)
    burned_in: bool = True
    srt: bool = True


class Canvas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    fps: int = Field(default=30, ge=1, le=120)


class Style(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Layout = "screen"
    palette: Palette
    fonts: Fonts
    captions: Captions = Field(default_factory=Captions)
    canvas: Canvas = Field(default_factory=Canvas)


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None
    language: str = "en"
    branding: str | None = Field(default=None, description="a line shown on the title frame")

    @field_validator("date", mode="before")
    @classmethod
    def _iso_date(cls, value: object) -> str | None:
        # YAML turns 2026-11-03 into a date object; keep it as text everywhere else.
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str = Field(min_length=1)
    kind: Literal["markdown", "text"] = "markdown"


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_sec: int = Field(gt=0)
    max_duration_sec: int | None = Field(default=None, gt=0)


class Voice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider = "kokoro-onnx"
    voice: str = "af_sarah"
    speed: float = Field(default=1.0, ge=0.5, le=1.5)
    disclosure: bool = Field(
        default=True, description="show that the narration is synthetic (EU AI Act Art. 50(4))"
    )


class Avatar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    name: str = "Presenter"
    preset: Literal["neutral", "workshop", "office"] = "neutral"
    position: Literal["corner", "side", "full"] = "corner"
    size: float = Field(default=0.34, ge=0.15, le=0.6, description="bust height, fraction of the frame")
    palette: dict[str, Hex] | None = None
    images: str | None = Field(
        default=None, description="folder holding one PNG per mouth shape; blank uses the vector presenter"
    )


class Diagram(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: DiagramType
    title: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class Paragraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    pages: list[int] = Field(default_factory=list, description="printed page numbers, if any")
    diagram: Diagram | None = None


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=1)
    target_sec: int = Field(gt=0)
    paragraphs: list[Paragraph] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not SCENE_ID.match(value):
            raise ValueError("scene ids are letters, digits, _ or -, and start with a letter")
        return value


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    source: Source
    target: Target
    voice: Voice = Field(default_factory=Voice)
    style: Style
    avatar: Avatar = Field(default_factory=Avatar)
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_scenes(self) -> Project:
        seen: set[str] = set()
        for scene in self.scenes:
            if scene.id in seen:
                raise ValueError(f"duplicate scene id {scene.id!r}")
            seen.add(scene.id)
        return self

    @property
    def total_target_sec(self) -> int:
        return sum(scene.target_sec for scene in self.scenes)

    @property
    def word_count(self) -> int:
        return sum(len(p.text.split()) for s in self.scenes for p in s.paragraphs)

    def warnings(self, base_dir: Path) -> list[str]:
        out: list[str] = []
        total = self.total_target_sec
        if total and abs(total - self.target.duration_sec) > self.target.duration_sec * DURATION_TOLERANCE:
            out.append(
                f"scenes add up to {total} s but target.duration_sec is {self.target.duration_sec} s"
            )
        if self.target.max_duration_sec and total > self.target.max_duration_sec:
            out.append(
                f"scenes add up to {total} s, over target.max_duration_sec {self.target.max_duration_sec} s"
            )
        source = base_dir / self.source.file
        if not source.exists():
            out.append(f"source file {self.source.file} does not exist yet (relative to the spec)")
        if self.avatar.enabled and not self.source.file:
            out.append("avatar is enabled but no source file is set")
        if self.avatar.images:
            folder = base_dir / self.avatar.images
            if not folder.is_dir():
                out.append(
                    f"avatar.images {self.avatar.images} is not a folder; the vector presenter will be used"
                )
            else:
                missing = [shape for shape in MOUTH_SHAPES if avatar_image(folder, shape) is None]
                if missing:
                    out.append(
                        f"avatar.images {self.avatar.images} has no PNG for {', '.join(missing)}; "
                        "the vector presenter will be used"
                    )
        return out

    def summary(self) -> str:
        minutes, seconds = divmod(self.total_target_sec, 60)
        voice = f"{self.voice.provider}:{self.voice.voice} at x{self.voice.speed:g}"
        avatar = f"{self.avatar.preset} ({self.avatar.name})" if self.avatar.enabled else "off"
        return "\n".join(
            [
                f"title      {self.meta.title}",
                f"scenes     {len(self.scenes)}, planned {minutes}:{seconds:02d}",
                f"words      {self.word_count}",
                f"layout     {self.style.layout}",
                f"voice      {voice}",
                f"avatar     {avatar}",
            ]
        )


def load_project(path: str | Path) -> Project:
    """Load and validate a spec. Raises SpecError with a readable message."""
    path = Path(path)
    if not path.exists():
        raise SpecError(f"no spec at {path}")
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise SpecError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise SpecError(f"{path} must be a YAML mapping with meta/source/target/style/scenes")
    try:
        project = Project.model_validate(raw)
    except ValidationError as exc:
        raise SpecError(_format_validation(exc)) from exc
    return project


def _format_validation(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        where = ".".join(str(part) for part in err["loc"]) or "spec"
        lines.append(f"  {where}: {err['msg']}")
    return "spec is invalid:\n" + "\n".join(lines)
