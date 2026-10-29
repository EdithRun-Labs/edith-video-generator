#!/bin/bash
# Double-click this file in Finder, or run ./setup.command in a terminal.
# It checks Python, creates .venv, installs the tool and reports what is missing.
# No admin rights, no account, no API key.

set -uo pipefail

cd "$(dirname "$0")" || exit 1

step() { printf '\n== %s\n' "$1"; }
fail() {
  printf '\n!! %s\n' "$1"
  printf '\nPress return to close.\n'
  read -r _
  exit 1
}

step "edith-video-generator setup"

if ! command -v python3 >/dev/null 2>&1; then
  fail "Python 3 was not found. Install Python 3.11 or newer from https://www.python.org/downloads/ (or: brew install python@3.12), then run this file again."
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  fail "This needs Python 3.11 or newer, but python3 here is $(python3 -V 2>&1). Install a newer one from https://www.python.org/downloads/ and run this file again."
fi

step "Using $(python3 -V 2>&1)"

if [ ! -x .venv/bin/python ]; then
  step "Creating .venv"
  python3 -m venv .venv || fail "Could not create the virtual environment."
fi

# A .venv made by `uv venv` has no pip; add it rather than starting over.
if ! ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
  step "Adding pip to .venv"
  ./.venv/bin/python -m ensurepip --upgrade --default-pip >/dev/null 2>&1 ||
    fail "This .venv has no pip and ensurepip could not add it. Delete .venv and run this file again."
fi

step "Installing the tool and its Python packages (a minute or two)"
./.venv/bin/python -m pip install --upgrade pip --quiet
./.venv/bin/python -m pip install --quiet -e ".[dev,tts-onnx]" ||
  fail "The install failed. The message above says why: usually no network, or not enough disk space."

if ! command -v node >/dev/null 2>&1; then
  step "Node is not installed, and the renderer needs it"
  if command -v brew >/dev/null 2>&1; then
    printf 'Install Node 20+ with Homebrew now? [y/N] '
    read -r answer
    case "$answer" in
      y | Y | yes | YES)
        brew install node ||
          printf '\n!! brew install node failed. Install Node from https://nodejs.org/\n'
        ;;
      *) printf '\nSkipped. Later: install Node, then run: cd video && npm install\n' ;;
    esac
  else
    printf 'Install Node 20+ from https://nodejs.org/, then run: cd video && npm install\n'
  fi
fi

if command -v npm >/dev/null 2>&1; then
  step "Installing the renderer packages (one time, about 100 MB)"
  ( cd video && npm install --no-audit --no-fund --silent ) ||
    printf '\n!! npm install failed. The speech commands still work; retry with: cd video && npm install\n'
else
  printf '\n== The renderer packages are not installed (npm not found yet).\n'
  printf '   Reopen Terminal and run: cd video && npm install\n'
fi

step "The speech weights (one time, about 340 MB)"
./.venv/bin/python -m edith fetch ||
  printf '\n!! The weights were not downloaded. Later: ./.venv/bin/python -m edith fetch\n'

step "Checking external tools"
./.venv/bin/python -m edith doctor || true

cat <<'EOF'

Next steps, one line at a time:

  ./.venv/bin/python -m edith init --out project.yaml
  ./.venv/bin/python -m edith build project.yaml
  ./.venv/bin/python -m edith render project.yaml

Put your text in sources/. Everything else is written by the wizard.
EOF

printf '\nPress return to close.\n'
read -r _
