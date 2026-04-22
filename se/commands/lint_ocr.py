"""
This module implements the `tl lint-ocr` command.

Finds and optionally auto-fixes common OCR artifacts in per-page XHTML files:
  ol-001  Missing apostrophes in possessives / contractions  (auto-fix)
  ol-002  Hyphenated line-break words                        (auto-fix)
  ol-003  Common misread characters                          (auto-fix)
  ol-004  Inline footnote markers embedded in text           (manual)
  ol-005  Footnote markers misread as ? or !                 (manual)
  ol-006  Illustration/caption garbage pages                 (manual)
  ol-007  Running-header bleed-through                       (manual)
  ol-008  Suspicious paragraph breaks                        (manual)

Rules are layered:
  1. Built-in rules (always active).
  2. Book-specific YAML at .tl-lint-ocr.yaml in the project root (optional).

Output is in VS Code–clickable format:  file:line: [ol-NNN] message
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

try:
	import yaml  # type: ignore
	_YAML_AVAILABLE = True
except ImportError:
	_YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Issue(NamedTuple):
	path: Path
	line: int
	code: str
	message: str
	auto_fixable: bool


# ---------------------------------------------------------------------------
# Built-in misread map  (common Tesseract errors for 19th-c. English printing)
# ---------------------------------------------------------------------------

_BUILTIN_MISREADS: list[tuple[str, str]] = [
	# OCR glyph confusion
	(r"\bTue\b",                    "The"),       # capital T+ue → The
	(r"\b([A-Z])1\b",               r"\g<1>I"),   # digit 1 as capital I after a letter
	(r"\b1t\b",                     "It"),
	(r"\b1n\b",                     "In"),
	(r"\b1s\b",                     "Is"),
	(r"\bl\b(?=[A-Z])",             "I"),          # lone lowercase l before capital
	(r"'1'sarevitch",               "Tsarevitch"),
	(r"\bTsarevitch\b",             "Tsarevitch"), # already correct — no-op placeholder
	(r"\brn\b",                     "m"),          # rn ligature
	(r"\bvv\b",                     "w"),
	(r"\bcl\b",                     "d"),
	(r"\bli\b",                     "h"),          # context-dependent; flagged only
	(r"fi(?=[a-z])",                "fi"),         # fi ligature already fine — normalise
	(r"fl(?=[a-z])",                "fl"),
	# Common word-level OCR errors in this era of printing
	(r"\biiis\b",                   "his"),
	(r"\btlie\b",                   "the"),
	(r"\btliat\b",                  "that"),
	(r"\bliim\b",                   "him"),
	(r"\bliis\b",                   "his"),
	(r"\bAvliat\b",                 "What"),
	(r"\bavlien\b",                 "when"),
	(r"\bAvhen\b",                  "When"),
	(r"\bvvith\b",                  "with"),
	(r"\bvvliich\b",                "which"),
]

# Possessive / contraction patterns (ol-001)
_POSSESSIVE_PATTERNS: list[tuple[re.Pattern, str]] = [
	# Tolstoys  →  Tolstoy's   (any word ending in a letter, followed by s)
	(re.compile(r"\b([A-Za-z]+) s\b"), r"\1's"),
]

# Line-break hyphenation (ol-002): word- at end of line, continuation on next
_LINEBREAK_HYPHEN = re.compile(r"(\w+)-\s*\n\s*([a-z]\w*)")


# ---------------------------------------------------------------------------
# YAML config loader
# ---------------------------------------------------------------------------

def _load_config(project_dir: Path) -> dict:
	"""Load .tl-lint-ocr.yaml from project root if it exists."""
	cfg_path = project_dir / ".tl-lint-ocr.yaml"
	if not cfg_path.exists():
		return {}
	if not _YAML_AVAILABLE:
		print("Warning: PyYAML not installed — book-specific config ignored.", file=sys.stderr)
		print("  pip install pyyaml --break-system-packages", file=sys.stderr)
		return {}
	with open(cfg_path, encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


def _build_running_header_pattern(config: dict) -> re.Pattern | None:
	"""Build a regex from the running_headers list in config."""
	headers = config.get("running_headers", [])
	if not headers:
		return None
	escaped = [re.escape(h) for h in headers]
	return re.compile(r"(?:" + "|".join(escaped) + r")", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Linting logic
# ---------------------------------------------------------------------------

def _lint_file(
	path: Path,
	running_header_re: re.Pattern | None,
	extra_misreads: list[tuple[str, str]],
	config: dict,
) -> list[Issue]:
	issues: list[Issue] = []

	try:
		text = path.read_text(encoding="utf-8")
	except Exception as e:
		return [Issue(path, 0, "ol-000", f"Could not read file: {e}", False)]

	lines = text.splitlines()

	for lineno, line in enumerate(lines, 1):
		# Skip XHTML boilerplate lines
		if line.strip().startswith("<") and not line.strip().startswith("<p"):
			continue

		# ol-001: Missing apostrophe in possessives / contractions
		for pattern, replacement in _POSSESSIVE_PATTERNS:
			for m in pattern.finditer(line):
				# Only flag if the space is NOT inside a tag
				if "<" not in m.group(0):
					issues.append(Issue(
						path, lineno, "ol-001",
						f"Possible missing apostrophe: {m.group(0)!r} → {pattern.sub(replacement, m.group(0))!r}",
						True,
					))

		# ol-002: Hyphenated line-break (across lines — check join of line+next)
		if lineno < len(lines):
			joined = line.rstrip() + "\n" + lines[lineno].lstrip()
			if _LINEBREAK_HYPHEN.search(joined):
				m = _LINEBREAK_HYPHEN.search(joined)
				if m:
					issues.append(Issue(
						path, lineno, "ol-002",
						f"Hyphenated line-break: {m.group(0)!r} → {m.group(1) + m.group(2)!r}",
						True,
					))

		# ol-003: Built-in misread map
		all_misreads = _BUILTIN_MISREADS + extra_misreads
		for pattern_str, replacement in all_misreads:
			try:
				pat = re.compile(pattern_str)
			except re.error:
				continue
			for m in pat.finditer(line):
				corrected = pat.sub(replacement, m.group(0))
				if corrected != m.group(0):
					issues.append(Issue(
						path, lineno, "ol-003",
						f"Likely misread: {m.group(0)!r} → {corrected!r}",
						True,
					))

		# ol-004: Inline footnote markers (digit(s) or * immediately after a word, mid-sentence)
		footnote_marker = re.compile(r"\w(\d{1,3}|\*)\s+[A-Z]")
		for m in footnote_marker.finditer(line):
			issues.append(Issue(
				path, lineno, "ol-004",
				f"Possible inline footnote marker: {m.group(0)!r}",
				False,
			))

		# ol-005: Footnote marker misread as ? or ! (? or ! in the middle of a sentence)
		bad_punct = re.compile(r"\w[?!]\s+[a-z]")
		for m in bad_punct.finditer(line):
			issues.append(Issue(
				path, lineno, "ol-005",
				f"Possible misread footnote marker (? or ! mid-sentence): {m.group(0)!r}",
				False,
			))

		# ol-006: Illustration/caption pages (lines with only a few words in all caps)
		stripped = line.strip()
		if stripped and re.fullmatch(r"[A-Z][A-Z\s\.\,\-]{5,50}", stripped):
			# Avoid flagging real ALL-CAPS headings (chapter titles handled separately)
			if not re.match(r"<h[1-6]", line):
				issues.append(Issue(
					path, lineno, "ol-006",
					f"Possible illustration/caption garbage: {stripped!r}",
					False,
				))

		# ol-007: Running header bleed-through
		if running_header_re and running_header_re.search(stripped):
			issues.append(Issue(
				path, lineno, "ol-007",
				f"Running header bleed-through: {stripped!r}",
				False,
			))

	# ol-008: Suspicious paragraph breaks (very short paragraphs sandwiched between normal ones)
	paragraphs = re.findall(r"<p>(.*?)</p>", text, re.DOTALL)
	for i, para in enumerate(paragraphs):
		words = para.split()
		if 1 <= len(words) <= 4 and i > 0 and i < len(paragraphs) - 1:
			# Short paragraph — likely a broken paragraph or dropped line
			lineno = text[:text.find(f"<p>{para}</p>")].count("\n") + 1
			issues.append(Issue(
				path, lineno, "ol-008",
				f"Short paragraph ({len(words)} words) — possible broken paragraph: {para.strip()!r}",
				False,
			))

	return issues


# ---------------------------------------------------------------------------
# Auto-fix logic
# ---------------------------------------------------------------------------

def _apply_fixes(path: Path, issues: list[Issue], extra_misreads: list[tuple[str, str]]) -> int:
	"""Apply auto-fixable rules to a file. Returns number of fixes applied."""
	try:
		text = path.read_text(encoding="utf-8")
	except Exception:
		return 0

	original = text
	fixes = 0

	# ol-001: Possessive apostrophes
	for pattern, replacement in _POSSESSIVE_PATTERNS:
		new_text, n = pattern.subn(replacement, text)
		if n:
			text = new_text
			fixes += n

	# ol-002: Hyphenated line-breaks
	new_text, n = _LINEBREAK_HYPHEN.subn(lambda m: m.group(1) + m.group(2), text)
	if n:
		text = new_text
		fixes += n

	# ol-003: Misread characters
	all_misreads = _BUILTIN_MISREADS + extra_misreads
	for pattern_str, replacement in all_misreads:
		try:
			pat = re.compile(pattern_str)
			new_text, n = pat.subn(replacement, text)
			if n and new_text != text:
				text = new_text
				fixes += n
		except re.error:
			continue

	if text != original:
		path.write_text(text, encoding="utf-8")

	return fixes


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def lint_ocr(plain_output: bool) -> int:
	"""
	Entry point for `tl lint-ocr`.
	"""

	parser = argparse.ArgumentParser(
		description="Find and fix OCR artifacts in per-page XHTML files. "
		"Without --fix, output is a clickable issue list (VS Code compatible). "
		"With --fix, auto-fixable rules are applied and the remaining issues are printed."
	)
	parser.add_argument(
		"directory",
		metavar="DIRECTORY",
		help="path to an ebook project directory",
	)
	parser.add_argument(
		"--fix",
		action="store_true",
		help="apply auto-fixable rules (ol-001 through ol-003)",
	)
	parser.add_argument(
		"--only",
		metavar="CODE",
		help="only report (or fix) issues matching this code, e.g. ol-003",
	)
	parser.add_argument(
		"--page",
		metavar="NNNN",
		help="lint only this page number (e.g. 0042)",
	)
	args = parser.parse_args()

	project_dir = Path(args.directory).resolve()
	if not project_dir.exists():
		print(f"Error: Directory not found: {project_dir}", file=sys.stderr)
		return 1

	# Find OCR directory
	sources_dir = project_dir / "_sources"
	ocr_dir = None
	if sources_dir.exists():
		for d in sources_dir.rglob("*_ocr"):
			if d.is_dir():
				ocr_dir = d
				break

	if not ocr_dir:
		print("Error: No *_ocr directory found in _sources/.", file=sys.stderr)
		print("  Run `tl ocr .` first.", file=sys.stderr)
		return 1

	# Load config
	config = _load_config(project_dir)
	running_header_re = _build_running_header_pattern(config)
	extra_misreads: list[tuple[str, str]] = [
		(pat, rep) for pat, rep in config.get("misreads", {}).items()
	]

	# Collect files
	if args.page:
		xhtml_files = sorted(ocr_dir.glob(f"{args.page}.xhtml"))
	else:
		xhtml_files = sorted(ocr_dir.glob("*.xhtml"))

	if not xhtml_files:
		print(f"No XHTML files found in {ocr_dir}", file=sys.stderr)
		return 1

	total_issues = 0
	total_fixes = 0

	for path in xhtml_files:
		issues = _lint_file(path, running_header_re, extra_misreads, config)

		if args.only:
			issues = [i for i in issues if i.code == args.only]

		if args.fix:
			auto_issues = [i for i in issues if i.auto_fixable]
			if auto_issues:
				n = _apply_fixes(path, auto_issues, extra_misreads)
				total_fixes += n
			# Re-lint to show remaining issues
			issues = _lint_file(path, running_header_re, extra_misreads, config)
			if args.only:
				issues = [i for i in issues if i.code == args.only]
			# Only report non-auto-fixable remaining
			issues = [i for i in issues if not i.auto_fixable]

		for issue in issues:
			print(f"{issue.path}:{issue.line}: [{issue.code}] {issue.message}")
			total_issues += 1

	print()
	if args.fix:
		print(f"Auto-fixes applied: {total_fixes}")
	print(f"Issues remaining:   {total_issues}")

	if total_issues > 0:
		print()
		print("Tip: click file:line links in VS Code to jump to each issue.")
		print("     Open the matching scan in Safari for context.")

	return 0
