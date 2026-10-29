"""What the renderer needs: frame timings, wrapped captions, and audio in place.

The measured wav files decide the timing, not the plan. Every paragraph gets an
absolute start frame, captions are split at word boundaries and given a share of
their paragraph's duration in proportion to their length, and the same cues are
written as an SRT for anyone who wants soft subtitles too.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import rhubarb
from .spec import MOUTH_SHAPES, Font, Project, avatar_image
from .tts import Clip, clip_key

TITLE_SEC = 2.5
CREDITS_SEC = 2.5
SCENE_PAD_SEC = 0.5
CUE_LINES = 2


@dataclass(frozen=True)
class Render:
    props: Path
    srt: Path | None
    frames: int
    seconds: float
    cues: int


def wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def cue_texts(text: str, width: int) -> list[str]:
    lines = wrap(text, width)
    return ["\n".join(lines[i : i + CUE_LINES]) for i in range(0, len(lines), CUE_LINES)]


def cues(text: str, start: float, duration: float, fps: int, width: int) -> list[dict]:
    """Split one paragraph into timed display cues."""
    parts = cue_texts(text, width)
    if not parts:
        return []
    weights = [len(part.replace("\n", " ")) or 1 for part in parts]
    total = sum(weights)
    out: list[dict] = []
    cursor = start
    for part, weight in zip(parts, weights):
        share = duration * weight / total
        out.append(
            {
                "startFrame": round(cursor * fps),
                "endFrame": max(round((cursor + share) * fps), round(cursor * fps) + 1),
                "text": part,
            }
        )
        cursor += share
    return out


def srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def to_srt(compositions: list[dict], fps: int) -> str:
    blocks: list[str] = []
    for number, cue in enumerate(compositions, start=1):
        start = srt_time(cue["startFrame"] / fps)
        end = srt_time(cue["endFrame"] / fps)
        text = cue["text"].replace("\n", " ")
        blocks.append(f"{number}\n{start} --> {end}\n{text}\n")
    return "\n".join(blocks)


def _font(font: Font | None, base_dir: Path, public: Path) -> dict | None:
    if font is None:
        return None
    entry: dict = {"family": font.family, "src": None}
    if font.file:
        source = base_dir / font.file
        if source.exists():
            target = public / "fonts" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            entry["src"] = f"fonts/{source.name}"
    return entry


def _avatar(project: Project, base_dir: Path, public: Path) -> dict:
    """The presenter settings, plus the shape images once all of them are present."""
    avatar = project.avatar
    images: dict[str, str] | None = None
    if avatar.images:
        folder = base_dir / avatar.images
        found = {shape: avatar_image(folder, shape) for shape in MOUTH_SHAPES}
        if all(found.values()):
            target_dir = public / "avatar"
            target_dir.mkdir(parents=True, exist_ok=True)
            images = {}
            for shape, source in found.items():
                assert source is not None
                shutil.copy2(source, target_dir / f"{shape}.png")
                images[shape] = f"avatar/{shape}.png"
    return {
        "enabled": avatar.enabled,
        "name": avatar.name,
        "preset": avatar.preset,
        "position": avatar.position,
        "size": avatar.size,
        "palette": avatar.palette,
        "images": images,
    }


def mouth_cues(
    project: Project, clips: list[Clip], root: Path | None, force: bool = False
) -> dict[str, list[dict]]:
    """Mouth shapes per clip, in frames relative to that paragraph's start.

    Nothing happens unless the avatar is on. Rhubarb is optional, so a missing
    binary is a printed notice and a still face, never a failed build.
    """
    if not project.avatar.enabled or root is None:
        return {}
    fps = project.style.canvas.fps
    text_of = {
        (scene.id, index): paragraph.text
        for scene in project.scenes
        for index, paragraph in enumerate(scene.paragraphs, start=1)
    }
    out: dict[str, list[dict]] = {}
    try:
        for clip in clips:
            text = text_of.get((clip.scene_id, clip.index))
            if text is None:
                continue
            cues = rhubarb.cues_for(
                clip.path,
                clip.path.with_suffix(".json"),
                clip_key(text, project.voice),
                root,
                force=force,
            )
            out[clip.path.stem] = [
                {
                    "startFrame": round(cue.start * fps),
                    "endFrame": max(round(cue.end * fps), round(cue.start * fps) + 1),
                    "shape": cue.shape,
                }
                for cue in cues
            ]
    except rhubarb.RhubarbError as exc:
        print(f"lip sync skipped: {exc}")
        return {}
    return out


def build_props(
    project: Project,
    clips: list[Clip],
    base_dir: Path,
    public: Path,
    mouth: dict[str, list[dict]] | None = None,
) -> tuple[dict, int, list[dict]]:
    """Return (props, total frames, flat cue list in composition frames)."""
    fps = project.style.canvas.fps
    width = project.style.captions.max_chars_per_line
    by_scene: dict[str, list[Clip]] = {}
    for clip in clips:
        by_scene.setdefault(clip.scene_id, []).append(clip)

    cursor = TITLE_SEC
    scenes: list[dict] = []
    flat: list[dict] = []

    for scene in project.scenes:
        mine = sorted(by_scene.get(scene.id, []), key=lambda c: c.index)
        if len(mine) != len(scene.paragraphs):
            raise ValueError(
                f"{scene.id} has {len(scene.paragraphs)} paragraph(s) but {len(mine)} clip(s); "
                "run `edith voice --project` first"
            )
        start = cursor
        paragraphs = []
        scene_cues: list[dict] = []
        for paragraph, clip in zip(scene.paragraphs, mine):
            audio = f"audio/{clip.path.name}"
            paragraphs.append(
                {
                    "startFrame": round(cursor * fps),
                    "durationInFrames": max(1, round(clip.duration_sec * fps)),
                    "text": paragraph.text,
                    "pages": paragraph.pages,
                    "diagram": paragraph.diagram.model_dump() if paragraph.diagram else None,
                    "audio": audio,
                    "mouth": (mouth or {}).get(clip.path.stem, []),
                }
            )
            flat.extend(cues(paragraph.text, cursor, clip.duration_sec, fps, width))
            scene_cues.extend(cues(paragraph.text, cursor, clip.duration_sec, fps, width))
            cursor += clip.duration_sec
        cursor += SCENE_PAD_SEC
        scenes.append(
            {
                "id": scene.id,
                "title": scene.title,
                "startFrame": round(start * fps),
                "durationInFrames": max(1, round((cursor - start) * fps)),
                "paragraphs": paragraphs,
                "captions": scene_cues,
            }
        )

    credits = CREDITS_SEC if (project.meta.author or project.meta.date) else 0
    total = round((cursor + credits) * fps)

    props = {
        "meta": project.meta.model_dump(),
        "canvas": project.style.canvas.model_dump(),
        "durationInFrames": total,
        "layout": project.style.layout,
        "palette": project.style.palette.model_dump(exclude_none=True),
        "fonts": {
            "body": _font(project.style.fonts.body, base_dir, public),
            "heading": _font(project.style.fonts.heading, base_dir, public),
        },
        "captions": {
            "position": project.style.captions.position,
            "burned_in": project.style.captions.burned_in,
        },
        "cards": {
            "titleFrames": round(TITLE_SEC * fps),
            "creditsFrames": round(credits * fps),
        },
        "disclosure": (
            f"Narration generated locally · {project.voice.provider} · synthetic voice"
            if project.voice.disclosure
            else None
        ),
        "avatar": _avatar(project, base_dir, public),
        "scenes": scenes,
    }
    return props, total, flat


def build(
    project: Project,
    clips: list[Clip],
    base_dir: Path,
    video_dir: Path,
    out_dir: Path,
    root: Path | None = None,
    force_lipsync: bool = False,
) -> Render:
    """Copy audio and fonts into the renderer's public folder, write props and SRT."""
    public = video_dir / "public"
    audio_dir = public / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for clip in clips:
        shutil.copy2(clip.path, audio_dir / clip.path.name)

    mouth = mouth_cues(project, clips, root, force=force_lipsync)
    props, frames, flat = build_props(project, clips, base_dir, public, mouth=mouth)

    out_dir.mkdir(parents=True, exist_ok=True)
    props_path = out_dir / "props.json"
    props_path.write_text(json.dumps(props, indent=2, ensure_ascii=False))

    srt_path: Path | None = None
    if project.style.captions.srt and flat:
        srt_path = out_dir / "captions.srt"
        srt_path.write_text(to_srt(flat, project.style.canvas.fps))

    cued = sum(len(scene["captions"]) for scene in props["scenes"])
    return Render(
        props=props_path,
        srt=srt_path,
        frames=frames,
        seconds=frames / project.style.canvas.fps,
        cues=cued,
    )
