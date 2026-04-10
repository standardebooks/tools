# CLAUDE.md — tolstoy.life ebook toolset

## Parent project

This repository is a child project of the Tolstoy Research Project at `/Volumes/Graugear/Tolstoy/`. The parent `CLAUDE.md` at that path defines the shared mission, vocabulary, data flow, and content standards that apply across all projects. Read it for context before making changes that affect ebook content, metadata, or copy.

```
/Volumes/Graugear/Tolstoy/          ← parent project
├── CLAUDE.md                       ← shared context (read this first)
├── website/                        ← front-end PWA and e-reader (tolstoy.life)
├── corpus/                         ← archived data pipeline (LightRAG, retired)
├── tools/ (this repo)              ← ebook build toolset (github.com/tolstoylife/tools)
```

This toolset sits alongside `website/` and `corpus/` as a specialist component — it is the build system that turns source text into finished `.epub` files for distribution on tolstoy.life.

---

## What this tool is

This is a fork of the [Standard Ebooks toolset](https://github.com/standardebooks/tools), adapted for the tolstoy.life project. It is a Python command-line toolkit (invoked via the `se` command) that handles the full lifecycle of producing a production-quality EPUB ebook from a marked-up source directory.

It is **not** a general-purpose ebook converter. It is an opinionated editorial pipeline that enforces consistent typography, accessibility, metadata, and structural standards across every ebook produced under the tolstoy.life imprint.

### What it produces

Finished `.epub` files suitable for:
- Distribution via tolstoy.life
- Sideloading onto e-readers (Kindle, Kobo, Apple Books, etc.)
- In-browser reading via the tolstoy.life PWA e-reader

### The source directory format

Every ebook lives in a source directory with a fixed structure:

```
my-ebook/
├── images/
│   ├── cover.jpg         ← cover artwork
│   ├── cover.svg         ← cover SVG (generated)
│   └── titlepage.svg     ← titlepage SVG (generated)
└── src/
    └── epub/
        ├── content.opf   ← EPUB metadata (publisher, title, author, etc.)
        ├── css/
        ├── images/
        └── text/
            ├── colophon.xhtml
            ├── imprint.xhtml
            ├── uncopyright.xhtml
            └── *.xhtml   ← chapter files
```

This structure is created by `se create-draft` and then populated with the source text.

---

## Key commands

| Command | What it does |
|---|---|
| `se create-draft` | Scaffold a new ebook source directory from templates |
| `se build` | Compile a source directory into a distributable `.epub` |
| `se build-images` | Generate cover and titlepage SVGs from templates |
| `se lint` | Check the source directory for style and structural errors |
| `se typogrify` | Apply typography rules (smart quotes, em-dashes, etc.) |
| `se semanticate` | Auto-add EPUB semantic markup to XHTML files |
| `se build-toc` | Generate the table of contents |
| `se build-manifest` | Generate the OPF manifest |
| `se recompose-epub` | Collapse an EPUB into a single HTML file (for the PWA reader) |
| `se prepare-release` | Final pre-release checks and metadata updates |

Run `se help` for the full list, or `se <command> --help` for per-command options.

---

## Relationship to the parent Tolstoy project

### Where metadata comes from

Ebook metadata (title, author, dates, genre, source transcription) originates in the **corpus project** and flows through `website/` via the sync pipeline. See the parent `CLAUDE.md` for the authoritative data-flow diagram.

When producing an ebook, the `content.opf` metadata should be populated from the canonical YAML in `corpus/` — do not invent or hand-estimate metadata values. Cross-reference against the works schema (`tolstoy-works-schema.yaml` at the parent level).

### Cover artwork

Cover images should be sourced from public domain artworks. Preferred sources are paintings and portraits already catalogued in the corpus project. See `_resources/` in the parent folder for existing image assets.

### Ebook URL slugs

The `SE_SLUG` placeholder in the colophon and OPF templates must match the `id` field from the canonical works schema (e.g., `anna-karenina`, `war-and-peace`). These slugs are the primary keys shared across all three projects.

---

## Branding and copy

This fork replaces Standard Ebooks branding with tolstoy.life throughout. Key things to know:

- **Publisher name:** `tolstoy.life` (lowercase, with dot)
- **Publisher URL:** `https://tolstoy.life/`
- **Logo:** `se/data/templates/logo.svg` — a simple text wordmark (placeholder; update when final brand assets are ready)
- **SE vocabulary namespace** (`se: https://standardebooks.org/vocab/1.0`) is retained intentionally — it is a technical EPUB standard, not visible branding
- **Copy review files** for imprint, colophon, and uncopyright pages live in `copy-review/` — these need final copy from the Tolstoy project before the first ebook release

---

## Upstream sync

This repository tracks upstream changes from `standardebooks/tools`. When pulling upstream updates:

1. Review any changes to files in `se/data/templates/` — these are the primary rebranded files and upstream changes may overwrite tolstoy.life copy
2. The files most likely to conflict are: `colophon.xhtml`, `imprint.xhtml`, `uncopyright.xhtml`, `logo.svg`, `cover.svg`, `titlepage.svg`, `content.opf`, `setup.py`
3. Lint rules and Python logic in `se_epub_lint.py` and `se_epub_build.py` can generally be taken from upstream without conflict

---

## Installation

Requires Python >= 3.10.12.

```shell
# Install with pipx (recommended)
pipx install .

# Or for development
python3 -m venv venv
source venv/bin/activate
pip install -e . --break-system-packages
```
