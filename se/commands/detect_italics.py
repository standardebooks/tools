"""
This module implements the `tl detect-italics` command.

Two detection modes:

  --mode phrase-list  (high confidence)
      Wraps known phrases — Tolstoy work titles, periodicals, foreign-language
      phrases, ship names — in <i epub:type="...">. Uses a built-in list plus
      an optional .tl-italics.yaml in the project root.

  --mode hocr  (speculative)
      Reads Tesseract hOCR files and wraps words/spans that Tesseract tagged
      as italic. Wraps them in <i class="ocr-italic-guess"> so they are
      visually flagged for manual review and se lint can catch any that slipped
      through unresolved.

Use --write to apply changes in place. Without --write, prints a diff-like
report showing what would change.
"""

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

try:
	import yaml  # type: ignore
	_YAML_AVAILABLE = True
except ImportError:
	_YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Built-in phrase list
# (Tolstoy work titles, journals, ships, foreign phrases most likely to appear
#  in biographical and critical texts from this era)
# ---------------------------------------------------------------------------

_BUILTIN_PHRASES: list[tuple[str, str]] = [
	# Works — novels / novellas
	("War and Peace",               "se:name.publication.book"),
	("Anna Karenina",               "se:name.publication.book"),
	("Resurrection",                "se:name.publication.book"),
	("The Death of Ivan Ilyich",    "se:name.publication.book"),
	("The Kreutzer Sonata",         "se:name.publication.book"),
	("Family Happiness",            "se:name.publication.book"),
	("Childhood",                   "se:name.publication.book"),
	("Boyhood",                     "se:name.publication.book"),
	("Youth",                       "se:name.publication.book"),
	("The Cossacks",                "se:name.publication.book"),
	("Hadji Murad",                 "se:name.publication.book"),
	("Master and Man",              "se:name.publication.book"),
	("The Power of Darkness",       "se:name.publication.book"),
	("The Fruits of Enlightenment", "se:name.publication.book"),
	("What Then Must We Do?",       "se:name.publication.book"),
	("What Is Art?",                "se:name.publication.book"),
	("The Kingdom of God Is Within You", "se:name.publication.book"),
	# Journals / newspapers
	("The Contemporary",            "se:name.publication.journal"),
	("Sovremennik",                 "se:name.publication.journal"),
	("Otechestvennye Zapiski",      "se:name.publication.journal"),
	("Messenger of Europe",         "se:name.publication.journal"),
	("Russian Gazette",             "se:name.publication.journal"),
	# Foreign phrases commonly used without translation in this period
	("à la",                        "z3998:foreign"),
	("en route",                    "z3998:foreign"),
	("vis-à-vis",                   "z3998:foreign"),
	("raison d'être",               "z3998:foreign"),
	("bête noire",                  "z3998:foreign"),
	("terra firma",                 "z3998:foreign"),
	("in statu quo",                "z3998:foreign"),
	("carte blanche",               "z3998:foreign"),
	("de facto",                    "z3998:foreign"),
	("de jure",                     "z3998:foreign"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_extra_phrases(project_dir: Path) -> list[tuple[str, str]]:
	"""Load additional phrases from .tl-italics.yaml."""
	cfg = project_dir / ".tl-italics.yaml"
	if not cfg.exists():
		return []
	if not _YAML_AVAILABLE:
		print("Warning: PyYAML not installed — .tl-italics.yaml ignored.", file=sys.stderr)
		return []
	with open(cfg, encoding="utf-8") as f:
		data = yaml.safe_load(f) or {}
	extras = []
	for phrase, semantic in data.get("phrases", {}).items():
		extras.append((phrase, semantic))
	return extras


def _wrap_phrase(text: str, phrase: str, semantic: str) -> tuple[str, int]:
	"""
	Replace bare occurrences of phrase with <i epub:type="SEMANTIC">phrase</i>.
	Only matches text outside existing tags. Returns (new_text, count).
	"""
	# Build a pattern that skips content already inside a tag
	escaped = re.escape(phrase)
	pattern = re.compile(
		r"(?<![<\w])" + escaped + r"(?![>\w])",
		re.IGNORECASE,
	)
	original = text
	count = 0

	def _replace(m):
		nonlocal count
		# Check that we're not inside an existing tag
		start = m.start()
		before = text[:start]
		# Count open < and > to see if we're inside a tag
		if before.count("<") > before.count(">"):
			return m.group(0)
		count += 1
		return f'<i epub:type="{semantic}">{m.group(0)}</i>'

	new_text = pattern.sub(_replace, text)
	return new_text, count


def _parse_hocr_italic_spans(hocr_text: str, confidence_threshold: int) -> list[str]:
	"""
	Extract word strings that Tesseract tagged as italic with sufficient confidence.
	Returns a list of word strings.
	"""
	italic_words = []

	# Tesseract hOCR italic words have class="ocrx_word" and font-style:italic in title
	word_pattern = re.compile(
		r'<span[^>]+class=["\']ocrx_word["\'][^>]+title=["\']([^"\']+)["\'][^>]*>(.*?)</span>',
		re.DOTALL,
	)
	for m in word_pattern.finditer(hocr_text):
		title_attr = m.group(1)
		word_text = re.sub(r"<[^>]+>", "", m.group(2)).strip()

		if not word_text:
			continue

		# Check confidence
		conf_match = re.search(r"x_wconf\s+(\d+)", title_attr)
		if not conf_match:
			continue
		conf = int(conf_match.group(1))
		if conf < confidence_threshold:
			continue

		# Check for italic flag (Tesseract 5 marks this in the title as x_font italic)
		if "italic" in title_attr.lower() or "x_font" in title_attr.lower():
			italic_words.append(word_text)

	return italic_words


# ---------------------------------------------------------------------------
# Mode: phrase-list
# ---------------------------------------------------------------------------

def _apply_phrase_list(
	xhtml_files: list[Path],
	phrases: list[tuple[str, str]],
	write: bool,
	plain_output: bool,
) -> int:
	total = 0
	for path in xhtml_files:
		try:
			text = path.read_text(encoding="utf-8")
		except Exception:
			continue

		new_text = text
		file_changes = 0
		for phrase, semantic in phrases:
			new_text, n = _wrap_phrase(new_text, phrase, semantic)
			file_changes += n

		if file_changes and new_text != text:
			total += file_changes
			if write:
				path.write_text(new_text, encoding="utf-8")
			if not plain_output:
				print(f"  {path.name}: {file_changes} phrase(s) wrapped")

	return total


# ---------------------------------------------------------------------------
# Mode: hocr
# ---------------------------------------------------------------------------

def _apply_hocr(
	xhtml_files: list[Path],
	ocr_dir: Path,
	confidence: int,
	write: bool,
	plain_output: bool,
) -> int:
	total = 0
	for xhtml_path in xhtml_files:
		# Find matching hOCR file
		hocr_path = ocr_dir / (xhtml_path.stem + ".hocr")
		if not hocr_path.exists():
			continue

		try:
			hocr_text = hocr_path.read_text(encoding="utf-8")
			xhtml_text = xhtml_path.read_text(encoding="utf-8")
		except Exception:
			continue

		italic_words = _parse_hocr_italic_spans(hocr_text, confidence)
		if not italic_words:
			continue

		new_text = xhtml_text
		file_changes = 0
		for word in set(italic_words):
			if not word or len(word) < 2:
				continue
			escaped = re.escape(word)
			pattern = re.compile(r"(?<![<\w>])" + escaped + r"(?![>\w<])")
			replacement = f'<i class="ocr-italic-guess">{word}</i>'
			new_xhtml, n = pattern.subn(replacement, new_text)
			if n:
				new_text = new_xhtml
				file_changes += n

		if file_changes and new_text != xhtml_text:
			total += file_changes
			if write:
				xhtml_path.write_text(new_text, encoding="utf-8")
			if not plain_output:
				print(f"  {xhtml_path.name}: {file_changes} italic word(s) wrapped (ocr-italic-guess)")

	return total


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def detect_italics(plain_output: bool) -> int:
	"""
	Entry point for `tl detect-italics`.
	"""

	parser = argparse.ArgumentParser(
		description="Detect and wrap italic text in ebook XHTML files. "
		"Two modes: phrase-list (high confidence, uses known titles and foreign phrases) "
		"and hocr (speculative, uses Tesseract italic tags). "
		"Without --write, prints a report without modifying files."
	)
	parser.add_argument(
		"directory",
		metavar="DIRECTORY",
		help="path to an ebook project directory",
	)
	parser.add_argument(
		"--mode",
		choices=["phrase-list", "hocr"],
		required=True,
		help="detection mode: 'phrase-list' or 'hocr'",
	)
	parser.add_argument(
		"--write",
		action="store_true",
		help="apply changes in place (default: dry run)",
	)
	parser.add_argument(
		"--confidence",
		type=int,
		default=70,
		metavar="0-100",
		help="minimum Tesseract confidence for hOCR mode (default: 70)",
	)
	parser.add_argument(
		"--src",
		metavar="DIR",
		help="path to src/epub/text/ XHTML files (default: auto-detected)",
	)
	args = parser.parse_args()

	project_dir = Path(args.directory).resolve()
	if not project_dir.exists():
		print(f"Error: Directory not found: {project_dir}", file=sys.stderr)
		return 1

	# Find XHTML source files
	if args.src:
		text_dir = Path(args.src).resolve()
	else:
		text_dir = project_dir / "src" / "epub" / "text"

	if not text_dir.exists():
		print(f"Error: XHTML source directory not found: {text_dir}", file=sys.stderr)
		return 1

	xhtml_files = sorted(text_dir.glob("*.xhtml"))
	if not xhtml_files:
		print(f"No .xhtml files found in {text_dir}", file=sys.stderr)
		return 1

	mode_label = "Phrase list" if args.mode == "phrase-list" else "hOCR-based"
	write_label = "Applying" if args.write else "Dry run —"
	print(f"{write_label} {mode_label} italic detection on {len(xhtml_files)} file(s) in {text_dir}")
	print()

	if args.mode == "phrase-list":
		extra = _load_extra_phrases(project_dir)
		all_phrases = _BUILTIN_PHRASES + extra
		print(f"Phrases in list: {len(all_phrases)} ({len(_BUILTIN_PHRASES)} built-in + {len(extra)} from .tl-italics.yaml)")
		print()
		total = _apply_phrase_list(xhtml_files, all_phrases, args.write, plain_output)

	else:  # hocr
		# Find OCR directory for hOCR files
		ocr_dir = None
		sources_dir = project_dir / "_sources"
		if sources_dir.exists():
			for d in sources_dir.rglob("*_ocr"):
				if d.is_dir():
					ocr_dir = d
					break

		if not ocr_dir:
			print("Error: No *_ocr directory found. Run `tl ocr . --hocr` first.", file=sys.stderr)
			return 1

		hocr_files = list(ocr_dir.glob("*.hocr"))
		if not hocr_files:
			print(f"Error: No .hocr files found in {ocr_dir}.", file=sys.stderr)
			print("  Re-run `tl ocr . --hocr` to generate hOCR output.", file=sys.stderr)
			return 1

		print(f"hOCR files:      {len(hocr_files)} in {ocr_dir}")
		print(f"Confidence min:  {args.confidence}")
		print()
		total = _apply_hocr(xhtml_files, ocr_dir, args.confidence, args.write, plain_output)

	print()
	action = "wrapped" if args.write else "would wrap"
	print(f"Total: {total} italic instance(s) {action}.")

	if not args.write and total > 0:
		print()
		print("Run with --write to apply changes.")

	if args.mode == "hocr" and args.write and total > 0:
		print()
		print("Next step: review <i class=\"ocr-italic-guess\"> instances manually.")
		print("  Change to <i epub:type=\"...\"> or <em> as appropriate.")
		print("  se lint will flag any ocr-italic-guess that remain after semanticate.")

	return 0
