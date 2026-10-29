# Turning a book into a scene script

Edith speaks your text verbatim, so what it needs is a script, not a book. This
page gives you a prompt to paste into any assistant you already use — or a
checklist to follow by hand. The tool itself calls no AI and asks for no account.

## What the wizard expects

| rule | why |
|---|---|
| a `.md` file under `sources/` | `.txt` works too, but then scene breaks are guessed by word count |
| `## Heading` starts a scene | level 2 only; a `# Title` line at the top is ignored |
| one blank line between paragraphs | paragraphs are the unit of speech and caption timing |
| every paragraph is read aloud | no stage directions, nothing that only makes sense on a page |
| text before the first `## ` becomes an "Introduction" scene | put the opening there, or start straight with a heading |

Length is the part people get wrong. Speech runs at roughly **180 words a
minute**, so:

| video length | words of script |
|---|---|
| 5 minutes | ~900 |
| 10 minutes | ~1,850 |
| 15 minutes | ~2,800 |
| 20 minutes | ~3,700 |

## The prompt

Replace the four bracketed lines, paste the whole block into the assistant, and
paste the chapter with it. It works with any model, and it works as a writing
brief if you are doing this yourself.

```text
You are helping me turn part of a book into the narration for a short
explainer video. The narration will be read aloud by a text-to-speech voice.

TOPIC:           [one line]
SOURCE:          [the chapter text, pasted below]
TARGET LENGTH:   [N] minutes of speech
AUDIENCE:        [who is watching and what they already know]

OUTPUT — a single Markdown document, nothing before or after it:

- The first line may be `# [title]`. It is never spoken.
- Each scene starts with a line `## [scene title]` at heading level two.
  Use between 5 and 12 scenes, each about 60 to 120 seconds when spoken.
- Under each heading write 2 to 5 paragraphs, separated by exactly one
  blank line.
- Total length must be [N] x 180 words, within ten percent.
- Plain prose only. No bullet lists, numbered lists, tables, bold, italics,
  links, footnotes, block quotes, code, horizontal rules, HTML or comments.
- Write for the ear: short sentences, one idea each. Write numbers and
  symbols the way they are said ("about eighteen hundred", "nineteen
  ninety-eight", "per cent"), not as digits or notation.
- Do not invent facts, figures, names, quotes or examples that are not in
  the source. If a passage is dense, restate it more simply without adding
  anything it does not say. If it is ambiguous, say what it actually says.
- Do not open by describing the video ("in this video we will...") and do
  not close with a summary of what was just said, unless the source does.

Keep a running word count as you write. If you are over the budget, cut
examples before you cut the argument.
```

## What to check when it comes back

- **Word count.** `wc -w sources/chapter.md` on macOS, `(Get-Content
  sources\chapter.md | Measure-Object -Word).Words` in PowerShell. More than
  ten percent over means a longer video than you asked for.
- **Shape.** `grep '^## ' sources/chapter.md` should show 5–12 scene headings.
  Any `-` at the start of a line, any `**`, any `[1]` will be read aloud.
- **Numbers.** Skim for digits that should be words. The voice reads "1998" as a
  number, not as a year, in some contexts.
- **Claims.** Compare against the book. An assistant that adds a statistic has
  added it to your video.

Then save it under `sources/` and point the wizard at it:

```bash
./.venv/bin/python -m edith init --out project.yaml
./.venv/bin/python -m edith validate project.yaml
./.venv/bin/python -m edith voice --project project.yaml --out audio/
```

`validate` checks the plan; `voice --project` speaks it and prints each scene's
real length next to the planned one, so you can see where another cut is needed
before you render. Nothing here needs an account, a key or a network connection.
