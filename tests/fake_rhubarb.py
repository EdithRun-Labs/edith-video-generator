"""A stand-in Rhubarb binary for tests: writes one canned payload, counts calls."""

from pathlib import Path

PAYLOAD = (
    '{"mouthCues":[{"start":0,"end":0.2,"value":"A"},'
    '{"start":0.2,"end":0.5,"value":"D"}]}'
)


def install(root: Path) -> Path:
    binary = root / "tools" / "rhubarb" / "rhubarb"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text(
        "#!/bin/sh\n"
        'echo run >> "$(dirname "$0")/calls.txt"\n'
        'out=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  if [ "$1" = "--output" ]; then out="$2"; fi\n'
        "  shift\n"
        "done\n"
        f"cat > \"$out\" <<'JSON'\n{PAYLOAD}\nJSON\n"
    )
    binary.chmod(0o755)
    return binary


def calls(root: Path) -> int:
    log = root / "tools" / "rhubarb" / "calls.txt"
    return len(log.read_text().splitlines()) if log.exists() else 0
