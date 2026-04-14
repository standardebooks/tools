"""
This module implements the `tl merge-pages` command.

Combines per-page OCR files into chapter XHTML files, guided by
a page-map.json that defines which scan pages belong to which chapter.
"""

import argparse
import json
import re
import sys
from pathlib import Path


XHTML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-GB">
\t<head>
\t\t<title>{title}</title>
\t\t<link href="../css/core.css" rel="stylesheet" type="text/css"/>
\t\t<link href="../css/local.css" rel="stylesheet" type="text/css"/>
\t</head>
\t<body epub:type="bodymatter">
\t\t<section id="{section_id}" epub:type="chapter">
{body}
\t\t</section>
\t</body>
</html>
"""


def _extract_body(xhtml: str) -> str:
	"""Extract the inner content of <body> from an XHTML string."""
	match = re.search(r"<body[^>]*>([\s\S]*)</body>", xhtml, re.IGNORECASE)
	if not match:
		return ""
	return match.group(1).strip()


def _find_ocr_dir(project_dir: Path) -> Path | None:
	"""Find the _ocr directory in _sources/."""
	sources_dir = project_dir / "_sources"
	if not sources_dir.exists():
		return None
	for d in sources_dir.rglob("*_ocr"):
		if d.is_dir():
			return d
	return None


def _chapter_title_from_filename(filename: str) -> str:
	"""Derive a human-readable title from a chapter filename."""
	name = filename.replace(".xhtml", "")
	if name.startswith("chapter-"):
		num = name.replace("chapter-", "")
		return f"Chapter {num}"
	return name.replace("-", " ").title()


def _section_id_from_filename(filename: str) -> str:
	"""Derive a section ID from a chapter filename."""
	return filename.replace(".xhtml", "")


def merge_pages(plain_output: bool) -> int:
	"""
	Entry point for `tl merge-pages`.
	"""

	parser = argparse.ArgumentParser(
		description="Combine per-page OCR files into chapter XHTML files, "
		"guided by page-map.json. Use after proofreading individual pages "
		"in the Korrektur."
	)
	parser.add_argument(
		"directory",
		metavar="DIRECTORY",
		help="path to an ebook project directory",
	)
	parser.add_argument(
		"-c", "--chapter",
		metavar="FILE",
		help="merge only this chapter (e.g. chapter-2.xhtml). Default: all chapters.",
	)
	parser.add_argument(
		"-o", "--output",
		metavar="DIR",
		help="output directory for merged XHTML (default: src/epub/text/)",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="show what would be merged without writing files",
	)
	parser.add_argument(
		"--diff",
		action="store_true",
		help="show a diff against existing chapter files instead of overwriting",
	)
	args = parser.parse_args()

	project_dir = Path(args.directory).resolve()
	if not project_dir.exists():
		print(f"Error: Directory not found: {project_dir}", file=sys.stderr)
		return 1

	# Load page map
	pagemap_path = project_dir / "page-map.json"
	if not pagemap_path.exists():
		print(f"Error: page-map.json not found in {project_dir}", file=sys.stderr)
		return 1

	pagemap = json.loads(pagemap_path.read_text(encoding="utf-8"))

	# Find OCR directory
	ocr_dir = _find_ocr_dir(project_dir)
	if not ocr_dir:
		print("Error: No *_ocr directory found in _sources/.", file=sys.stderr)
		print("  Run `tl ocr` first to generate per-page OCR files.", file=sys.stderr)
		return 1

	# Determine output directory
	if args.output:
		out_dir = Path(args.output).resolve()
	else:
		out_dir = project_dir / "src" / "epub" / "text"
	out_dir.mkdir(parents=True, exist_ok=True)

	# Filter chapters
	chapters = {}
	for filename, mapping in pagemap.items():
		if not isinstance(mapping, dict):
			continue
		if mapping.get("startPage") is None:
			continue
		if args.chapter and filename != args.chapter:
			continue
		chapters[filename] = mapping

	if not chapters:
		if args.chapter:
			print(f"Error: Chapter '{args.chapter}' not found in page-map.json", file=sys.stderr)
		else:
			print("Error: No chapters with page mappings found in page-map.json", file=sys.stderr)
		return 1

	errors = 0

	for filename, mapping in sorted(chapters.items()):
		start = mapping["startPage"]
		end = mapping["endPage"]
		title = _chapter_title_from_filename(filename)
		section_id = _section_id_from_filename(filename)

		# Collect body content from per-page OCR files
		page_bodies = []
		missing_pages = []

		for page_num in range(start, end + 1):
			ocr_file = ocr_dir / f"{page_num:04d}.xhtml"
			if not ocr_file.exists():
				missing_pages.append(page_num)
				continue

			content = ocr_file.read_text(encoding="utf-8")
			body = _extract_body(content)
			if body:
				# Add a page marker comment for reference
				page_bodies.append(f"\t\t\t<!-- page {page_num} -->")
				# Re-indent body content to fit inside <section>
				for line in body.split("\n"):
					stripped = line.strip()
					if stripped:
						page_bodies.append(f"\t\t\t{stripped}")

		if missing_pages:
			print(f"  Warning: {filename}: missing OCR for pages {missing_pages}")

		if not page_bodies:
			print(f"  Skipping {filename}: no OCR content found")
			errors += 1
			continue

		# Build the merged XHTML
		body_text = "\n".join(page_bodies)
		merged = XHTML_TEMPLATE.format(
			title=title,
			section_id=section_id,
			body=body_text,
		)

		if args.dry_run:
			page_count = end - start + 1
			print(f"  {filename}: pages {start}-{end} ({page_count} pages, {len(page_bodies)} content lines)")
			continue

		if args.diff:
			# Show diff against existing file
			existing_path = out_dir / filename
			if existing_path.exists():
				import difflib
				existing = existing_path.read_text(encoding="utf-8").splitlines()
				new = merged.splitlines()
				diff = difflib.unified_diff(
					existing, new,
					fromfile=f"existing/{filename}",
					tofile=f"merged/{filename}",
					lineterm="",
				)
				diff_lines = list(diff)
				if diff_lines:
					print(f"\n--- {filename} ---")
					for line in diff_lines[:100]:  # Cap output
						print(line)
					if len(diff_lines) > 100:
						print(f"  ... ({len(diff_lines) - 100} more lines)")
				else:
					print(f"  {filename}: no differences")
			else:
				print(f"  {filename}: no existing file to diff against")
			continue

		# Write merged file
		out_path = out_dir / filename
		out_path.write_text(merged, encoding="utf-8")
		page_count = end - start + 1
		print(f"  {filename}: merged {page_count} pages ({len(merged)} bytes)")

	return 1 if errors else 0
