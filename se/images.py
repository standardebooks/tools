#!/usr/bin/env python3
"""
Defines various functions useful for image processing tasks common to epubs.
"""

import subprocess
from pathlib import Path
import shutil
import tempfile
import regex
import psutil
import se
import se.formatting


def render_mathml_to_png(mathml: str, output_filename: Path) -> None:
	"""
	Render a string of MathML into a transparent PNG file.

	INPUTS
	mathml: A string of MathML
	output_filename: A filename to store PNG output to

	OUTPUTS
	A string of XHTML with soft hyphens inserted in words. The output is not guaranteed to be pretty-printed.
	"""

	firefox_path = se.get_firefox_path()
	convert_path = shutil.which("convert")

	if convert_path is None:
		raise se.MissingDependencyException("Couldn’t locate imagemagick. Is it installed?")

	if "firefox" in (p.name() for p in psutil.process_iter()):
		raise se.FirefoxRunningException("Firefox is required, but it’s currently running. Stop all instances of Firefox and try again.")

	with tempfile.NamedTemporaryFile(mode="w+") as mathml_file:
		with tempfile.NamedTemporaryFile(mode="w+", suffix=".png") as png_file:
			mathml_file.write(f"<!doctype html><html><head><meta charset=\"utf-8\"><title>MathML fragment</title></head><body>{mathml}</body></html>")
			mathml_file.seek(0)

			subprocess.call([firefox_path, "-screenshot", png_file.name, f"file://{mathml_file.name}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

			subprocess.call([convert_path, png_file.name, "-fuzz", "10%", "-transparent", "white", "-trim", output_filename])

def format_inkscape_svg(filename: Path):
	"""
	Clean and format SVGs created by Inkscape, which have lots of useless metadata.

	INPUTS
	filename: A filename of an Inkkscape SVG

	OUTPUTS
	None.
	"""

	with open(filename, "r+", encoding="utf-8") as file:
		svg = file.read()

		# Time to clean up Inkscape's mess
		svg = regex.sub(r"id=\"[^\"]+?\"", "", svg)
		svg = regex.sub(r"<metadata[^>]*?>.*?</metadata>", "", svg, flags=regex.DOTALL)
		svg = regex.sub(r"<defs[^>]*?/>", "", svg)
		svg = regex.sub(r"xmlns:(dc|cc|rdf)=\"[^\"]*?\"", "", svg)

		# Inkscape includes CSS even though we've removed font information
		svg = regex.sub(r" style=\".*?\"", "", svg)

		svg = se.formatting.format_xhtml(svg)

		file.seek(0)
		file.write(svg)
		file.truncate()

def remove_image_metadata(filename: Path) -> None:
	"""
	Remove exif metadata from an image.

	INPUTS
	filename: A filename of an image

	OUTPUTS
	None.
	"""

	which_exiftool = shutil.which("exiftool")
	if which_exiftool:
		exiftool_path = Path(which_exiftool)
	else:
		raise se.MissingDependencyException("Couldn’t locate exiftool. Is it installed?")

	# Path arguments must be cast to string for Windows compatibility.
	subprocess.run([str(exiftool_path), "-overwrite_original", "-all=", str(filename)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
