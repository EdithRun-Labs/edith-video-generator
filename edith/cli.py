"""Command line entry point: python -m edith <command>."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from . import build as buildmod
from . import fetch, tts, wizard
from .deps import load_manifest, platform_key, probe
from .spec import Project, SpecError, Voice, load_project

ROOT = Path(__file__).resolve().parents[1]
SPEECH_DRIFT = 0.20
REMOTION_CLI = Path("node_modules/@remotion/cli/remotion-cli.js")
ENTRY = "src/index.ts"
COMPOSITION = "Video"


def cmd_validate(args: argparse.Namespace) -> int:
    spec = Path(args.spec)
    try:
        project = load_project(spec)
    except SpecError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(project.summary())
    warnings = project.warnings(spec.resolve().parent)
    if warnings:
        print("\nwarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nno warnings")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    platform = platform_key()
    print(f"platform {platform}")
    print("no AI service, no API key, no account — everything below runs locally\n")
    missing_required = 0
    for dep in manifest.dependencies:
        present, detail = probe(dep, ROOT, platform)
        state = "ok" if present else ("MISSING" if dep.required else "absent (optional)")
        if not present and dep.required:
            missing_required += 1
        print(f"[{state}] {dep.id} {dep.version} — {dep.why}")
        print(f"         {detail}")
        if not present and not args.quiet:
            hint = dep.hint(platform)
            if hint:
                print(f"         get it: {hint}")
            print(f"         home:   {dep.home}")
    if missing_required:
        print(f"\n{missing_required} required item(s) missing. Nothing is downloaded for you.")
        return 1
    print("\neverything required is present")
    return 0


def _mmss(seconds: float) -> str:
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes}:{rest:02d}"


def _drift(spoken: float, planned: float) -> str:
    """Measured speech against the planned scene length, in both directions."""
    if spoken > planned * (1 + SPEECH_DRIFT):
        return "over"
    if spoken < planned * (1 - SPEECH_DRIFT):
        return "under"
    return "ok"


def cmd_voice(args: argparse.Namespace) -> int:
    provider = args.provider or "kokoro-onnx"

    if args.project:
        try:
            project = load_project(args.project)
        except SpecError as exc:
            print(exc, file=sys.stderr)
            return 1
        if args.voice or args.speed or args.provider:
            project = project.model_copy(
                update={
                    "voice": project.voice.model_copy(
                        update={
                            "provider": provider,
                            "voice": args.voice or project.voice.voice,
                            "speed": args.speed or project.voice.speed,
                        }
                    )
                }
            )
        out = Path(args.out or "audio")
        try:
            clips = tts.synthesize_project(project, out, ROOT, force=args.force)
        except tts.EngineMissing as exc:
            print(exc, file=sys.stderr)
            return 1
        for scene in project.scenes:
            mine = [clip for clip in clips if clip.scene_id == scene.id]
            spoken = tts.total_seconds(mine)
            print(
                f"{scene.id}  {len(mine):>2} clip(s)  "
                f"{_mmss(spoken)} spoken vs {_mmss(scene.target_sec)} planned "
                f"{_drift(spoken, scene.target_sec)}"
            )
        total = tts.total_seconds(clips)
        reused = sum(1 for clip in clips if clip.reused)
        print(f"\ntotal {total:.1f} s ({_mmss(total)}), {len(clips)} clip(s), {reused} reused")
        print(f"index {out / tts.INDEX}")
        return 0

    if args.text:
        voice = Voice(provider=provider, voice=args.voice or "af_sarah", speed=args.speed or 1.0)  # type: ignore[arg-type]
        out = Path(args.out or f"{voice.voice}.wav")
        try:
            duration = tts.speak(args.text, out, voice, ROOT)
        except tts.EngineMissing as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"wrote {out} ({duration:.1f} s, {_mmss(duration)})")
        return 0

    print(f"platform {platform_key()}\n\nengines")
    for name in tts.ENGINES:
        ready, detail = tts.engine_status(name, ROOT)
        print(f"  [{'ok' if ready else 'MISSING'}] {name} — {detail}")
    print(f"\nvoices ({provider})")
    voices, source = tts.list_voices(provider, ROOT)
    print(f"  {' '.join(voices)}")
    print(f"  ({source})")
    print('\ntry one: edith voice "Your first line." --voice af_heart --out hello.wav')
    return 0


def _with_voice(project: Project, args: argparse.Namespace) -> Project:
    """Let the command line try a voice without editing the spec."""
    if not (getattr(args, "voice", None) or getattr(args, "speed", None) or getattr(args, "provider", None)):
        return project
    voice = project.voice.model_copy(
        update={
            "provider": args.provider or project.voice.provider,
            "voice": args.voice or project.voice.voice,
            "speed": args.speed or project.voice.speed,
        }
    )
    return project.model_copy(update={"voice": voice})


def _prepare(args: argparse.Namespace) -> tuple[Project, Path, list[tts.Clip]]:
    spec = Path(args.spec)
    project = _with_voice(load_project(spec), args)
    base = spec.resolve().parent
    clips = tts.synthesize_project(project, base / "audio", ROOT, force=args.force)
    return project, base, clips


def _build(project: Project, base: Path, clips: list[tts.Clip]) -> buildmod.Render:
    return buildmod.build(project, clips, base, ROOT / "video", base / "build", root=ROOT)


def _slug(title: str) -> str:
    keep = [character.lower() if character.isalnum() else "-" for character in title]
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "video"


def _report(report: buildmod.Render, project: Project) -> None:
    minutes, seconds = divmod(int(round(report.seconds)), 60)
    print(f"props      {report.props}")
    if report.srt:
        print(f"subtitles  {report.srt}")
    print(
        f"timeline   {len(project.scenes)} scene(s), {minutes}:{seconds:02d} "
        f"({report.frames} frames at {project.style.canvas.fps} fps)"
    )
    print(f"captions   {report.cues} cue(s)")


def cmd_build(args: argparse.Namespace) -> int:
    try:
        project, base, clips = _prepare(args)
        report = _build(project, base, clips)
    except (SpecError, ValueError, tts.EngineMissing) as exc:
        print(exc, file=sys.stderr)
        return 1
    _report(report, project)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    try:
        project, base, clips = _prepare(args)
        report = _build(project, base, clips)
    except (SpecError, ValueError, tts.EngineMissing) as exc:
        print(exc, file=sys.stderr)
        return 1
    _report(report, project)

    node = shutil.which("node")
    if node is None:
        print("\nNode 20+ is needed to render. `edith doctor` shows the command for your OS.", file=sys.stderr)
        return 1
    cli = ROOT / "video" / REMOTION_CLI
    if not cli.exists():
        print("\nthe renderer packages are not installed yet. Run: cd video && npm install", file=sys.stderr)
        return 1

    fps = project.style.canvas.fps
    if args.still is not None:
        frame = max(0, round(args.still * fps))
        target = Path(args.out) if args.out else base / "build" / f"still-{frame:04d}.png"
        command = [
            node,
            str(cli),
            "still",
            ENTRY,
            COMPOSITION,
            str(target.resolve()),
            f"--frame={frame}",
            f"--props={report.props.resolve()}",
        ]
    else:
        target = Path(args.out) if args.out else base / "out" / f"{_slug(project.meta.title)}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [
            node,
            str(cli),
            "render",
            ENTRY,
            COMPOSITION,
            str(target.resolve()),
            f"--props={report.props.resolve()}",
            "--codec=h264",
        ]

    print(f"\n{'still' if args.still is not None else 'rendering'} → {target}")
    completed = subprocess.run(command, cwd=ROOT / "video")
    if completed.returncode != 0:
        print(f"the renderer exited with code {completed.returncode}", file=sys.stderr)
        return 1
    if not target.exists():
        print(f"the renderer finished but wrote nothing to {target}", file=sys.stderr)
        return 1
    print(f"wrote {target} ({target.stat().st_size / 1_000_000:.1f} MB)")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    try:
        return fetch.run(ROOT, assume_yes=args.yes)
    except fetch.FetchError as exc:
        print(exc, file=sys.stderr)
        return 1


def cmd_init(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if not args.answers:
        wizard.run(out, force=args.force)
        return 0

    source = Path(args.answers)
    try:
        answers = yaml.safe_load(source.read_text())
        spec = wizard.build_from_answers(answers, source.resolve().parent)
        path = wizard.save(spec, out, force=args.force)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"wrote {path} ({len(spec['scenes'])} scenes, {spec['target']['duration_sec']} s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edith", description="Spec-driven explainer video builder.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="check a project spec")
    validate.add_argument("spec", help="path to project.yaml")
    validate.set_defaults(func=cmd_validate)

    doctor = sub.add_parser("doctor", help="report external dependencies and how to get them")
    doctor.add_argument("--quiet", action="store_true", help="hide install hints")
    doctor.set_defaults(func=cmd_doctor)

    fetch_cmd = sub.add_parser("fetch", help="download the weight files the manifest pins")
    fetch_cmd.add_argument("--yes", action="store_true", help="do not ask first")
    fetch_cmd.set_defaults(func=cmd_fetch)

    init = sub.add_parser("init", help="ask the questions and write a project spec")
    init.add_argument("--out", default="project.yaml", help="where to write the spec")
    init.add_argument("--answers", help="read answers from a YAML file instead of asking")
    init.add_argument("--force", action="store_true", help="overwrite an existing spec")
    init.set_defaults(func=cmd_init)

    voice = sub.add_parser("voice", help="list engines and voices, or speak some text")
    voice.add_argument("text", nargs="?", help="a line or two to speak")
    voice.add_argument("--project", help="synthesize every paragraph of this spec")
    voice.add_argument("--out", help="wav file (text) or folder (project)")
    voice.add_argument("--voice", help="e.g. af_heart")
    voice.add_argument("--speed", type=float, help="e.g. 1.05")
    voice.add_argument("--provider", help="kokoro-onnx (portable) or kokoro-mlx (Apple silicon)")
    voice.add_argument("--force", action="store_true", help="re-render even unchanged paragraphs")
    voice.set_defaults(func=cmd_voice)

    def voice_flags(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("spec", help="path to project.yaml")
        parser.add_argument("--voice", help="e.g. af_heart, overriding the spec")
        parser.add_argument("--speed", type=float, help="e.g. 1.05, overriding the spec")
        parser.add_argument("--provider", help="kokoro-onnx or kokoro-mlx, overriding the spec")
        parser.add_argument("--force", action="store_true", help="re-render every paragraph")

    build_cmd = sub.add_parser("build", help="speak the script, then write the renderer's props")
    voice_flags(build_cmd)
    build_cmd.set_defaults(func=cmd_build)

    render = sub.add_parser("render", help="build, then render the video (or one still frame)")
    voice_flags(render)
    render.add_argument("--out", help="mp4 path, or png path with --still")
    render.add_argument("--still", type=float, metavar="SECONDS", help="render one frame instead")
    render.set_defaults(func=cmd_render)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
