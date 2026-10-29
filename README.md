# Edith Video Generator

Turn a source document into a narrated explainer video. One YAML file describes
the video — subject, source, length, palette, fonts, voice — and the tool builds
it. Nothing about style or subject is baked in.

**Status: step 5 of 8.** Spec, wizard, speech, lip sync, timing and a working
renderer. A 61-second demo renders to 1080p with captions and burned-in audio.
Still missing: the presenter, contrast checks and CI.

## You do not need an AI assistant

No Claude, ChatGPT or other hosted model is called, and no API key is asked for
anywhere. The wizard, the speech engines and the dependency checks are ordinary
local code; the only time you touch the network is fetching a declared
dependency yourself (the Kokoro weights, Rhubarb). If a tutorial tells you to
install an AI CLI first, that is a different kind of tool.

## What this is not

- Not a house style. The default is whatever your spec says.
- Not a content generator. It reads a file you own; it ships no text of its own.
- Not a wrapper around a paid service. Everything runs locally.
- Not a copy of the course video it grew out of. Same logic, no fixed look.

## Start here

**macOS** — double-click **`setup.command`**, or follow
[docs/setup-macos.md](docs/setup-macos.md).

**Windows** — double-click **`setup.bat`**, or follow
[docs/setup-windows.md](docs/setup-windows.md).

Each script checks Python, creates `.venv`, installs the tool and prints what is
still missing. Python 3.11+ is the only prerequisite — macOS:
`brew install python@3.12`; Windows: the installer from python.org with **"Add
python.exe to PATH"** ticked. No account, no API key, no admin rights.

The same four steps by hand, macOS shown (Windows uses
`.venv\Scripts\python.exe` instead of `./.venv/bin/python`):

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev,tts-onnx]"
./.venv/bin/python -m edith doctor        # what is missing, and the command for your OS
./.venv/bin/python -m edith voice         # which engines work, which voices exist
```

## Where your inputs go

Three plain files, nothing hidden:

- **Your source text** — a `.md` or `.txt` file under `sources/`, which git
  ignores. The wizard reads it and splits it into scenes; it never rewrites it.
- **Your answers** — `project.yaml`, written by the wizard and editable
  afterwards in any text editor. That file is the whole description of the video.
- **Generated files** — audio under `audio/`, renders later, all git-ignored.

The questions are asked in the terminal (`edith init`). A browser form served
from localhost is planned but not built; a double-clickable installer is not
planned, because every route still needs Python, and unsigned macOS and Windows
binaries are blocked by Gatekeeper and SmartScreen.

## If your input is a book

The tool reads plain text, so a PDF, EPUB or DOCX has to become `.md` or `.txt`
first. That conversion is mechanical — no AI involved:

| you have | command |
|---|---|
| a PDF with selectable text | `pdftotext -layout book.pdf book.txt` (Poppler: `brew install poppler` on macOS) |
| EPUB, MOBI, DOCX | `ebook-convert book.epub book.txt` (Calibre, macOS and Windows) |
| DOCX, or anything Pandoc reads | `pandoc book.docx -t plain -o book.txt` |
| a scanned PDF | needs OCR first — with no text layer neither command returns anything usable |

Calibre keeps `ebook-convert` inside its own install folder; if the terminal
cannot find it, reopen the terminal or call the full path. None of these three
are in `deps.yaml`, because the pipeline never calls them.

**A book is not a script.** Speech runs at about 180 words a minute, so ten
minutes is roughly 1,850 words, and a 90,000-word book would be ten hours of
audio. Nothing blocks that input: `validate` warns that the scenes add up to far
more than `target.duration_sec`, and the render is simply hours long. Take one
chapter, then cut it to length.

Two ways from the chapter to a script:

- **By hand** — Markdown with one `## ` heading per scene and one blank line
  between paragraphs. Everything written is spoken.
- **With an assistant** — [docs/outline-prompt.md](docs/outline-prompt.md) is a
  copy-paste prompt that asks for exactly that shape and that word budget. The
  tool itself still calls no AI and asks for no account.

## Make a video

```bash
./.venv/bin/python -m edith init --out project.yaml     # questions → spec
./.venv/bin/python -m edith build project.yaml          # speech, timing, captions
./.venv/bin/python -m edith render project.yaml         # mp4
./.venv/bin/python -m edith render project.yaml --still 12   # one frame, seconds in
```

`build` writes `build/props.json` (frame timings measured from the real audio)
and `build/captions.srt`, and copies the wavs where the renderer can reach them.
`render` runs it first, so one command is enough. The first render also fetches
Remotion's headless Chrome, about 90 MB, once.

Layouts, colours, fonts, canvas size and caption position all come from
`project.yaml` — the renderer has no look of its own.

## Speech

Two engines behind one interface, so the rest of the pipeline does not care:

| provider | runs on | installed by |
|---|---|---|
| `kokoro-onnx` | Windows, macOS, Linux (CPU) | `.[tts-onnx]` plus two weight files |
| `kokoro-mlx` | Apple silicon | `.[tts-mlx]`, weights download on first use |

Each paragraph becomes its own wav under `audio/`, which is what keeps the
runtime budget and caption timing honest. Re-running reuses any paragraph whose
text, voice and speed are unchanged (`audio/clips.yaml` holds the keys);
`--force` re-renders everything.

## Nothing external is vendored

`deps.yaml` declares ffmpeg, Node, Rhubarb, the Kokoro weights and fonts with a
version, a homepage and a per-platform hint. `edith doctor` reports what is
present and prints the instruction for your OS. The repository contains only our
own code — no binaries, no models, no fonts, no source text.

## Layout

```
edith/spec.py      the project spec: schema, validation, warnings
edith/deps.py      the dependency manifest: load, resolve platform, probe
edith/wizard.py    questions in, a first-pass spec out
edith/tts.py       speech engines, chunking, per-paragraph wav cache
edith/build.py     frame timings, caption cues, props.json, SRT
edith/rhubarb.py   lip-sync cues from a finished wav
edith/fetch.py     guided download of the weight files deps.yaml pins
edith/cli.py       validate / doctor / init / voice / build / render
video/              the Remotion renderer: title, scenes, captions, diagrams
setup.command       macOS double-click: check Python, make .venv, install, doctor
setup.bat           Windows double-click: the same
docs/setup-*.md     those steps written out, one page per OS
docs/outline-prompt.md  a prompt that turns a chapter into a script
deps.yaml           external dependencies (fetched by you, never committed)
examples/demo/      a small self-contained project (original text)
sources/            your own source text — ignored by git
tests/              spec, wizard, speech, build and fetch tests
LICENSE             MIT
```

## Verified, and not yet

- Speech through `kokoro-mlx`, lip sync through Rhubarb 1.14, and a full render
  (1920×1080 h264 with AAC audio, 64 s) run end to end on macOS.
- The `kokoro-onnx` path also runs end to end on CPU, using the weights
  `edith fetch` downloads. Nothing has been executed on Windows yet — the `.bat`
  and the Windows page are written but unrun.
- Layouts and all seven diagram types render; the presenter and any contrast
  checking do not exist.

## Licence

MIT — see [LICENSE](LICENSE). The external tools keep their own licences: the
Kokoro model is Apache-2.0, Rhubarb is MIT, ffmpeg depends on how it was built,
and Remotion is free for individuals and organisations of up to three staff —
four or more needs its company licence.

## Open decisions

- Whether to publish a Windows CI job before the renderer exists.
