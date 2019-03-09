#!/usr/bin/env python3
"""
Defines various functions useful for image processing tasks common to epubs.
"""

import subprocess
import shutil
import tempfile
import regex
import psutil
import se
import se.formatting


def render_mathml_to_png(mathml: str, output_filename: str) -> None:
	"""
	Render a string of MathML into a transparent PNG file.

	INPUTS
	mathml: A string of MathML
	output_filename: A filename to store PNG output to

	OUTPUTS
	A string of XHTML with soft hyphens inserted in words. The output is not guaranteed to be pretty-printed.
	"""

	firefox_path = shutil.which("firefox")
	convert_path = shutil.which("convert")

	if firefox_path is None:
		raise se.MissingDependencyException("Couldn’t locate firefox. Is it installed?")

	if convert_path is None:
		raise se.MissingDependencyException("Couldn’t locate imagemagick. Is it installed?")

	if "firefox" in (p.name() for p in psutil.process_iter()):
		raise se.FirefoxRunningException("Firefox is required, but it’s currently running. Stop all instances of Firefox and try again.")

	with tempfile.NamedTemporaryFile(mode="w+") as mathml_temp_file:
		with tempfile.NamedTemporaryFile(mode="w+", suffix=".png") as png_temp_file:
			mathml_temp_file.write("<!doctype html><html><head><meta charset=\"utf-8\"><title>MathML fragment</title></head><body>{}</body></html>".format(mathml))
			mathml_temp_file.seek(0)

			subprocess.call([firefox_path, "-screenshot", png_temp_file.name, "file://{}".format(mathml_temp_file.name)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

			subprocess.call([convert_path, png_temp_file.name, "-fuzz", "10%", "-transparent", "white", "-trim", output_filename])

def format_inkscape_svg(filename: str):
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

def remove_image_metadata(filename: str) -> None:
	"""
	Remove exif metadata from an image.

	INPUTS
	filename: A filename of an image

	OUTPUTS
	None.
	"""

	exiftool_path = shutil.which("exiftool")

	if exiftool_path is None:
		raise se.MissingDependencyException("Couldn’t locate exiftool. Is it installed?")

	subprocess.run([exiftool_path, "-overwrite_original", "-all=", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
