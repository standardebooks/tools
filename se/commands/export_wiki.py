"""
This module implements the `tl export-wiki` command.

Exports an ebook's text and metadata as a single Markdown file suitable for
ingestion into the Tolstoy LLM wiki (Obsidian vault). The output includes
YAML frontmatter derived from the ebook's content.opf and the full text
converted from XHTML to Markdown with [[wikilinks]] ready to be woven in.
"""

import argparse
import json
from pathlib import Path

import regex
from lxml import etree
from natsort import natsorted

import se
import se.easy_xml
from se.se_epub import SeEpub
from se.xhtml_sanitize import sanitize_xhtml, strip_ocr_noise

console = se.init_console()

# OPF namespaces
OPF_NS = {
	"opf": "http://www.idpf.org/2007/opf",
	"dc": "http://purl.org/dc/elements/1.1/",
}

# Files to skip when reading text content
BOILERPLATE_FILES = {"colophon.xhtml", "imprint.xhtml", "uncopyright.xhtml", "titlepage.xhtml", "halftitlepage.xhtml", "toc.xhtml", "loi.xhtml"}


def _xhtml_to_markdown(xhtml: str, filename: str = "") -> tuple[str, str | None]:
	"""
	Convert SE XHTML body content to clean Markdown.

	Handles: paragraphs, headings, blockquotes, italics, bold, links,
	line breaks, poetry/verse blocks. Strips all other markup.

	Returns a tuple of (markdown_text, error_message_or_none).
	"""

	# Sanitize OCR-damaged XHTML before parsing (fixes bare '<', unclosed void elements)
	sanitized = sanitize_xhtml(xhtml)
	error_msg = None

	try:
		tree = etree.fromstring(sanitized.encode("utf-8"))
	except etree.XMLSyntaxError as ex:
		error_msg = f"File: {filename}. Exception: Couldn't parse XHTML file. Exception: {ex}"

		# Fall back to lenient HTML parser
		try:
			parser = etree.HTMLParser(encoding="utf-8")
			tree = etree.fromstring(sanitized.encode("utf-8"), parser)
		except Exception:
			# If even the HTML parser fails, strip tags manually
			text = regex.sub(r"<[^>]+>", "", xhtml).strip()
			return (strip_ocr_noise(text), error_msg)

	body = tree.find(".//{http://www.w3.org/1999/xhtml}body")
	if body is None:
		body = tree.find(".//body")
	if body is None:
		body = tree

	try:
		markdown = _element_to_markdown(body).strip()
	except Exception as ex:
		# The lenient HTML parser can produce trees with garbage elements
		# that cause unexpected errors during conversion. Fall back to
		# plain text extraction from the tree, then tag-stripping.
		if error_msg is None:
			error_msg = f"File: {filename}. Exception: Markdown conversion failed: {ex}"

		try:
			markdown = etree.tostring(body, method="text", encoding="unicode").strip()
		except Exception:
			markdown = regex.sub(r"<[^>]+>", "", xhtml).strip()

	return (strip_ocr_noise(markdown), error_msg)


def _safe_localname(tag) -> str:
	"""
	Extract the local name from an lxml tag, handling malformed tag names
	that the lenient HTML parser may produce from broken OCR text.
	"""

	if not isinstance(tag, str):
		return ""
	try:
		return etree.QName(tag).localname
	except ValueError:
		return ""


def _element_to_markdown(element: etree._Element, depth: int = 0) -> str:
	"""
	Recursively convert an lxml element tree to Markdown.
	"""

	tag = _safe_localname(element.tag)
	result = ""

	# Handle specific tags
	if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
		level = int(tag[1])
		prefix = "#" * level
		inner = _inner_text(element).strip()
		result += f"\n\n{prefix} {inner}\n\n"
		return result

	if tag == "p":
		inner = _inline_content(element).strip()
		if inner:
			result += f"\n\n{inner}\n"
		return result

	if tag == "blockquote":
		inner = _element_to_markdown(element, depth + 1).strip()
		# Prefix each line with >
		lines = inner.splitlines()
		quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in lines)
		result += f"\n\n{quoted}\n"
		return result

	if tag in ("ul", "ol"):
		for i, li in enumerate(element):
			li_tag = _safe_localname(li.tag)
			if li_tag == "li":
				prefix = f"{i + 1}." if tag == "ol" else "-"
				inner = _inline_content(li).strip()
				result += f"\n{prefix} {inner}"
		result += "\n"
		return result

	if tag == "hr":
		result += "\n\n---\n\n"
		return result

	if tag == "br":
		result += "  \n"
		return result

	# For section and other container elements, recurse into children
	if element.text:
		result += element.text

	for child in element:
		result += _element_to_markdown(child, depth)
		if child.tail:
			result += child.tail

	return result


def _inline_content(element: etree._Element) -> str:
	"""
	Convert inline element content to Markdown (handles em, strong, i, b, a, abbr, span).
	"""

	result = ""

	if element.text:
		result += element.text

	for child in element:
		tag = _safe_localname(child.tag)

		if tag in ("em", "i"):
			inner = _inline_content(child).strip()
			if inner:
				result += f"*{inner}*"
		elif tag in ("strong", "b"):
			inner = _inline_content(child).strip()
			if inner:
				result += f"**{inner}**"
		elif tag == "a":
			href = child.get("href", "")
			inner = _inline_content(child).strip()
			if href and inner:
				result += f"[{inner}]({href})"
			elif inner:
				result += inner
		elif tag == "br":
			result += "  \n"
		elif tag == "abbr":
			result += _inline_content(child)
		elif tag == "span":
			result += _inline_content(child)
		else:
			# Unknown inline element — just get text
			result += _inline_content(child)

		if child.tail:
			result += child.tail

	return result


def _inner_text(element: etree._Element) -> str:
	"""Get all text content from an element, stripping markup."""
	return etree.tostring(element, method="text", encoding="unicode")


def _read_opf_metadata(opf_path: Path) -> dict:
	"""
	Read metadata from content.opf and return a dict suitable for YAML frontmatter.
	"""

	with open(opf_path, "r", encoding="utf-8") as f:
		opf_xml = f.read()

	tree = etree.fromstring(opf_xml.encode("utf-8"))
	md = tree.find("opf:metadata", OPF_NS)
	if md is None:
		return {}

	def _text(xpath: str) -> str:
		el = md.find(xpath, OPF_NS)
		return el.text.strip() if el is not None and el.text else ""

	def _all_text(xpath: str) -> list[str]:
		return [el.text.strip() for el in md.findall(xpath, OPF_NS) if el.text]

	# Extract basic metadata
	title = _text("dc:title")
	authors = _all_text("dc:creator")
	description = _text("dc:description")
	language = _text("dc:language")
	subjects = _all_text("dc:subject")
	sources = _all_text("dc:source")

	# Try to get SE-specific metadata
	se_meta = {}
	for meta in md.findall("opf:meta", OPF_NS):
		prop = meta.get("property", "")
		if prop and meta.text:
			se_meta[prop] = meta.text.strip()

	# Build word count if available
	word_count = se_meta.get("se:word-count", "")

	return {
		"title": title,
		"authors": authors,
		"description": description,
		"language": language,
		"subjects": subjects,
		"sources": sources,
		"word_count": word_count,
		"long_description": se_meta.get("se:long-description", ""),
	}


def _read_spine_files(epub_dir: Path) -> list[Path]:
	"""
	Read the OPF spine and return text file paths in reading order.
	Falls back to natsorted file listing if spine parsing fails.
	"""

	opf_path = epub_dir / "src" / "epub" / "content.opf"
	text_dir = epub_dir / "src" / "epub" / "text"

	try:
		with open(opf_path, "r", encoding="utf-8") as f:
			opf_xml = f.read()

		tree = etree.fromstring(opf_xml.encode("utf-8"))

		# Build manifest id -> href map
		manifest = {}
		for item in tree.findall(".//opf:manifest/opf:item", OPF_NS):
			item_id = item.get("id", "")
			href = item.get("href", "")
			if href.startswith("text/") and href.endswith(".xhtml"):
				manifest[item_id] = href

		# Read spine in order
		spine_files = []
		for itemref in tree.findall(".//opf:spine/opf:itemref", OPF_NS):
			idref = itemref.get("idref", "")
			if idref in manifest:
				filepath = epub_dir / "src" / "epub" / manifest[idref]
				if filepath.exists() and filepath.name not in BOILERPLATE_FILES:
					spine_files.append(filepath)

		if spine_files:
			return spine_files

	except Exception:
		pass

	# Fallback: natsorted listing of text files
	if text_dir.exists():
		files = [f for f in text_dir.iterdir() if f.suffix == ".xhtml" and f.name not in BOILERPLATE_FILES]
		return natsorted(files, key=lambda p: p.name)

	return []


def _build_frontmatter(opf_meta: dict, ia_meta: dict | None, identifier: str) -> str:
	"""
	Build YAML frontmatter for the wiki export.
	"""

	lines = ["---"]

	# Core identity
	lines.append(f"id: {identifier}")
	lines.append(f"recordStatus: draft")
	lines.append(f'titleEn: "{opf_meta.get("title", "")}"')

	if opf_meta.get("authors"):
		if len(opf_meta["authors"]) == 1:
			lines.append(f'author: "{opf_meta["authors"][0]}"')
		else:
			lines.append("authors:")
			for a in opf_meta["authors"]:
				lines.append(f'  - "{a}"')

	if opf_meta.get("description"):
		lines.append(f'description: "{opf_meta["description"]}"')

	if opf_meta.get("language"):
		lines.append(f'language: {opf_meta["language"]}')

	if opf_meta.get("subjects"):
		lines.append("subjects:")
		for s in opf_meta["subjects"]:
			lines.append(f'  - "{s}"')

	if opf_meta.get("word_count"):
		lines.append(f"wordCount: {opf_meta['word_count']}")

	# Source information
	if opf_meta.get("sources"):
		lines.append("sources:")
		for s in opf_meta["sources"]:
			lines.append(f'  - "{s}"')

	# IA metadata if available
	if ia_meta:
		lines.append(f'iaIdentifier: "{ia_meta.get("ia_identifier", "")}"')
		lines.append(f'iaUrl: "{ia_meta.get("ia_url", "")}"')
		if ia_meta.get("date"):
			lines.append(f'publicationDate: "{ia_meta["date"]}"')
		if ia_meta.get("publisher"):
			lines.append(f'publisher: "{ia_meta["publisher"]}"')

	lines.append("---")
	return "\n".join(lines)


def export_wiki(plain_output: bool) -> int:
	"""
	Entry point for `tl export-wiki`.
	"""

	parser = argparse.ArgumentParser(
		description="Export an ebook's text and metadata as a single Markdown file for ingestion into the Tolstoy LLM wiki (Obsidian vault)."
	)
	parser.add_argument("directory", metavar="DIRECTORY", nargs="?", default=".", help="the ebook source directory to export (default: current directory)")
	parser.add_argument("-o", "--output", metavar="FILE", help="output file path (default: {title}.md in the ebook directory)")
	parser.add_argument("-i", "--id", dest="work_id", metavar="ID", help="canonical work ID slug (default: derived from directory name)")
	parser.add_argument("--no-frontmatter", action="store_true", help="omit YAML frontmatter, output text only")
	parser.add_argument("--chapters-as-headings", action="store_true", default=True, help="render each chapter file as a heading in the output (default: true)")
	args = parser.parse_args()

	ebook_dir = Path(args.directory).resolve()

	if not ebook_dir.exists():
		se.print_error(f"Directory not found: [path]{ebook_dir}[/].", plain_output=plain_output)
		return se.InvalidFileException.code

	opf_path = ebook_dir / "src" / "epub" / "content.opf"
	if not opf_path.exists():
		se.print_error(f"No [path]content.opf[/] found in [path]{ebook_dir}[/]. Is this an SE source directory?", plain_output=plain_output)
		return se.InvalidFileException.code

	# Read OPF metadata
	opf_meta = _read_opf_metadata(opf_path)

	# Check for IA metadata
	ia_meta = None
	ia_meta_path = ebook_dir / "ia-metadata.json"
	if ia_meta_path.exists():
		try:
			with open(ia_meta_path, "r", encoding="utf-8") as f:
				ia_meta = json.load(f)
		except Exception:
			pass

	# Determine work ID
	work_id = args.work_id
	if not work_id:
		# Try to derive from directory name (e.g., "leo-tolstoy_anna-karenina" → "anna-karenina")
		parts = ebook_dir.name.split("_")
		if len(parts) >= 2:
			# Skip author part(s) — take the title slug
			# Convention: author_title or author_title_translator
			work_id = parts[1]
		else:
			work_id = ebook_dir.name

	title = opf_meta.get("title", work_id)

	# Read spine files in order
	spine_files = _read_spine_files(ebook_dir)

	if not spine_files:
		se.print_error("No text files found in the ebook.", plain_output=plain_output)
		return se.InvalidFileException.code

	# Build the output
	output_parts: list[str] = []

	# Frontmatter
	if not args.no_frontmatter:
		output_parts.append(_build_frontmatter(opf_meta, ia_meta, work_id))

	# Long description as intro if available
	if opf_meta.get("long_description"):
		# Strip HTML from long description
		desc_text = regex.sub(r"<[^>]+>", "", opf_meta["long_description"]).strip()
		if desc_text:
			output_parts.append(f"\n{desc_text}\n")

	# Text zone marker
	output_parts.append("\n<!-- TEXT — source text, do not modify -->\n")

	# Convert each chapter
	error_files: list[str] = []

	for filepath in spine_files:
		try:
			with open(filepath, "r", encoding="utf-8") as f:
				xhtml = f.read()
		except Exception as ex:
			console.print(f"  [yellow]Warning:[/] Could not read {filepath.name}: {ex}")
			continue

		markdown, parse_error = _xhtml_to_markdown(xhtml, filename=filepath.name)

		if parse_error:
			se.print_error(parse_error, plain_output=plain_output)
			error_files.append(filepath.name)

		if markdown.strip():
			output_parts.append(markdown)

	# Join and clean up
	full_text = "\n".join(output_parts)

	# Normalize multiple blank lines
	full_text = regex.sub(r"\n{4,}", "\n\n\n", full_text)

	# Determine output path
	if args.output:
		output_path = Path(args.output).resolve()
	else:
		output_path = Path.cwd() / f"{title}.md"

	with open(output_path, "w", encoding="utf-8") as f:
		f.write(full_text)

	console.print(f"Exported to [path]{output_path}[/]")
	console.print(f"  Chapters: {len(spine_files)}")
	console.print(f"  Work ID:  {work_id}")

	if error_files:
		console.print(f"\n[bold yellow]Warning:[/] {len(error_files)} file(s) had XHTML parse errors (content was still extracted using fallback parser):")
		for ef in error_files:
			console.print(f"  [path]{ef}[/]")
		console.print(f"Run [bash]tl lint .[/] to check for structural issues, or fix the source files and re-export.")

	if not args.no_frontmatter:
		console.print(f"\nThe file includes YAML frontmatter and a TEXT zone marker.")
		console.print(f"Copy to [path]src/works/[/] in the website project and weave in [[wikilinks]].")

	return 0
