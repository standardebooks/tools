#!/usr/bin/env python3
"""
Defines various functions useful for image processing tasks common to epubs.
"""

from pathlib import Path
import tempfile

import regex
from PIL import Image, ImageMath

import se
import se.formatting


def _color_to_alpha(image: Image, color=None) -> Image:
	"""
	Implements GIMP's color to alpha algorithm.
	See https://stackoverflow.com/a/1617909
	GPLv3: http://bazaar.launchpad.net/~stani/phatch/trunk/annotate/head:/phatch/actions/color_to_alpha.py#L50

	INPUTS
	image: A PIL image to work on
	color: A 4-tuple (R, G, B, A) value as the color to change to alpha

	OUTPUTS
	A string of XML representing the new SVG
	"""

	image = image.convert("RGBA")

	color = list(map(float, color))
	img_bands = [band.convert("F") for band in image.split()]

	# Find the maximum difference rate between source and color. I had to use two
	# difference functions because ImageMath.eval only evaluates the expression
	# once.
	alpha = ImageMath.eval(
		"""float(
		    max(
		        max(
		            max(
		                difference1(red_band, cred_band),
		                difference1(green_band, cgreen_band)
		            ),
		            difference1(blue_band, cblue_band)
		        ),
		        max(
		            max(
		                difference2(red_band, cred_band),
		                difference2(green_band, cgreen_band)
		            ),
		            difference2(blue_band, cblue_band)
		        )
		    )
		)""",
		difference1=lambda source, color: (source - color) / (255.0 - color),
		difference2=lambda source, color: (color - source) / color,
		red_band=img_bands[0],
		green_band=img_bands[1],
		blue_band=img_bands[2],
		cred_band=color[0],
		cgreen_band=color[1],
		cblue_band=color[2]
	)

	# Calculate the new image colors after the removal of the selected color
	new_bands = [
		ImageMath.eval(
			"convert((image - color) / alpha + color, 'L')",
			image=img_bands[i],
			color=color[i],
			alpha=alpha
		)
		for i in range(3)
	]

	# Add the new alpha band
	new_bands.append(ImageMath.eval(
		"convert(alpha_band * alpha, 'L')",
		alpha=alpha,
		alpha_band=img_bands[3]
	))

	new_image = Image.merge("RGBA", new_bands)

	background = Image.new("RGB", new_image.size, (0, 0, 0, 0))
	background.paste(new_image.convert("RGB"), mask=new_image)

	# SE addition: Lastly, convert transparent pixels to rgba(0, 0, 0, 0) so that Pillow's
	# crop function can detect them.
	# See https://stackoverflow.com/a/14211878
	pixdata = new_image.load()

	width, height = new_image.size
	for image_y in range(height):
		for image_x in range(width):
			if pixdata[image_x, image_y] == (255, 255, 255, 0):
				pixdata[image_x, image_y] = (0, 0, 0, 0)

	return new_image

# Note: We can't type hint driver, because we conditionally import selenium for performance reasons
def render_mathml_to_png(driver, mathml: str, output_filename: Path) -> None:
	"""
	Render a string of MathML into a transparent PNG file.

	INPUTS
	driver: A Selenium webdriver, usually initialized from se.browser.initialize_selenium_firefox_webdriver
	mathml: A string of MathML
	output_filename: A filename to store PNG output to

	OUTPUTS
	None.
	"""

	with tempfile.NamedTemporaryFile(mode="w+") as mathml_file:
		with tempfile.NamedTemporaryFile(mode="w+", suffix=".png") as png_file:
			mathml_file.write(f"<!doctype html><html><head><meta charset=\"utf-8\"><title>MathML fragment</title></head><body>{mathml}</body></html>")
			mathml_file.seek(0)

			driver.get(f"file://{mathml_file.name}")
			# We have to take a screenshot of the html element, because otherwise we screenshot the viewport, which would result in a truncated image
			driver.find_element_by_tag_name("html").screenshot(png_file.name)

			image = Image.open(png_file.name)
			image = _color_to_alpha(image, (255, 255, 255, 255))
			image.crop(image.getbbox()).save(output_filename)

def format_inkscape_svg(filename: Path):
	"""
	Clean and format SVGs created by Inkscape, which have lots of useless metadata.

	INPUTS
	filename: A filename of an Inkscape SVG

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

	image = Image.open(filename)
	data = list(image.getdata())

	image_without_exif = Image.new(image.mode, image.size)
	image_without_exif.putdata(data)
	image_without_exif.save(filename, subsampling="4:4:4")
