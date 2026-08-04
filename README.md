# The Estate Builder · v0

One command stamps a complete writing estate onto a person's computer: a voice law, a verbatim dictation well, writing lanes, quality gates, a one-command seal to GitHub, and a render path. It is the architecture behind THE STEERSMAN and the One Water body of work, separated from its first author so anyone can run it.

## What person A does, start to finish

```
git clone https://github.com/hpad66-pixel/estate-builder
bash estate-builder/scripts/new_estate.sh
```

Four questions (name, folder, book title, GitHub username), then the stamp. The estate lands in `~/dev/<their-slug>`, already a git repository with its first commit made.

Then, inside the new estate, in any AI tool (Claude, Cowork, Codex):

1. Choose how the estate learns their voice. They can paste `INTERVIEW.md` into the session and answer twelve questions, or import an existing `SOUL.md` during setup and skip the interview. The imported file is preserved exactly as provided.
2. Start speaking. Every dictation lands verbatim and dated in `outputs/book-evidence/book-one/raw-dictations.md` before any shaping. That file is evidence and is never edited.
3. On publish day: `gh repo create <slug> --private --source ~/dev/<slug> --push`
4. From then on, one command ships everything: `bash scripts/seal_all.sh "what changed"`

## What the stamp lays down

```
<their-slug>/
  SOUL.md                the voice law, filled by the interview
  CLAUDE.md              how the estate runs: stations, hats, rules
  AGENTS.md              the same rules, compressed for any tool
  book/
    chapters/            the writing lane (.md, first person, their voice)
    figures/             the drawing lane
    ART.md               the sketchbook art system
  outputs/
    book-evidence/       the well: verbatim, dated, append-only
    book-compiled/       the compiled book (.html, .pdf)
  docs/                  maps and concept pages
  scripts/
    seal_all.sh          the seal: commit + push everything listed in repos.txt
    qc_check.py          the voice gate: banned characters and banned words
```

## Requirements

A Mac or Linux machine, git, python3. A GitHub account and the `gh` CLI only when they are ready to publish; the estate works fully offline until then.

## The rules the estate enforces

Dictation is captured verbatim before any shaping, so provenance is never in doubt. Everything is authored in the estate; every other place receives copies. Gates check the voice and the facts before anything ships. The seal is the only door to GitHub, and it swings one way, under the owner's hand.

Reference build: the One Water estate, estate number one, already running.

## The one-line install (v1)

Once `install.sh` is served at `https://owos.ai/install.sh`, a person needs no git knowledge to start:

```
bash -c "$(curl -fsSL https://owos.ai/install.sh)"
```

It fetches this engine, refreshes it if they already have it, and runs the stamp. The four questions still run on their keyboard even though the installer arrived through a pipe. Hosting the file at owos.ai is a one-time deploy step on the One Water OS platform (Cloudflare).

## Owner-controlled updates

SoulOS Studio shows the current release and prepares the owner's private update command. A check reports whether an update is available without changing the estate. An update downloads the authenticated engine, verifies its SHA-256 checksum, shows a dry run, asks for approval, backs up every replaced engine-owned file, and records the installed version.

The updater never touches `SOUL.md`, the owner's brand, logo, chapters, figures, dated article folders, verbatim well, or repository list. Updates are available automatically, but they are never silently installed.
