"""
This module implements the `tl ia-import` command.

Downloads a text from Internet Archive by ID or URL, scaffolds an ebook
project with `create-draft --offline`, and imports the text into chapter
files using import-text logic.
"""

import argparse
import json
import tempfile
from pathlib import Path

import regex
import requests

from lxml import etree

import se

console = se.init_console()

# File format preferences — ordered by typical quality
FORMAT_PREFERENCES = [
	("DjVuTXT", "_djvu.txt", "OCR text (DjVu)"),
	("EPUB", ".epub", "EPUB ebook"),
	("Text", ".txt", "Plain text"),
	("Animated GIF", None, None),  # skip
]

# Formats we can import, in display order
IMPORTABLE_FORMATS = {
	"DjVuTXT": "OCR text from DjVu — always available, may have OCR noise",
	"Text": "Plain text — cleaner when available",
	"EPUB": "EPUB ebook — cleanest but not always present",
}


def _parse_ia_identifier(source: str) -> str:
	"""
	Extract an Internet Archive identifier from a URL or bare ID.

	Handles:
	- https://archive.org/details/leotolstoyhislif00biriiala
	- https://archive.org/details/leotolstoyhislif00biriiala/page/n5/mode/2up
	- archive.org/details/leotolstoyhislif00biriiala
	- leotolstoyhislif00biriiala
	"""

	# Strip whitespace
	source = source.strip()

	# Try to extract from URL
	match = regex.search(r"archive\.org/details/([^/\s?#]+)", source)
	if match:
		return match.group(1)

	# If no URL pattern found, treat as bare identifier (alphanumeric + hyphens + underscores)
	if regex.match(r"^[\w\-]+$", source):
		return source

	raise se.InvalidInputException(f"Could not parse Internet Archive identifier from: {source}")


def _fetch_metadata(identifier: str) -> dict:
	"""
	Fetch item metadata from the Internet Archive Metadata API.
	Returns the full JSON response.
	"""

	url = f"https://archive.org/metadata/{identifier}"
	response = requests.get(url, timeout=30, headers={"User-Agent": "tolstoy.life ebook toolset <https://tolstoy.life/>"})
	response.raise_for_status()
	return response.json()


def _get_importable_files(metadata: dict) -> list[dict]:
	"""
	Extract the list of files that we can import from the metadata response.
	Returns a list of dicts with 'name', 'format', 'size', and 'description'.
	"""

	files = metadata.get("files", [])
	importable = []

	for f in files:
		fmt = f.get("format", "")
		name = f.get("name", "")
		size = int(f.get("size", 0))

		if fmt in IMPORTABLE_FORMATS:
			importable.append({
				"name": name,
				"format": fmt,
				"size": size,
				"description": IMPORTABLE_FORMATS[fmt],
			})

	return importable


def _download_file(identifier: str, filename: str, dest_path: Path) -> Path:
	"""
	Download a file from Internet Archive.
	URL pattern: https://archive.org/download/{identifier}/{filename}
	"""

	url = f"https://archive.org/download/{identifier}/{filename}"
	response = requests.get(url, timeout=120, stream=True, headers={"User-Agent": "tolstoy.life ebook toolset <https://tolstoy.life/>"})
	response.raise_for_status()

	output = dest_path / filename
	with open(output, "wb") as f:
		for chunk in response.iter_content(chunk_size=8192):
			f.write(chunk)

	return output


def _format_size(size_bytes: int) -> str:
	"""Format a byte count as a human-readable string."""
	if size_bytes < 1024:
		return f"{size_bytes} B"
	elif size_bytes < 1024 * 1024:
		return f"{size_bytes / 1024:.1f} KB"
	else:
		return f"{size_bytes / (1024 * 1024):.1f} MB"


def _extract_ia_metadata(metadata: dict) -> dict:
	"""
	Extract useful metadata fields from the IA metadata response.
	Returns a dict with title, creator, date, language, description, subjects.
	"""

	md = metadata.get("metadata", {})

	# IA fields can be strings or lists
	def _as_str(val: str | list | None) -> str:
		if val is None:
			return ""
		if isinstance(val, list):
			return val[0] if val else ""
		return str(val)

	def _as_list(val: str | list | None) -> list[str]:
		if val is None:
			return []
		if isinstance(val, str):
			return [val]
		return [str(v) for v in val]

	return {
		"title": _as_str(md.get("title")),
		"creator": _as_list(md.get("creator")),
		"date": _as_str(md.get("date")),
		"language": _as_list(md.get("language")),
		"description": _as_str(md.get("description")),
		"subjects": _as_list(md.get("subject")),
		"publisher": _as_str(md.get("publisher")),
		"identifier": _as_str(md.get("identifier")),
		"ia_url": f"https://archive.org/details/{_as_str(md.get('identifier'))}",
	}


def ia_import(plain_output: bool) -> int:
	"""
	Entry point for `tl ia-import`.
	"""

	parser = argparse.ArgumentParser(
		description="Download a text from Internet Archive and create a tolstoy.life ebook project. Accepts an IA identifier or a full archive.org URL."
	)
	parser.add_argument("source", metavar="ID_OR_URL", help="an Internet Archive identifier (e.g., leotolstoyhislif00biriiala) or a full archive.org URL")
	parser.add_argument("-a", "--author", dest="author", nargs="+", help="override the author name(s) detected from IA metadata")
	parser.add_argument("-t", "--title", dest="title", help="override the title detected from IA metadata")
	parser.add_argument("-r", "--translator", dest="translator", nargs="+", help="translator name(s) for the ebook")
	parser.add_argument("-l", "--language", metavar="LANG", type=str, default="en-US", help="BCP 47 language tag for the text (default: en-US)")
	parser.add_argument("-o", "--output-dir", metavar="DIRECTORY", default=".", help="directory to create the ebook project in (default: current directory)")
	parser.add_argument("-f", "--format", dest="source_format", metavar="FORMAT", choices=["djvu", "text", "epub"], help="source format to download: djvu, text, or epub (default: show available and prompt)")
	parser.add_argument("--list-formats", action="store_true", help="list available formats and exit without downloading")
	args = parser.parse_args()

	# Parse the IA identifier
	try:
		identifier = _parse_ia_identifier(args.source)
	except se.InvalidInputException as ex:
		se.print_error(str(ex), plain_output=plain_output)
		return se.InvalidInputException.code

	console.print(f"Fetching metadata for [bold]{identifier}[/bold] from Internet Archive...")

	# Fetch metadata
	try:
		metadata = _fetch_metadata(identifier)
	except requests.HTTPError as ex:
		if ex.response is not None and ex.response.status_code == 404:
			se.print_error(f"Item not found on Internet Archive: [url]https://archive.org/details/{identifier}[/]", plain_output=plain_output)
		else:
			se.print_error(f"Error fetching metadata: {ex}", plain_output=plain_output)
		return se.RemoteCommandErrorException.code
	except requests.RequestException as ex:
		se.print_error(f"Network error: {ex}", plain_output=plain_output)
		return se.RemoteCommandErrorException.code

	# Extract metadata
	ia_meta = _extract_ia_metadata(metadata)

	title = args.title or ia_meta["title"]
	authors = args.author or ia_meta["creator"]

	if not title:
		se.print_error("Could not detect title from IA metadata. Use [bash]--title[/] to specify.", plain_output=plain_output)
		return se.InvalidInputException.code

	if not authors:
		se.print_error("Could not detect author from IA metadata. Use [bash]--author[/] to specify.", plain_output=plain_output)
		return se.InvalidInputException.code

	# Display metadata
	console.print()
	console.print(f"  Title:    [bold]{title}[/bold]")
	console.print(f"  Author:   {', '.join(authors)}")
	if ia_meta["date"]:
		console.print(f"  Date:     {ia_meta['date']}")
	if ia_meta["publisher"]:
		console.print(f"  Publisher: {ia_meta['publisher']}")
	console.print(f"  URL:      {ia_meta['ia_url']}")
	console.print()

	# Find importable files
	importable = _get_importable_files(metadata)

	if not importable:
		se.print_error("No importable text files found for this item. Available formats may not include text, EPUB, or DjVu.", plain_output=plain_output)
		return se.InvalidInputException.code

	# Display available formats
	console.print("Available formats:")
	format_map: dict[str, dict] = {}
	for i, f in enumerate(importable, 1):
		label = f["format"].lower().replace("djvutxt", "djvu")
		format_map[label] = f
		console.print(f"  [{i}] {f['format']:10s} {_format_size(f['size']):>10s}  — {f['description']}")
	console.print()

	if args.list_formats:
		return 0

	# Select format
	selected: dict | None = None

	if args.source_format:
		# Map user choice to IA format name
		choice_map = {"djvu": "DjVuTXT", "text": "Text", "epub": "EPUB"}
		target_fmt = choice_map.get(args.source_format, "")
		for f in importable:
			if f["format"] == target_fmt:
				selected = f
				break
		if not selected:
			se.print_error(f"Requested format [bash]{args.source_format}[/] not available for this item.", plain_output=plain_output)
			return se.InvalidInputException.code
	else:
		# Interactive: prompt user
		while selected is None:
			try:
				choice = input("Select format number (or 'q' to quit): ").strip()
			except (EOFError, KeyboardInterrupt):
				return 0

			if choice.lower() == "q":
				return 0

			try:
				idx = int(choice) - 1
				if 0 <= idx < len(importable):
					selected = importable[idx]
				else:
					console.print("  Invalid number, try again.")
			except ValueError:
				# Try matching by format name
				for f in importable:
					label = f["format"].lower().replace("djvutxt", "djvu")
					if choice.lower() == label:
						selected = f
						break
				if not selected:
					console.print("  Invalid choice, try again.")

	console.print(f"Downloading [bold]{selected['name']}[/bold] ({_format_size(selected['size'])})...")

	# Download to a temp directory
	with tempfile.TemporaryDirectory() as tmp_dir:
		tmp_path = Path(tmp_dir)

		try:
			downloaded = _download_file(identifier, selected["name"], tmp_path)
		except requests.RequestException as ex:
			se.print_error(f"Download failed: {ex}", plain_output=plain_output)
			return se.RemoteCommandErrorException.code

		console.print(f"Downloaded to temporary file.")

		# Determine file extension for import-text
		suffix = downloaded.suffix.lower()
		if suffix not in (".txt", ".md", ".html", ".htm", ".xhtml", ".epub"):
			# DjVu text files sometimes have compound extensions
			if "_djvu.txt" in downloaded.name:
				suffix = ".txt"

		# Build the ebook directory name (SE-style slug)
		author_slug = "_".join(a.lower().replace(" ", "-") for a in authors)
		title_slug = regex.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
		if args.translator:
			translator_slug = "_".join(t.lower().replace(" ", "-") for t in args.translator)
			dir_name = f"{author_slug}_{title_slug}_{translator_slug}"
		else:
			dir_name = f"{author_slug}_{title_slug}"

		output_dir = Path(args.output_dir).resolve()
		ebook_dir = output_dir / dir_name

		if ebook_dir.exists():
			console.print(f"[bold yellow]Warning:[/] Directory [path]{ebook_dir}[/] already exists. Importing into existing project.")
		else:
			# Scaffold the ebook project
			console.print(f"Scaffolding ebook project: [path]{dir_name}[/]")

			from se.commands.create_draft import create_draft as _create_draft
			import sys as _sys

			# Build argv for create-draft
			create_draft_args = ["create-draft", "--author"]
			create_draft_args.extend(authors)
			create_draft_args.extend(["--title", title, "--offline"])
			if args.translator:
				create_draft_args.extend(["--translator"])
				create_draft_args.extend(args.translator)

			# Save and restore sys.argv
			old_argv = _sys.argv
			old_cwd = Path.cwd()

			try:
				import os
				os.chdir(output_dir)
				_sys.argv = create_draft_args
				result = _create_draft(plain_output)
				if result != 0:
					se.print_error("Failed to scaffold ebook project.", plain_output=plain_output)
					return result
			finally:
				_sys.argv = old_argv
				os.chdir(old_cwd)

			# Find the created directory (create-draft makes its own dir name)
			# Look for the most recently created directory in output_dir
			if not ebook_dir.exists():
				# create-draft may have used a different name format
				candidates = sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
				for c in candidates:
					if c.is_dir() and not c.name.startswith("."):
						ebook_dir = c
						break

		# Import the text
		text_dir = ebook_dir / "src" / "epub" / "text"
		if not text_dir.exists():
			se.print_error(f"Could not find [path]src/epub/text/[/] in [path]{ebook_dir}[/].", plain_output=plain_output)
			return se.InvalidFileException.code

		console.print(f"Importing text into [path]{ebook_dir.name}[/]...")

		from se.commands.import_text import import_text as _import_text
		import sys as _sys

		old_argv = _sys.argv
		try:
			_sys.argv = ["import-text", str(downloaded), "-d", str(ebook_dir), "-l", args.language]
			result = _import_text(plain_output)
			if result != 0:
				return result
		finally:
			_sys.argv = old_argv

		# Write IA metadata as a note in the project
		ia_note_path = ebook_dir / "ia-metadata.json"
		with open(ia_note_path, "w", encoding="utf-8") as f:
			json.dump({
				"ia_identifier": identifier,
				"ia_url": ia_meta["ia_url"],
				"source_file": selected["name"],
				"source_format": selected["format"],
				"title": title,
				"authors": authors,
				"date": ia_meta["date"],
				"publisher": ia_meta["publisher"],
				"language": ia_meta["language"],
				"subjects": ia_meta["subjects"],
			}, f, indent="\t", ensure_ascii=False)

		# ---------------------------------------------------------------
		# Post-import validation: check all generated XHTML files
		# ---------------------------------------------------------------
		text_dir = ebook_dir / "src" / "epub" / "text"
		xhtml_errors: list[tuple[str, str]] = []
		chapter_count = 0
		empty_chapters: list[str] = []

		if text_dir.exists():
			for xhtml_file in sorted(text_dir.glob("chapter-*.xhtml")):
				chapter_count += 1
				try:
					content = xhtml_file.read_text(encoding="utf-8")
					etree.fromstring(content.encode("utf-8"))

					# Check for essentially empty chapters (only whitespace in section)
					body_match = regex.search(r"<section[^>]*>(.*?)</section>", content, flags=regex.DOTALL)
					if body_match and not body_match.group(1).strip():
						empty_chapters.append(xhtml_file.name)

				except etree.XMLSyntaxError as ex:
					xhtml_errors.append((xhtml_file.name, str(ex)))

		# ---------------------------------------------------------------
		# Report results
		# ---------------------------------------------------------------
		console.print()
		console.print(f"[bold green]Done![/] Ebook project created at [path]{ebook_dir}[/]")
		console.print(f"  Chapters imported: {chapter_count}")

		if xhtml_errors:
			console.print(f"\n[bold red]XHTML validation errors ({len(xhtml_errors)}):[/]")
			for filename, err in xhtml_errors:
				console.print(f"  [path]{filename}[/]: {err}")
			console.print(f"\nThese files need manual repair before [bash]tl build[/] or [bash]tl export-wiki[/] will work correctly.")

		if empty_chapters:
			console.print(f"\n[bold yellow]Empty chapters ({len(empty_chapters)}):[/]")
			for ec in empty_chapters[:10]:
				console.print(f"  [path]{ec}[/]")
			if len(empty_chapters) > 10:
				console.print(f"  ... and {len(empty_chapters) - 10} more")
			console.print(f"These likely correspond to images, blank pages, or boilerplate that was filtered out.")

		# ---------------------------------------------------------------
		# SE workflow guidance — follows the Standard Ebooks step-by-step
		# ---------------------------------------------------------------
		console.print()
		console.print(f"IA source: {ia_meta['ia_url']}")
		console.print()
		console.print("[bold]SE production pipeline — next steps:[/]")
		console.print()
		console.print(f"  [bold]Phase 2: Clean and split[/]")
		console.print(f"    cd {ebook_dir.name}")
		console.print(f"    tl clean .")
		console.print(f"    # Review chapter structure — IA imports often split by page, not by chapter.")
		console.print(f"    # You may need to merge files or re-split at actual chapter boundaries.")
		console.print()
		console.print(f"  [bold]Phase 3: Typography and semantics[/]")
		console.print(f"    tl typogrify .          # smart quotes, dashes, ellipses")
		console.print(f"    git diff                 # review changes — watch for elision vs. quotes")
		console.print(f"    tl semanticate .         # auto-add epub semantic markup")
		console.print(f"    # Manual: tag foreign languages (xml:lang), abbreviations, verse, letters")
		console.print()
		console.print(f"  [bold]Phase 4: Build and proofread[/]")
		console.print(f"    tl build-title .")
		console.print(f"    tl build-manifest .")
		console.print(f"    tl build-spine .")
		console.print(f"    tl build-toc .")
		console.print(f"    tl lint .                # check for structural errors")
		console.print(f"    tl build --output-dir=$HOME/dist/ .   # build and proofread on device")
		console.print()
		console.print(f"  [bold]Phase 5: Cover and metadata[/]")
		console.print(f"    # Find public domain cover art, complete content.opf, colophon, imprint")
		console.print()
		console.print(f"  [bold]Wiki export (can be done at any stage):[/]")
		console.print(f"    tl export-wiki           # export text + metadata as Obsidian Markdown")

	return 0
