# Edith Video Generator — set up on macOS

<!-- os-switch -->
Windows? See [setup-windows.md](setup-windows.md).
<!-- /os-switch -->

Everything here runs in **Terminal** (Applications → Utilities → Terminal). The
project needs no admin password; only Homebrew installs do.

## 1. Python 3.11 or newer

```bash
python3 -V
```

If that prints 3.11 or higher, skip ahead. If it prints 3.9 or older — the
Command Line Tools version, usually — install a newer one:

```bash
brew install python@3.12          # or download it from https://www.python.org/downloads/
```

## 2. Get the code

Either way works; the second needs no git:

```bash
git clone <repository-url> edith-video-generator && cd edith-video-generator
```

or **Code → Download ZIP** on the repository page, unzip it, and open Terminal
in that folder (`cd` then drag the folder in).

## 3. Run the setup

Double-click **`setup.command`**. It checks Python, creates `.venv`, installs
the tool, and prints what external programs are still missing. If macOS says it
cannot open the file, right-click it → **Open** → **Open**.

The same four steps by hand:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev,tts-onnx]"
./.venv/bin/python -m edith doctor
./.venv/bin/python -m edith voice
```

`edith doctor` tells you what is missing and the exact command for macOS.
`edith voice` lists the speech engines and voices.

Apple silicon alternative: `pip install -e ".[dev,tts-mlx]"` uses Apple's MLX
framework and is noticeably faster. Both produce the same wav files.

## 4. Your own video

```bash
# put your .md or .txt in sources/, then:
./.venv/bin/python -m edith init --out project.yaml
./.venv/bin/python -m edith validate project.yaml
./.venv/bin/python -m edith voice --project project.yaml --out audio/
```

The third command measures every paragraph and prints each scene's real speech
against its planned length, flagged `over`, `ok` or `under`.

Input is `.md` or `.txt` only, so a book needs one conversion first: for a PDF
with selectable text, `brew install poppler` then
`pdftotext -layout book.pdf book.txt`; for EPUB, MOBI and DOCX, Calibre's
`ebook-convert book.epub book.txt`. Take one chapter, not the whole book — at
about 180 words a minute a 90,000-word book is ten hours of audio. If you want
help drafting the script itself, [outline-prompt.md](outline-prompt.md) has a
prompt that produces the scene shape the wizard reads.

## 5. External programs, if doctor reports them missing

| what | macOS |
|---|---|
| ffmpeg | `brew install ffmpeg` |
| Kokoro weights | download the two files from the link `doctor` prints into `models/` |
| Rhubarb (presenter only) | unzip the macOS release into `tools/rhubarb/`, then `xattr -d com.apple.quarantine tools/rhubarb/rhubarb` |
| fonts | any `.ttf`/`.otf` you have the right to use, into `fonts/` |

## 6. When something goes wrong

| message | fix |
|---|---|
| `This needs Python 3.11 or newer` | install Python from python.org, then run `setup.command` again |
| `No module named edith` | the four commands were not run in this folder — repeat step 3 |
| `ffmpeg not found` | `brew install ffmpeg`, then reopen Terminal |
| `"rhubarb" cannot be opened because the developer cannot be verified` | right-click → Open, or run the `xattr` line above |
| `the kokoro-onnx weights are missing` | download both files `doctor` names into `models/` |
| `ssl certificate` / network errors during install | behind a proxy? set `HTTPS_PROXY`, or use a different network |
