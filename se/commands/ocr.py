"""
This module implements the `tl ocr` command.

Re-OCR JP2 scans using Tesseract's LSTM engine, producing per-page text
files (and optionally hOCR) suitable for proofreading in the Korrektur.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _find_jp2_dir(project_dir: Path) -> Path | None:
	"""Find the *_jp2 directory inside _sources/."""
	sources_dir = project_dir / "_sources"
	if not sources_dir.exists():
		return None
	for d in sources_dir.rglob("*_jp2"):
		if d.is_dir():
			return d
	return None


def _ocr_dir_for(jp2_dir: Path) -> Path:
	"""Return the sibling _ocr directory for a _jp2 directory."""
	return jp2_dir.parent / jp2_dir.name.replace("_jp2", "_ocr")


def _text_to_xhtml(raw_text: str, page_num: int) -> str:
	"""Convert Tesseract plain text output to simple XHTML."""
	lines = raw_text.split("\n")

	# Group lines into paragraphs (blank lines separate paragraphs)
	paragraphs: list[str] = []
	current: list[str] = []
	for line in lines:
		stripped = line.strip()
		if stripped == "":
			if current:
				paragraphs.append(" ".join(current))
				current = []
		else:
			current.append(stripped)
	if current:
		paragraphs.append(" ".join(current))

	# Build XHTML body
	body_parts = []
	for para in paragraphs:
		# Escape XML entities
		para = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
		body_parts.append(f"\t\t<p>{para}</p>")

	body_html = "\n".join(body_parts)

	return f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
\t<head>
\t\t<title>Page {page_num}</title>
\t</head>
\t<body>
{body_html}
\t</body>
</html>
"""


def _process_one_page(
	jp2_path: Path,
	page_num: int,
	ocr_dir: Path,
	oem: int,
	dpi: int,
	lang: str,
	generate_hocr: bool,
	use_opj: bool,
) -> dict:
	"""OCR a single JP2 page. Returns a status dict."""
	padded = f"{page_num:04d}"
	out_xhtml = ocr_dir / f"{padded}.xhtml"
	out_txt = ocr_dir / f"{padded}.txt"
	out_hocr = ocr_dir / f"{padded}.hocr" if generate_hocr else None

	# Skip if already done
	if out_xhtml.exists() and out_xhtml.stat().st_size > 0:
		return {"page": page_num, "status": "skipped"}

	tmp_bmp = None
	try:
		# Step 1: Convert JP2 to BMP
		if use_opj:
			tmp_bmp = ocr_dir / f".tmp_{padded}.bmp"
			result = subprocess.run(
				["opj_decompress", "-i", str(jp2_path), "-o", str(tmp_bmp)],
				capture_output=True, text=True, timeout=60,
			)
			if result.returncode != 0:
				return {"page": page_num, "status": "error",
						"error": f"opj_decompress: {result.stderr.strip()[:200]}"}
			ocr_input = str(tmp_bmp)
		else:
			# Fallback: try Tesseract directly (works if Leptonica supports JP2)
			ocr_input = str(jp2_path)

		# Step 2: Run Tesseract for plain text
		result = subprocess.run(
			["tesseract", ocr_input, "stdout",
			 "-l", lang,
			 "--oem", str(oem),
			 "--dpi", str(dpi)],
			capture_output=True, text=True, timeout=120,
		)
		if result.returncode != 0:
			return {"page": page_num, "status": "error",
					"error": f"tesseract: {result.stderr.strip()[:200]}"}

		raw_text = result.stdout.strip()

		# Write XHTML (primary output for Korrektur)
		xhtml = _text_to_xhtml(raw_text, page_num)
		out_xhtml.write_text(xhtml, encoding="utf-8")

		# Also write plain text (useful for import-text and grep)
		out_txt.write_text(raw_text, encoding="utf-8")

		# Step 3: Optionally generate hOCR
		if generate_hocr and out_hocr:
			hocr_base = str(out_hocr).removesuffix(".hocr")
			subprocess.run(
				["tesseract", ocr_input, hocr_base,
				 "-l", lang,
				 "--oem", str(oem),
				 "--dpi", str(dpi),
				 "hocr"],
				capture_output=True, text=True, timeout=120,
			)

		return {"page": page_num, "status": "ok"}

	except subprocess.TimeoutExpired:
		return {"page": page_num, "status": "error", "error": "timeout"}
	except Exception as e:
		return {"page": page_num, "status": "error", "error": str(e)[:200]}
	finally:
		if tmp_bmp and tmp_bmp.exists():
			tmp_bmp.unlink()


def ocr(plain_output: bool) -> int:
	"""
	Entry point for `tl ocr`.
	"""

	parser = argparse.ArgumentParser(
		description="Re-OCR JP2 scans using Tesseract's LSTM engine. "
		"Produces per-page XHTML and plain text files for proofreading "
		"in the Korrektur or importing with `tl import-text`."
	)
	parser.add_argument(
		"directory",
		metavar="DIRECTORY",
		help="path to an ebook project directory (must contain _sources/ with a *_jp2 folder)",
	)
	parser.add_argument(
		"-o", "--output",
		metavar="DIR",
		help="output directory (default: sibling *_ocr directory next to the *_jp2 folder)",
	)
	parser.add_argument(
		"-j", "--jobs",
		type=int,
		default=os.cpu_count() or 4,
		help=f"number of parallel jobs (default: {os.cpu_count() or 4})",
	)
	parser.add_argument(
		"-s", "--start",
		type=int,
		default=1,
		help="start at this page number (default: 1)",
	)
	parser.add_argument(
		"-e", "--end",
		type=int,
		default=None,
		help="end at this page number (default: last page)",
	)
	parser.add_argument(
		"-l", "--language",
		default="eng",
		help="Tesseract language code (default: eng)",
	)
	parser.add_argument(
		"--dpi",
		type=int,
		default=300,
		help="DPI for Tesseract (default: 300)",
	)
	parser.add_argument(
		"--oem",
		type=int,
		default=1,
		choices=[0, 1, 2, 3],
		help="Tesseract OCR engine mode: 0=legacy, 1=LSTM (default), 2=both, 3=auto",
	)
	parser.add_argument(
		"--hocr",
		action="store_true",
		help="also generate hOCR files (slower, runs Tesseract twice per page)",
	)
	parser.add_argument(
		"--force",
		action="store_true",
		help="re-process pages even if output files already exist",
	)
	args = parser.parse_args()

	project_dir = Path(args.directory).resolve()
	if not project_dir.exists():
		print(f"Error: Directory not found: {project_dir}", file=sys.stderr)
		return 1

	# Find JP2 scans
	jp2_dir = _find_jp2_dir(project_dir)
	if not jp2_dir:
		print("Error: No *_jp2 directory found in _sources/.", file=sys.stderr)
		print("  Expected: <project>/_sources/**/*_jp2/", file=sys.stderr)
		return 1

	jp2_files = sorted(jp2_dir.glob("*.jp2"))
	total = len(jp2_files)
	if total == 0:
		print(f"Error: No .jp2 files found in {jp2_dir}", file=sys.stderr)
		return 1

	# Determine output directory
	if args.output:
		ocr_dir = Path(args.output).resolve()
	else:
		ocr_dir = _ocr_dir_for(jp2_dir)
	ocr_dir.mkdir(parents=True, exist_ok=True)

	# Check tools
	if not shutil.which("tesseract"):
		print("Error: tesseract not found.", file=sys.stderr)
		print("  macOS:  brew install tesseract", file=sys.stderr)
		print("  Linux:  sudo apt install tesseract-ocr", file=sys.stderr)
		return 1

	use_opj = bool(shutil.which("opj_decompress"))
	if not use_opj:
		print("Warning: opj_decompress not found. Trying Tesseract directly on JP2.")
		print("  For best results: brew install openjpeg")
		print()

	# Determine page range
	start_page = max(1, args.start)
	end_page = min(total, args.end) if args.end else total

	# If --force, remove existing output for the target range
	if args.force:
		for p in range(start_page, end_page + 1):
			for ext in (".xhtml", ".txt", ".hocr"):
				f = ocr_dir / f"{p:04d}{ext}"
				if f.exists():
					f.unlink()

	# Print summary
	print(f"Scan directory:  {jp2_dir}")
	print(f"Output:          {ocr_dir}")
	print(f"Total scans:     {total}")
	print(f"Page range:      {start_page}–{end_page}")
	print(f"Parallel jobs:   {args.jobs}")
	print(f"Tesseract:       {shutil.which('tesseract')}")
	print(f"Engine (OEM):    {args.oem} ({'LSTM' if args.oem == 1 else 'legacy' if args.oem == 0 else 'mixed'})")
	print(f"DPI:             {args.dpi}")
	print(f"Language:        {args.language}")
	print(f"hOCR:            {args.hocr}")
	print(f"JP2 decoder:     {'opj_decompress' if use_opj else 'direct (fallback)'}")
	print()

	# Process pages
	processed = 0
	skipped = 0
	errors = []

	def make_task(i: int):
		page_num = i + 1
		return _process_one_page(
			jp2_files[i], page_num, ocr_dir,
			args.oem, args.dpi, args.language,
			args.hocr, use_opj,
		)

	with ThreadPoolExecutor(max_workers=args.jobs) as executor:
		futures = {}
		for i in range(start_page - 1, end_page):
			future = executor.submit(make_task, i)
			futures[future] = i + 1  # page_num

		for future in as_completed(futures):
			page_num = futures[future]
			try:
				result = future.result()
			except Exception as e:
				result = {"page": page_num, "status": "error", "error": str(e)}

			if result["status"] == "ok":
				processed += 1
				print(f"  Page {page_num:4d}  OK")
			elif result["status"] == "skipped":
				skipped += 1
			else:
				errors.append(result)
				print(f"  Page {page_num:4d}  ERROR: {result.get('error', '?')}")

			done = processed + skipped + len(errors)
			if done % 50 == 0:
				print(f"  --- {done}/{end_page - start_page + 1} ---")

	# Combine into full text (same format as ocr-scans.sh for import-text compatibility)
	full_text_path = ocr_dir / "full-text.txt"
	print()
	print("Combining pages into full-text.txt...")
	with open(full_text_path, "w", encoding="utf-8") as f:
		for p in range(1, total + 1):
			txt_file = ocr_dir / f"{p:04d}.txt"
			if txt_file.exists():
				f.write(f"\n--- PAGE {p:04d} ---\n\n")
				f.write(txt_file.read_text(encoding="utf-8"))

	# Summary
	print()
	print("Done!")
	print(f"  Processed:     {processed}")
	print(f"  Skipped:       {skipped}")
	print(f"  Errors:        {len(errors)}")
	print(f"  Per-page XHTML: {ocr_dir}/")
	print(f"  Per-page text:  {ocr_dir}/")
	print(f"  Combined text:  {full_text_path}")
	if errors:
		print()
		print("Failed pages:")
		for e in errors:
			print(f"  Page {e['page']}: {e.get('error', '?')}")

	print()
	print("Next steps:")
	print(f"  1. Proofread in Korrektur:  python projects/korrektur/server.py {project_dir}")
	print(f"  2. Or import combined text:  tl import-text {full_text_path} -d <ebook-dir>")

	return 1 if errors else 0
