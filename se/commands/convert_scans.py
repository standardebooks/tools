"""
This module implements the `tl convert-scans` command.

Converts JP2 scans to JPEG (or PNG) and generates a self-contained
index.html scan browser for split-screen proofreading in Safari.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


_INDEX_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scan Browser — {title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #1a1a1a; color: #eee; display: flex; height: 100vh; overflow: hidden; }}
  #sidebar {{ width: 200px; min-width: 120px; overflow-y: auto; background: #111; padding: 0.5rem 0; flex-shrink: 0; }}
  #sidebar a {{ display: block; padding: 0.35rem 0.75rem; color: #bbb; text-decoration: none; font-size: 0.85rem; }}
  #sidebar a:hover, #sidebar a.active {{ background: #333; color: #fff; }}
  #main {{ flex: 1; overflow-y: auto; display: flex; flex-direction: column; align-items: center; padding: 1rem; gap: 0.5rem; }}
  #page-label {{ font-size: 0.9rem; color: #aaa; }}
  #scan-img {{ max-width: 100%; max-height: calc(100vh - 60px); object-fit: contain; border: 1px solid #444; }}
  #nav {{ display: flex; gap: 0.5rem; }}
  button {{ background: #333; color: #eee; border: 1px solid #555; border-radius: 4px; padding: 0.3rem 0.8rem; cursor: pointer; font-size: 0.85rem; }}
  button:hover {{ background: #444; }}
  button:disabled {{ opacity: 0.4; cursor: default; }}
</style>
</head>
<body>
<nav id="sidebar">
{sidebar_links}
</nav>
<main id="main">
  <div id="nav">
    <button id="btn-prev" onclick="navigate(-1)">&#8592; Prev</button>
    <span id="page-label">Page 1 of {total}</span>
    <button id="btn-next" onclick="navigate(1)">Next &#8594;</button>
  </div>
  <img id="scan-img" src="" alt="Scan">
</main>
<script>
const pages = {pages_json};
let current = 0;

function show(idx) {{
  if (idx < 0 || idx >= pages.length) return;
  current = idx;
  document.getElementById('scan-img').src = pages[idx].src;
  document.getElementById('page-label').textContent = 'Page ' + pages[idx].num + ' of {total}';
  document.getElementById('btn-prev').disabled = (current === 0);
  document.getElementById('btn-next').disabled = (current === pages.length - 1);
  document.querySelectorAll('#sidebar a').forEach((a, i) => a.classList.toggle('active', i === idx));
  document.querySelectorAll('#sidebar a')[idx].scrollIntoView({{block: 'nearest'}});
}}

function navigate(delta) {{ show(current + delta); }}

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') navigate(1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   navigate(-1);
}});

show(0);
</script>
</body>
</html>
"""


def _find_jp2_dir(project_dir: Path) -> Path | None:
	"""Find the *_jp2 directory inside _sources/."""
	sources_dir = project_dir / "_sources"
	if not sources_dir.exists():
		return None
	for d in sources_dir.rglob("*_jp2"):
		if d.is_dir():
			return d
	return None


def _jpeg_dir_for(jp2_dir: Path, fmt: str) -> Path:
	"""Return the sibling _jpeg (or _png) output directory."""
	suffix = "_jpeg" if fmt == "jpeg" else "_png"
	return jp2_dir.parent / jp2_dir.name.replace("_jp2", suffix)


def _convert_one(jp2_path: Path, out_path: Path, fmt: str, quality: int) -> dict:
	"""Convert a single JP2 to JPEG or PNG. Returns a status dict."""
	if out_path.exists() and out_path.stat().st_size > 0:
		return {"path": jp2_path, "status": "skipped"}

	# Try opj_decompress → ImageMagick pipeline first (highest quality)
	try:
		if shutil.which("opj_decompress") and shutil.which("convert"):
			tmp_bmp = out_path.with_suffix(".tmp.bmp")
			r1 = subprocess.run(
				["opj_decompress", "-i", str(jp2_path), "-o", str(tmp_bmp)],
				capture_output=True, timeout=60,
			)
			if r1.returncode == 0 and tmp_bmp.exists():
				if fmt == "jpeg":
					r2 = subprocess.run(
						["convert", str(tmp_bmp), "-quality", str(quality), str(out_path)],
						capture_output=True, timeout=30,
					)
				else:
					r2 = subprocess.run(
						["convert", str(tmp_bmp), str(out_path)],
						capture_output=True, timeout=30,
					)
				tmp_bmp.unlink(missing_ok=True)
				if r2.returncode == 0:
					return {"path": jp2_path, "status": "ok"}

		# Fallback: ImageMagick direct (needs JP2 codec support)
		if shutil.which("convert"):
			args = ["convert"]
			if fmt == "jpeg":
				args += ["-quality", str(quality)]
			args += [str(jp2_path), str(out_path)]
			r = subprocess.run(args, capture_output=True, timeout=60)
			if r.returncode == 0:
				return {"path": jp2_path, "status": "ok"}
			return {"path": jp2_path, "status": "error",
					"error": f"convert: {r.stderr.decode()[:200]}"}

		# Fallback: Python Pillow
		try:
			from PIL import Image  # type: ignore
			with Image.open(jp2_path) as img:
				if fmt == "jpeg":
					img.convert("RGB").save(str(out_path), "JPEG", quality=quality)
				else:
					img.save(str(out_path), "PNG")
			return {"path": jp2_path, "status": "ok"}
		except ImportError:
			return {"path": jp2_path, "status": "error",
					"error": "No converter found. Install imagemagick or pip install Pillow."}

	except subprocess.TimeoutExpired:
		return {"path": jp2_path, "status": "error", "error": "timeout"}
	except Exception as e:
		return {"path": jp2_path, "status": "error", "error": str(e)[:200]}


def _build_index(jpeg_dir: Path, images: list[Path], fmt: str, title: str) -> None:
	"""Generate a self-contained index.html scan browser."""
	ext = ".jpg" if fmt == "jpeg" else ".png"
	entries = []
	sidebar_lines = []
	for img in images:
		num = img.stem  # e.g. "0042"
		rel = img.name
		entries.append(f'{{"num": "{num}", "src": "{rel}"}}')
		sidebar_lines.append(
			f'  <a href="#" onclick="show({len(entries)-1}); return false;">Page {num}</a>'
		)

	pages_json = "[" + ", ".join(entries) + "]"
	sidebar_links = "\n".join(sidebar_lines)

	html = _INDEX_HTML_TEMPLATE.format(
		title=title,
		total=len(images),
		pages_json=pages_json,
		sidebar_links=sidebar_links,
	)
	(jpeg_dir / "index.html").write_text(html, encoding="utf-8")


def convert_scans(plain_output: bool) -> int:
	"""
	Entry point for `tl convert-scans`.
	"""

	parser = argparse.ArgumentParser(
		description="Convert JP2 scans to JPEG (or PNG) and generate a self-contained "
		"index.html scan browser for split-screen proofreading. "
		"Open index.html in Safari while editing OCR files in VS Code."
	)
	parser.add_argument(
		"directory",
		metavar="DIRECTORY",
		help="path to an ebook project directory (must contain _sources/ with a *_jp2 folder)",
	)
	parser.add_argument(
		"-f", "--format",
		choices=["jpeg", "png"],
		default="jpeg",
		help="output image format (default: jpeg)",
	)
	parser.add_argument(
		"-q", "--quality",
		type=int,
		default=85,
		metavar="1-100",
		help="JPEG quality 1–100 (default: 85, ignored for PNG)",
	)
	parser.add_argument(
		"-o", "--output",
		metavar="DIR",
		help="output directory (default: sibling *_jpeg/*_png next to the *_jp2 folder)",
	)
	parser.add_argument(
		"--force",
		action="store_true",
		help="re-convert files that already exist in the output directory",
	)
	parser.add_argument(
		"--no-index",
		action="store_true",
		help="skip generating index.html",
	)
	args = parser.parse_args()

	project_dir = Path(args.directory).resolve()
	if not project_dir.exists():
		print(f"Error: Directory not found: {project_dir}", file=sys.stderr)
		return 1

	jp2_dir = _find_jp2_dir(project_dir)
	if not jp2_dir:
		print("Error: No *_jp2 directory found in _sources/.", file=sys.stderr)
		print("  Expected: <project>/_sources/**/*_jp2/", file=sys.stderr)
		return 1

	jp2_files = sorted(jp2_dir.glob("*.jp2"))
	if not jp2_files:
		print(f"Error: No .jp2 files found in {jp2_dir}", file=sys.stderr)
		return 1

	out_dir = Path(args.output).resolve() if args.output else _jpeg_dir_for(jp2_dir, args.format)
	out_dir.mkdir(parents=True, exist_ok=True)

	ext = ".jpg" if args.format == "jpeg" else ".png"
	title = project_dir.name

	print(f"Source JP2:   {jp2_dir}")
	print(f"Output:       {out_dir}")
	print(f"Format:       {args.format.upper()}" + (f" quality={args.quality}" if args.format == "jpeg" else ""))
	print(f"Total pages:  {len(jp2_files)}")
	print()

	if args.force:
		for f in out_dir.glob(f"*{ext}"):
			f.unlink()

	ok = skipped = 0
	errors = []

	for jp2 in jp2_files:
		out_path = out_dir / (jp2.stem + ext)
		result = _convert_one(jp2, out_path, args.format, args.quality)
		if result["status"] == "ok":
			ok += 1
			if not plain_output:
				print(f"  {jp2.name}  →  {out_path.name}")
		elif result["status"] == "skipped":
			skipped += 1
		else:
			errors.append(result)
			print(f"  ERROR {jp2.name}: {result.get('error', '?')}", file=sys.stderr)

	# Generate index.html
	if not args.no_index:
		converted = sorted(out_dir.glob(f"*{ext}"))
		if converted:
			_build_index(out_dir, converted, args.format, title)
			print()
			print(f"Scan browser: {out_dir / 'index.html'}")

	print()
	print(f"Done.  Converted: {ok}  Skipped: {skipped}  Errors: {len(errors)}")

	if not args.no_index:
		print()
		print("Open in Safari for split-screen proofreading:")
		print(f"  open {out_dir / 'index.html'}")

	return 1 if errors else 0
