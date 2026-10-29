# Edith Video Generator — set up on Windows

<!-- os-switch -->
macOS? See [setup-macos.md](setup-macos.md).
<!-- /os-switch -->

Everything here runs in **PowerShell** or **Command Prompt** (Start → type
`powershell`). The project needs no admin rights; only `winget` installs may ask.

## 1. Python 3.11 or newer

```bat
py -3 -V
```

If that prints 3.11 or higher, skip ahead. If Windows says the command is not
recognised, install Python from <https://www.python.org/downloads/windows/> and
**tick "Add python.exe to PATH"** in the first screen of the installer. Then
close and reopen the terminal.

Note: typing `python` on a fresh Windows install may open the Microsoft Store
instead of Python. `py -3` avoids that; the setup script tries both.

## 2. Get the code

Either way works; the second needs no git:

```bat
git clone <repository-url> edith-video-generator
cd edith-video-generator
```

or **Code → Download ZIP** on the repository page, right-click the `.zip` →
**Extract All**, then open PowerShell in that folder (Shift + right-click →
"Open PowerShell window here").

## 3. Run the setup

Double-click **`setup.bat`**. It checks Python, creates `.venv`, installs the
tool, and prints what external programs are still missing.

The same four steps by hand:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,tts-onnx]"
.venv\Scripts\python.exe -m edith doctor
.venv\Scripts\python.exe -m edith voice
```

`edith doctor` tells you what is missing and the exact command for Windows.
`edith voice` lists the speech engines and voices.

Use `.venv\Scripts\python.exe -m edith ...` rather than a bare `edith`, so the
command works in any terminal without activating anything.

## 4. Your own video

```bat
rem put your .md or .txt in sources\, then:
.venv\Scripts\python.exe -m edith init --out project.yaml
.venv\Scripts\python.exe -m edith validate project.yaml
.venv\Scripts\python.exe -m edith voice --project project.yaml --out audio\
```

The third command measures every paragraph and prints each scene's real speech
against its planned length, flagged `over`, `ok` or `under`.

Input is `.md` or `.txt` only, so a book needs one conversion first. Install
Calibre from calibre-ebook.com and run `ebook-convert book.pdf book.txt` (or
`book.epub`); if the command is not recognised, reopen the terminal or call
`"C:\Program Files\Calibre2\ebook-convert.exe"`. Take one chapter, not the whole
book — at about 180 words a minute a 90,000-word book is ten hours of audio. If
you want help drafting the script itself, [outline-prompt.md](outline-prompt.md)
has a prompt that produces the scene shape the wizard reads.

## 5. External programs, if doctor reports them missing

| what | Windows |
|---|---|
| ffmpeg | `winget install Gyan.FFmpeg`, then reopen the terminal |
| Kokoro weights | download the two files from the link `doctor` prints into `models\` |
| Rhubarb (presenter only) | unzip the Windows release into `tools\rhubarb\` — it must end up as `tools\rhubarb\rhubarb.exe` |
| fonts | any `.ttf`/`.otf` you have the right to use, into `fonts\` |

## 6. When something goes wrong

| message | fix |
|---|---|
| `Python 3 was not found` | install from python.org with "Add python.exe to PATH" ticked, then run `setup.bat` again |
| `This needs Python 3.11 or newer` | same — install a newer version, not the 3.9 from the Store |
| `No module named edith` | the commands were not run in this folder — repeat step 3 |
| `'ffmpeg' is not recognized` | `winget install Gyan.FFmpeg`, then close and reopen the terminal |
| `Windows protected your PC` (on rhubarb.exe) | **More info** → **Run anyway**; it is a release download you placed there yourself |
| `the kokoro-onnx weights are missing` | download both files `doctor` names into `models\` |
| install fails on a long path | move the folder to something short such as `C:\edith-video-generator` |
