"""
This module implements the `tl ocr-confidence-report` command.

Reads Tesseract hOCR files and produces a sorted list of words that fell
below a confidence threshold. Each entry shows:

  file:line  WORD  (confidence%)  "surrounding context"

The list is sorted by confidence (lowest first), so the most likely misreads
appear at the top. Use this as a final punch list after tl lint-ocr --fix
has handled the auto-fixable artifacts.
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# hOCR parsing
# ---------------------------------------------------------------------------

def _parse_hocr(hocr_path: Path, threshold: int) -> list[dict]:
	"""
	Parse a Tesseract hOCR file and return low-confidence words.

	Each entry: {word, confidence, line, bbox, context}
	"""
	try:
		text = hocr_path.read_text(encoding="utf-8")
	except Exception:
		return []

	entries = []

	# Tesseract hOCR word span:
	#   <span class='ocrx_word' id='word_...' title='bbox ...; x_wconf 42'>word</span>
	word_re = re.compile(
		r"<span[^>]+class=['\"]ocrx_word['\"][^>]+title=['\"]([^'\"]+)['\"][^>]*>(.*?)</span>",
		re.DOTALL,
	)

	# Also capture the surrounding line for context
	line_re = re.compile(
		r"<span[^>]+class=['\"]ocr_line['\"][^>]*>([\s\S]*?)</span>",
		re.DOTALL,
	)

	# Build a flat list of words with their line numbers (estimated from hOCR bbox)
	for line_match in line_re.finditer(text):
		line_html = line_match.group(1)
		# Extract all words in this line
		line_words = []
		for wm in word_re.finditer(line_html):
			title = wm.group(1)
			word_text = re.sub(r"<[^>]+>", "", wm.group(2)).strip()
			if not word_text:
				continue
			conf_match = re.search(r"x_wconf\s+(\d+)", title)
			if not conf_match:
				continue
			conf = int(conf_match.group(1))
			bbox_match = re.search(r"bbox\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", title)
			bbox = bbox_match.group(0) if bbox_match else ""
			line_words.append({"word": word_text, "confidence": conf, "bbox": bbox})

		# Build context string from all words in this line
		context = " ".join(w["word"] for w in line_words)

		for entry in line_words:
			if entry["confidence"] < threshold:
				entries.append({
					"word": entry["word"],
					"confidence": entry["confidence"],
					"bbox": entry["bbox"],
					"context": context,
					"hocr_file": hocr_path,
				})

	return entries


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _format_report(
	entries: list[dict],
	group_by: str,
	plain_output: bool,
) -> None:
	if not entries:
		return

	if group_by == "confidence":
		entries.sort(key=lambda e: (e["confidence"], e["word"]))
	elif group_by == "word":
		entries.sort(key=lambda e: (e["word"].lower(), e["confidence"]))
	else:  # file
		entries.sort(key=lambda e: (str(e["hocr_file"]), e["confidence"]))

	for entry in entries:
		conf = entry["confidence"]
		word = entry["word"]
		ctx = entry["context"][:80]
		path = entry["hocr_file"]
		# Truncate context around the word
		word_pos = ctx.find(word)
		if word_pos >= 0:
			start = max(0, word_pos - 20)
			end = min(len(ctx), word_pos + len(word) + 20)
			ctx_snippet = ("…" if start > 0 else "") + ctx[start:end] + ("…" if end < len(ctx) else "")
		else:
			ctx_snippet = ctx[:60]

		print(f"{path}:  [{conf:3d}%]  {word!r:25s}  {ctx_snippet!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def ocr_confidence_report(plain_output: bool) -> int:
	"""
	Entry point for `tl ocr-confidence-report`.
	"""

	parser = argparse.ArgumentParser(
		description="List words that Tesseract assigned low confidence, sorted by "
		"confidence (lowest first). Use as a final punch list after tl lint-ocr. "
		"Requires hOCR files — run `tl ocr . --hocr` if missing."
	)
	parser.add_argument(
		"directory",
		metavar="DIRECTORY",
		help="path to an ebook project directory",
	)
	parser.add_argument(
		"-t", "--threshold",
		type=int,
		default=70,
		metavar="0-100",
		help="confidence threshold: report words below this value (default: 70)",
	)
	parser.add_argument(
		"--group-by",
		choices=["confidence", "word", "file"],
		default="confidence",
		help="sort order for the report (default: confidence)",
	)
	parser.add_argument(
		"--page",
		metavar="NNNN",
		help="limit report to this page number (e.g. 0042)",
	)
	parser.add_argument(
		"--min-length",
		type=int,
		default=2,
		metavar="N",
		help="ignore words shorter than N characters (default: 2)",
	)
	parser.add_argument(
		"--top",
		type=int,
		default=None,
		metavar="N",
		help="show only the N lowest-confidence words",
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
		print("  Run `tl ocr . --hocr` first.", file=sys.stderr)
		return 1

	# Find hOCR files
	if args.page:
		hocr_files = sorted(ocr_dir.glob(f"{args.page}.hocr"))
	else:
		hocr_files = sorted(ocr_dir.glob("*.hocr"))

	if not hocr_files:
		print(f"No .hocr files found in {ocr_dir}", file=sys.stderr)
		print("  Run `tl ocr . --hocr` to generate hOCR output.", file=sys.stderr)
		return 1

	print(f"hOCR files:    {len(hocr_files)}")
	print(f"Threshold:     below {args.threshold}% confidence")
	print(f"Min length:    {args.min_length} chars")
	print()

	all_entries = []
	for hocr_path in hocr_files:
		entries = _parse_hocr(hocr_path, args.threshold)
		# Filter by minimum word length
		entries = [e for e in entries if len(e["word"]) >= args.min_length]
		all_entries.extend(entries)

	if not all_entries:
		print(f"No words below {args.threshold}% confidence — looks clean!")
		return 0

	# Deduplicate if grouping by word (show unique words with their lowest confidence)
	if args.group_by == "word":
		seen: dict[str, dict] = {}
		for e in all_entries:
			key = e["word"].lower()
			if key not in seen or e["confidence"] < seen[key]["confidence"]:
				seen[key] = e
		all_entries = list(seen.values())

	# Sort
	all_entries.sort(key=lambda e: (e["confidence"], e["word"].lower()))

	# Top N
	if args.top:
		all_entries = all_entries[: args.top]

	print(f"Low-confidence words: {len(all_entries)}")
	print("-" * 72)
	_format_report(all_entries, args.group_by, plain_output)

	print()
	print(f"Tip: open the matching scan in Safari to verify each word.")
	print(f"     Edit the corresponding XHTML in VS Code or Korrektur.")

	return 0
