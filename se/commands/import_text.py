"""
This module implements the `tl import-text` command.

Imports a local source text file (.txt, .md, .html, or .epub) into
an existing tolstoy.life ebook source directory, converting it to
SE-compatible XHTML chapter files.
"""

import argparse
import zipfile
from pathlib import Path
import importlib.resources

import regex
import roman
from lxml import etree

import se
from se.xhtml_sanitize import sanitize_xhtml, strip_ocr_noise


console = se.init_console()

# ---------------------------------------------------------------------------
# Format-specific readers — each returns a list of (title, body_html) tuples
# ---------------------------------------------------------------------------

def _read_plain_text(text: str) -> list[tuple[str, str]]:
	"""
	Split plain text into chapters.

	Detection order:
	1. Lines matching 'CHAPTER <number/roman>' (case-insensitive)
	2. Lines that are ALL CAPS and surrounded by blank lines
	3. If no headings found, treat the whole file as one chapter
	"""

	lines = text.splitlines()

	# Strip OCR page markers (e.g. "--- PAGE 0053 ---") inserted by ocr-scans.sh
	lines = [line for line in lines if not regex.match(r"^---\s*PAGE\s+\d+\s*---$", line.strip())]

	# Normalize excessive whitespace common in OCR/DjVu text (e.g., "CHAPTER   I" → "CHAPTER I")
	normalized = [regex.sub(r"  +", " ", line) for line in lines]

	# --- Pass 1: look for explicit "Chapter X" headings ---
	chapter_headings: list[tuple[int, str]] = []
	for i, norm in enumerate(normalized):
		stripped = norm.strip()
		if not stripped:
			continue
		if regex.match(r"^chapter\s+[\divxlcm]+\.?$", stripped, flags=regex.IGNORECASE):
			chapter_headings.append((i, stripped))

	# --- Pass 2: fall back to ALL CAPS lines only if no Chapter headings were found ---
	if not chapter_headings:
		for i, norm in enumerate(normalized):
			stripped = norm.strip()
			if not stripped:
				continue
			# Must be ALL CAPS, alphabetic content, reasonable length, and surrounded by blank lines
			if (stripped == stripped.upper()
					and regex.match(r"^[A-Z][A-Z\s\d.,!?\-:;]+$", stripped)
					and len(stripped) > 5
					and len(stripped) < 80):
				prev_blank = (i == 0) or (normalized[i - 1].strip() == "")
				next_blank = (i == len(normalized) - 1) or (normalized[i + 1].strip() == "")
				if prev_blank and next_blank:
					chapter_headings.append((i, stripped))

	if not chapter_headings:
		# No headings detected — single chapter
		body = _paragraphs_from_lines(normalized)
		return [("", body)]

	result: list[tuple[str, str]] = []
	for idx, (start_line, heading) in enumerate(chapter_headings):
		if idx + 1 < len(chapter_headings):
			end_line = chapter_headings[idx + 1][0]
		else:
			end_line = len(normalized)

		# Body starts after the heading line
		body_lines = normalized[start_line + 1:end_line]
		body = _paragraphs_from_lines(body_lines)
		result.append((heading, body))

	return result


def _paragraphs_from_lines(lines: list[str]) -> str:
	"""
	Convert plain text lines into <p> elements.
	Blank lines separate paragraphs.
	"""

	paragraphs: list[str] = []
	current: list[str] = []

	for line in lines:
		stripped = line.strip()
		if stripped == "":
			if current:
				paragraphs.append(" ".join(current))
				current = []
		else:
			current.append(_escape_xml(stripped))

	if current:
		paragraphs.append(" ".join(current))

	return "\n\t\t\t\t".join(f"<p>{p}</p>" for p in paragraphs)


def _escape_xml(text: str) -> str:
	"""Escape XML special characters in text content."""
	text = text.replace("&", "&amp;")
	text = text.replace("<", "&lt;")
	text = text.replace(">", "&gt;")
	return text



def _read_markdown(text: str) -> list[tuple[str, str]]:
	"""
	Split Markdown into chapters using ## headings (h2) as split points.
	Falls back to # headings (h1) if no h2 found.
	Falls back to plain-text detection if no headings at all.
	"""

	# Determine which heading level to split on
	h2_lines = [(i, line) for i, line in enumerate(text.splitlines()) if regex.match(r"^##\s+", line)]
	h1_lines = [(i, line) for i, line in enumerate(text.splitlines()) if regex.match(r"^#\s+", line)]

	if h2_lines:
		heading_pattern = r"^##\s+"
		split_lines = h2_lines
	elif h1_lines:
		heading_pattern = r"^#\s+"
		split_lines = h1_lines
	else:
		# No markdown headings — fall back to plain text detection
		return _read_plain_text(text)

	lines = text.splitlines()
	result: list[tuple[str, str]] = []

	for idx, (start_line, heading_line) in enumerate(split_lines):
		heading = regex.sub(heading_pattern, "", heading_line).strip()

		if idx + 1 < len(split_lines):
			end_line = split_lines[idx + 1][0]
		else:
			end_line = len(lines)

		body_lines = lines[start_line + 1:end_line]
		body = _markdown_to_html(body_lines)
		result.append((heading, body))

	return result


def _markdown_to_html(lines: list[str]) -> str:
	"""
	Minimal Markdown-to-HTML conversion.
	Handles: paragraphs, bold, italic, blockquotes.
	For full fidelity, use pandoc externally before importing.
	"""

	paragraphs: list[str] = []
	current: list[str] = []
	in_blockquote = False
	blockquote_lines: list[str] = []

	def _flush_current() -> None:
		nonlocal current
		if current:
			text = " ".join(current)
			text = _inline_markdown(text)
			paragraphs.append(f"<p>{text}</p>")
			current = []

	def _flush_blockquote() -> None:
		nonlocal in_blockquote, blockquote_lines
		if blockquote_lines:
			inner = " ".join(_inline_markdown(l) for l in blockquote_lines)
			paragraphs.append(f"<blockquote>\n\t\t\t\t\t<p>{inner}</p>\n\t\t\t\t</blockquote>")
			blockquote_lines = []
		in_blockquote = False

	for line in lines:
		stripped = line.strip()

		# Blockquote lines
		if stripped.startswith("> "):
			_flush_current()
			in_blockquote = True
			blockquote_lines.append(stripped[2:])
			continue
		elif in_blockquote and stripped == "":
			_flush_blockquote()
			continue
		elif in_blockquote:
			_flush_blockquote()

		# Blank line = paragraph break
		if stripped == "":
			_flush_current()
			continue

		current.append(_escape_xml(stripped))

	_flush_current()
	_flush_blockquote()

	return "\n\t\t\t\t".join(paragraphs)


def _inline_markdown(text: str) -> str:
	"""Convert inline Markdown (bold, italic) to HTML."""
	# Bold: **text** or __text__
	text = regex.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
	text = regex.sub(r"__(.+?)__", r"<b>\1</b>", text)
	# Italic: *text* or _text_
	text = regex.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
	text = regex.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
	return text


def _read_html(text: str) -> list[tuple[str, str]]:
	"""
	Split an HTML file into chapters at <h2> boundaries.
	Falls back to <h1> if no <h2> found.
	Extracts inner HTML of each chapter section.
	"""

	# Try to parse as XML first, fall back to HTML parser
	try:
		parser = etree.HTMLParser(encoding="utf-8")
		tree = etree.fromstring(text.encode("utf-8"), parser)
	except Exception:
		# If even the HTML parser fails, treat as plain text
		return _read_plain_text(text)

	body = tree.find(".//body")
	if body is None:
		body = tree

	# Look for h2 elements first, then h1
	h2s = body.findall(".//h2")
	h1s = body.findall(".//h1")

	headings = h2s if h2s else h1s if h1s else []

	if not headings:
		# No headings — grab all body content as one chapter
		body_html = _inner_html(body)
		return [("", body_html)]

	result: list[tuple[str, str]] = []

	for heading in headings:
		title = etree.tostring(heading, method="text", encoding="unicode").strip()

		# Collect all siblings after this heading until the next heading of the same level
		tag = heading.tag
		content_parts: list[str] = []
		sibling = heading.getnext()
		while sibling is not None:
			if sibling.tag == tag:
				break
			content_parts.append(etree.tostring(sibling, method="html", encoding="unicode").strip())
			sibling = sibling.getnext()

		body_html = "\n\t\t\t\t".join(content_parts)
		result.append((title, body_html))

	return result


def _inner_html(element: etree._Element) -> str:
	"""Get the inner HTML of an lxml element."""
	parts = []
	if element.text:
		parts.append(_escape_xml(element.text))
	for child in element:
		parts.append(etree.tostring(child, method="html", encoding="unicode"))
	return "\n\t\t\t\t".join(p.strip() for p in parts if p.strip())


def _is_nontext_content(body_html: str) -> bool:
	"""
	Return True if the HTML body looks like a non-text page that should be
	skipped during import: cover pages, IA boilerplate, navigation, etc.
	"""

	stripped = body_html.strip()
	if not stripped:
		return True

	# Cover pages: body is just an <img> tag (possibly with wrapper)
	if regex.match(r"^<img\b[^>]*>$", stripped, flags=regex.DOTALL):
		return True

	# IA EPUB boilerplate: notice/about pages
	lower = stripped.lower()
	if "internet archive" in lower and ("this book was produced" in lower or "was founded in 1996" in lower):
		return True

	# Navigation-only pages (just an <ol>/<ul> of links)
	if regex.match(r"^<[ou]l\b[^>]*>\s*(<li\b[^>]*>\s*<a\b[^>]*>.*?</a>\s*</li>\s*)+</[ou]l>$", stripped, flags=regex.DOTALL):
		return True

	return False



def _strip_page_preamble(text: str) -> str:
	"""
	Strip OCR preamble from the beginning of a page's plain text.

	IA scanned pages typically begin with:
	1. A Roman or Arabic page number (e.g. "XXVI", "42")
	2. An OCR accuracy estimate ("The text on this page is estimated to be only 28% accurate")
	3. A lowercase Roman numeral page number (e.g. "xxvi", "xiv")

	These are not content — strip them so heading detection can see the real text.
	"""

	# Strip leading/trailing whitespace
	text = text.strip()

	# Strip leading uppercase Roman numeral page number (standalone, e.g. "XXVI ")
	text = regex.sub(r"^[IVXLCDM]+\s+", "", text)

	# Strip OCR accuracy line
	text = regex.sub(r"^The text on this page is estimated to be only [\d.]+% accurate\s*", "", text, flags=regex.IGNORECASE)

	# Strip leading lowercase Roman numeral page number (e.g. "xxvi ")
	text = regex.sub(r"^[ivxlcdm]+\s+", "", text)

	# Strip leading Arabic page number (e.g. "42 ")
	text = regex.sub(r"^\d+\s+", "", text)

	return text.strip()


def _detect_heading(body_html: str) -> str | None:
	"""
	Detect a real chapter or part heading in a page's HTML content.

	IA EPUBs split by page, not by chapter. Headings appear as ALL CAPS
	text inside <p> elements (not as <h1>/<h2>). This function scans the
	first portion of the page text for patterns like:

	- "CHAPTER I", "CHAPTER XII", "CHAP. IV"
	- "PART I", "PART III"
	- "INTRODUCTION", "CONCLUSION", "BIBLIOGRAPHY", "PREFACE"

	Returns a tuple-style string if found:
	- "CHAPTER I" for chapter headings
	- "PART I" for part-only pages
	- "PART I :: CHAPTER I" when both appear on the same page
	- "INTRODUCTION" for named sections

	Returns None if no heading is detected.
	"""

	# Strip tags to get plain text
	text = regex.sub(r"<[^>]+>", " ", body_html)
	text = regex.sub(r"&\w+;", " ", text)  # strip entities
	text = regex.sub(r"\s+", " ", text).strip()

	# Strip page numbers and OCR noise from the start
	text = _strip_page_preamble(text)

	# Check a generous window — IA pages can have book title + part title
	# before the chapter heading (e.g. "BIOGRAPHY OF LEO TOLSTOY PART I ... CHAPTER I ...")
	check = text[:500]

	# Priority 0: Named sections at page start — check BEFORE PART/CHAPTER
	# because CONTENTS pages list "PART I", "CHAPTER IV" etc. as TOC entries,
	# and we don't want those matched as real headings.
	early = text[:80]
	match = regex.match(
		r"^(?:BIOGRAPHY[A-Z\s]*?)?(CONTENTS|LIST OF ILLUSTRATIONS)\b",
		early,
		flags=regex.IGNORECASE
	)
	if match:
		return match.group(1).strip().upper()

	# Priority 1: Look for CHAPTER heading anywhere in the check window
	chapter_match = regex.search(
		r"\b((?:CHAPTER|CHAP\.?)\s+[IVXLCDM\d]+\.?)\b",
		check
	)

	# Priority 2: Look for PART heading
	part_match = regex.search(
		r"\b(PART\s+[IVXLCDM]+)\b",
		check
	)

	if chapter_match and part_match:
		# Both found — return combined heading
		return f"{part_match.group(1).strip()} :: {chapter_match.group(1).strip()}"

	if chapter_match:
		return chapter_match.group(1).strip()

	if part_match:
		return part_match.group(1).strip()

	# Priority 3: Other named sections near page start
	match = regex.match(
		r"^(?:BIOGRAPHY[A-Z\s]*?)?(INTRODUCTION|CONCLUSION|BIBLIOGRAPHY|PREFACE|APPENDIX)\b",
		early,
		flags=regex.IGNORECASE
	)
	if match:
		return match.group(1).strip().upper()

	return None


def _normalize_section_name(heading: str) -> str:
	"""
	Extract the canonical section name from a heading for deduplication.

	"PART I :: CHAPTER I" → "CHAPTER I"
	"CHAPTER I" → "CHAPTER I"
	"PART I" → "PART I"
	"INTRODUCTION" → "INTRODUCTION"
	"""

	if " :: " in heading:
		# Combined PART + CHAPTER — the chapter is the canonical key
		return heading.split(" :: ", 1)[1]
	return heading


def _merge_pages_into_chapters(pages: list[tuple[str, str]]) -> list[tuple[str, str]]:
	"""
	Merge page-level chunks into real chapters by detecting headings.

	IA EPUBs typically have one spine item per scanned page. This function
	scans each page for real chapter/part headings and merges all pages
	between headings into a single chapter.

	Special handling:
	- PART-only pages (no CHAPTER on the same page) are merged with the
	  following chapter rather than creating a 1-page section.
	- Consecutive pages with the same named section (e.g. INTRODUCTION
	  running across pages 11-18) are merged into one section.

	If no headings are detected (i.e. the EPUB already has proper chapter
	structure), the input is returned unchanged.
	"""

	if not pages:
		return pages

	# First pass: detect headings on each page
	page_headings: list[str | None] = []
	for _, body in pages:
		page_headings.append(_detect_heading(body))

	heading_indices: list[tuple[int, str]] = [
		(i, h) for i, h in enumerate(page_headings) if h is not None
	]

	# If very few headings found relative to page count, it's likely a
	# page-per-page EPUB that needs merging. If the ratio is close to 1:1,
	# the EPUB already has proper chapters — don't merge.
	if not heading_indices or len(heading_indices) >= len(pages) * 0.5:
		return pages

	# Second pass: consolidate headings
	# - Merge PART-only pages into the following CHAPTER
	# - Merge consecutive pages with the same named section
	consolidated: list[tuple[int, str]] = []

	i = 0
	while i < len(heading_indices):
		page_idx, heading = heading_indices[i]

		# Is this a PART-only page (no CHAPTER on the same page)?
		if regex.match(r"^PART\s+[IVXLCDM]+$", heading):
			# Look ahead: if the next heading is a CHAPTER (or PART::CHAPTER),
			# skip this PART-only page — its content will be absorbed into the
			# next chapter's page range
			if i + 1 < len(heading_indices):
				next_heading = heading_indices[i + 1][1]
				if "CHAPTER" in next_heading or "CHAP" in next_heading:
					# Merge: use next heading but start from this page
					next_page_idx = heading_indices[i + 1][0]
					# The combined heading uses PART info
					combined = f"{heading} :: {_normalize_section_name(next_heading)}"
					consolidated.append((page_idx, combined))
					i += 2  # skip both PART and CHAPTER entries
					continue
			# No following chapter — keep the PART heading as-is
			consolidated.append((page_idx, heading))
			i += 1
			continue

		# For named sections: check if the previous consolidated entry has
		# the same canonical name — if so, don't start a new section
		canonical = _normalize_section_name(heading)
		if consolidated:
			prev_canonical = _normalize_section_name(consolidated[-1][1])
			if canonical == prev_canonical:
				# Same section continuing on next page — skip this heading
				i += 1
				continue

		consolidated.append((page_idx, heading))
		i += 1

	heading_indices = consolidated

	console.print(f"  Detected {len(heading_indices)} chapter/section headings across {len(pages)} pages — merging pages into chapters.")
	for page_idx, heading in heading_indices:
		console.print(f"    Page {page_idx + 1}: {heading}")

	merged: list[tuple[str, str]] = []

	# Pages before the first heading → front matter
	if heading_indices[0][0] > 0:
		front_matter_bodies = [body for _, body in pages[:heading_indices[0][0]]]
		merged_body = "\n\t\t\t\t".join(b for b in front_matter_bodies if b.strip())
		if merged_body.strip():
			merged.append(("Front Matter", merged_body))

	# Merge pages between headings
	for idx, (start_page, heading) in enumerate(heading_indices):
		if idx + 1 < len(heading_indices):
			end_page = heading_indices[idx + 1][0]
		else:
			end_page = len(pages)

		# Collect bodies from all pages in this chapter
		chapter_bodies = [body for _, body in pages[start_page:end_page]]
		merged_body = "\n\t\t\t\t".join(b for b in chapter_bodies if b.strip())
		if merged_body.strip():
			# Clean up the heading for use as chapter title
			title = _normalize_section_name(heading)
			# Normalise casing: "CHAPTER XII" → "Chapter XII",
			# "INTRODUCTION" → "Introduction"
			# Preserve Roman numerals (II, IV, XII) and Arabic digits
			parts = title.split()
			if parts:
				parts[0] = parts[0].capitalize()
				for j in range(1, len(parts)):
					if not regex.match(r"^[IVXLCDM\d]+\.?$", parts[j]):
						parts[j] = parts[j].capitalize()
			title = " ".join(parts)
			merged.append((title, merged_body))

	return merged


def _read_epub(filepath: Path) -> list[tuple[str, str]]:
	"""
	Extract text from an EPUB file by reading its spine-ordered XHTML files.

	For EPUBs with proper chapter structure (<h1>/<h2> elements), splits
	at heading boundaries as expected.

	For IA page-level EPUBs (one spine item per scanned page, no heading
	elements), detects real chapter headings in the text content and merges
	consecutive pages between them into single chapters.

	Skips non-text content (cover pages, IA boilerplate, navigation).
	"""

	if not zipfile.is_zipfile(filepath):
		raise se.InvalidFileException(f"Not a valid EPUB/ZIP file: {filepath}")

	chapters: list[tuple[str, str]] = []

	with zipfile.ZipFile(filepath, "r") as zf:
		# Find the OPF file
		container_xml = zf.read("META-INF/container.xml")
		container_tree = etree.fromstring(container_xml)
		ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
		rootfile = container_tree.find(".//c:rootfile", ns)
		if rootfile is None:
			raise se.InvalidFileException("No rootfile found in container.xml")

		opf_path = rootfile.get("full-path", "")
		opf_dir = str(Path(opf_path).parent)
		opf_xml = zf.read(opf_path)
		opf_tree = etree.fromstring(opf_xml)

		# Get the default namespace
		opf_ns = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}

		# Build manifest id -> href map
		manifest = {}
		for item in opf_tree.findall(".//opf:manifest/opf:item", opf_ns):
			item_id = item.get("id", "")
			href = item.get("href", "")
			media_type = item.get("media-type", "")
			if "xhtml" in media_type or "html" in media_type:
				manifest[item_id] = href

		skipped_count = 0

		# Read spine items in order
		for itemref in opf_tree.findall(".//opf:spine/opf:itemref", opf_ns):
			idref = itemref.get("idref", "")
			if idref not in manifest:
				continue

			href = manifest[idref]
			full_path = f"{opf_dir}/{href}" if opf_dir != "." else href

			try:
				content = zf.read(full_path).decode("utf-8")
			except (KeyError, UnicodeDecodeError):
				continue

			# Parse and extract chapters from this file
			file_chapters = _read_html(content)

			# Filter out non-text pages (covers, boilerplate, navigation)
			for title, body in file_chapters:
				if _is_nontext_content(body):
					skipped_count += 1
					continue
				chapters.append((title, body))

		if skipped_count > 0:
			console.print(f"  Skipped {skipped_count} non-text page(s) (covers, boilerplate, navigation).")

	# Merge page-level chunks into real chapters if this is an IA page-per-page EPUB
	chapters = _merge_pages_into_chapters(chapters)

	return chapters


# ---------------------------------------------------------------------------
# XHTML output
# ---------------------------------------------------------------------------

def _write_chapter(output_dir: Path, chapter_number: int, title: str, body_html: str, template: str) -> Path:
	"""
	Write a single chapter XHTML file using the SE template.
	Returns the path to the written file.
	"""

	filename = f"chapter-{chapter_number}.xhtml"
	file_id = f"chapter-{chapter_number}"

	xhtml = template.replace("ID", file_id)
	xhtml = xhtml.replace("NUMERAL", str(roman.toRoman(chapter_number)))

	# Build the section content
	if title:
		# Convert title to title case for the heading
		heading = f"<h2 epub:type=\"title\">{_escape_xml(title)}</h2>"
		section_content = f"{heading}\n\t\t\t\t{body_html}"
	else:
		section_content = body_html

	xhtml = xhtml.replace("TEXT", section_content)

	output_path = output_dir / filename
	with open(output_path, "w", encoding="utf-8") as f:
		f.write(xhtml)

	return output_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def import_text(plain_output: bool) -> int:
	"""
	Entry point for `tl import-text`.
	"""

	parser = argparse.ArgumentParser(
		description="Import a local source text file (.txt, .md, .html, or .epub) into an ebook source directory as SE-compatible XHTML chapter files."
	)
	parser.add_argument("source", metavar="SOURCE", help="path to the source file (.txt, .md, .html, or .epub)")
	parser.add_argument("-d", "--dest", metavar="DIRECTORY", default=".", help="the ebook source directory (default: current directory)")
	parser.add_argument("-s", "--start-at", metavar="INTEGER", type=se.is_positive_integer, default="1", help="start numbering chapters at this number (default: 1)")
	parser.add_argument("-f", "--filename-format", metavar="STRING", type=str, default="chapter-%n.xhtml", help="output filename format; %%n is replaced with the chapter number (default: chapter-%%n.xhtml)")
	parser.add_argument("-l", "--language", metavar="LANG", type=str, default="en-US", help="BCP 47 language tag for the text (default: en-US)")
	args = parser.parse_args()

	source_path = Path(args.source).resolve()
	dest_dir = Path(args.dest).resolve()

	# Validate source file
	if not source_path.exists():
		se.print_error(f"Couldn't open file: [path][link=file://{source_path}]{source_path}[/][/].", plain_output=plain_output)
		return se.InvalidFileException.code

	suffix = source_path.suffix.lower()
	supported = (".txt", ".md", ".html", ".htm", ".xhtml", ".epub")
	if suffix not in supported:
		se.print_error(f"Unsupported file format: [text]{suffix}[/]. Supported formats: {', '.join(supported)}.", plain_output=plain_output)
		return se.InvalidFileException.code

	# Determine output directory for chapter files
	text_dir = dest_dir / "src" / "epub" / "text"
	if not text_dir.exists():
		# Maybe dest_dir is already the text directory, or doesn't have SE structure
		if dest_dir.name == "text" and dest_dir.exists():
			text_dir = dest_dir
		else:
			se.print_error(f"Couldn't find [path]src/epub/text/[/] in [path][link=file://{dest_dir}]{dest_dir}[/][/]. Is this an SE source directory?", plain_output=plain_output)
			return se.InvalidFileException.code

	# Read and parse the source file
	try:
		if suffix == ".epub":
			chapters = _read_epub(source_path)
		else:
			with open(source_path, "r", encoding="utf-8") as f:
				text = f.read()

			if suffix == ".md":
				chapters = _read_markdown(text)
			elif suffix in (".html", ".htm", ".xhtml"):
				chapters = _read_html(text)
			else:
				chapters = _read_plain_text(text)
	except Exception as ex:
		se.print_error(f"Error reading source file: {ex}", plain_output=plain_output)
		return se.InvalidFileException.code

	if not chapters:
		se.print_error("No content found in source file.", plain_output=plain_output)
		return se.InvalidFileException.code

	# Load the chapter template
	with importlib.resources.files("se.data.templates").joinpath("chapter-template.xhtml").open("r", encoding="utf-8") as f:
		template = f.read()

	template = template.replace("LANG", args.language)

	# Write chapter files
	chapter_number = args.start_at
	written_files: list[Path] = []
	validation_errors: list[tuple[str, str]] = []

	for title, body_html in chapters:
		if not body_html.strip():
			continue

		# Strip OCR noise from body content
		body_html = strip_ocr_noise(body_html)

		# Skip if body is empty after noise removal
		if not body_html.strip():
			continue

		filename_format = args.filename_format.replace("%n", str(chapter_number))
		file_id = regex.sub(r"\.xhtml$", "", filename_format)

		xhtml = template.replace("ID", file_id)
		xhtml = xhtml.replace("NUMERAL", str(roman.toRoman(chapter_number)))

		if title:
			heading = f"<h2 epub:type=\"title\">{_escape_xml(title)}</h2>"
			section_content = f"{heading}\n\t\t\t\t{body_html}"
		else:
			section_content = body_html

		xhtml = xhtml.replace("TEXT", section_content)

		# Sanitize the complete XHTML (fixes bare '<', unclosed void elements)
		xhtml = sanitize_xhtml(xhtml)

		# Validate the generated XHTML before writing
		try:
			etree.fromstring(xhtml.encode("utf-8"))
		except etree.XMLSyntaxError as ex:
			validation_errors.append((filename_format, str(ex)))
			# Still write the file so the user can inspect and fix it,
			# but warn about it
			console.print(f"  [bold yellow]Warning:[/] Generated XHTML is not well-formed: [path]{filename_format}[/]")
			console.print(f"           {ex}")

		output_path = text_dir / filename_format
		with open(output_path, "w", encoding="utf-8") as f:
			f.write(xhtml)

		written_files.append(output_path)
		chapter_number += 1

	# Report results
	console.print(f"Imported {len(written_files)} chapter(s) from [path]{source_path.name}[/] into [path]{text_dir}[/].")
	if not plain_output:
		for f in written_files:
			console.print(f"  [path]{f.name}[/]")

	if validation_errors:
		console.print(f"\n[bold yellow]Warning:[/] {len(validation_errors)} file(s) have XHTML validation errors.")
		console.print(f"Run [bash]tl clean .[/] to attempt auto-repair, then check manually.")

	console.print(f"\nNext steps:")
	console.print(f"  tl clean {args.dest}")
	console.print(f"  tl typogrify {args.dest}")
	console.print(f"  tl semanticate {args.dest}")

	return 0
