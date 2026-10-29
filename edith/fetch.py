"""The only downloads this tool performs: files the manifest pins by size.

Nothing here is vendored or bundled. A file is fetched only when it is missing,
only after you agree, and the byte count is checked afterwards so a truncated
download is an error rather than a mysterious failure later.
"""

from __future__ import annotations

import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

from .deps import Manifest, load_manifest

CHUNK = 1 << 20
YES = {"", "y", "yes"}


class FetchError(RuntimeError):
    """A download that failed or arrived incomplete."""


@dataclass(frozen=True)
class Item:
    dependency: str
    path: str
    url: str
    size: int


def human(size: int) -> str:
    if size >= 1_000_000_000:
        return f"{size / 1_000_000_000:.1f} GB"
    if size >= 1_000_000:
        return f"{size / 1_000_000:.0f} MB"
    return f"{size / 1000:.0f} KB"


def planned(manifest: Manifest, root: Path) -> list[Item]:
    """Declared files that are not on disk yet."""
    items: list[Item] = []
    for dependency in manifest.dependencies:
        for file in dependency.files:
            if not (root / file.path).exists():
                items.append(Item(dependency.id, file.path, file.url, file.size))
    return items


def download(item: Item, root: Path, stream: TextIO = sys.stdout) -> Path:
    target = root / item.path
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    done = 0
    try:
        with urllib.request.urlopen(item.url, timeout=60) as response, partial.open("wb") as handle:
            total = int(response.headers.get("Content-Length") or item.size)
            while chunk := response.read(CHUNK):
                handle.write(chunk)
                done += len(chunk)
                percent = min(100, done * 100 // total) if total else 0
                stream.write(f"\r  {Path(item.path).name}  {percent}%  ({human(done)})")
                stream.flush()
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise FetchError(f"could not download {item.url}\n  {exc}") from exc
    stream.write("\n")

    if done != item.size:
        partial.unlink(missing_ok=True)
        raise FetchError(
            f"{item.path} arrived as {done} bytes but the manifest pins {item.size}; "
            "the download was truncated or the release changed. Nothing was kept."
        )
    partial.replace(target)
    return target


def run(
    root: Path,
    assume_yes: bool = False,
    ask: Callable[[str], str] = input,
    stream: TextIO = sys.stdout,
    manifest: Manifest | None = None,
) -> int:
    manifest = manifest or load_manifest()
    items = planned(manifest, root)
    if not items:
        stream.write("every declared file is already here\n")
        return 0

    total = sum(item.size for item in items)
    stream.write("the tool can fetch these for you:\n")
    for item in items:
        stream.write(f"  {item.path}  {human(item.size)}  (for {item.dependency})\n")
    stream.write(f"total {human(total)}\n")

    if not assume_yes:
        answer = ask(f"download {len(items)} file(s) into {root.name or '.'}? [Y/n] ")
        if answer.strip().lower() not in YES:
            stream.write("nothing downloaded\n")
            return 1

    for item in items:
        download(item, root, stream)
        stream.write(f"  kept {item.path}\n")
    stream.write("\nrun `edith doctor` to confirm everything is in place\n")
    return 0
