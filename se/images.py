#!/usr/bin/env python3
"""
Defines various functions useful for image processing tasks common to epubs.
"""

from pathlib import Path
import tempfile
import struct

from html import unescape
from typing import List, Callable, Dict
import regex
from PIL import Image, ImageMath, PngImagePlugin, UnidentifiedImageError
import importlib_resources
from lxml import etree

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
# iBooks srcset bug: Temporarily ignore this line in pylint
def render_mathml_to_png(driver, mathml: str, output_filename: Path, output_filename_2x: Path) -> None: # pylint: disable=unused-argument
	"""
	Render a string of MathML into a transparent PNG file.

	INPUTS
	driver: A Selenium webdriver, usually initialized from se.browser.initialize_selenium_firefox_webdriver
	mathml: A string of MathML
	output_filename: A filename to store PNG output to
	output_filename_2x: A filename to store hiDPI PNG output to

	OUTPUTS
	None.
	"""

	# For some reason, we must use an .xhtml suffix. Without that, some mathml expressions don't render.
	with tempfile.NamedTemporaryFile(mode="w+", suffix=".xhtml") as mathml_file:
		with tempfile.NamedTemporaryFile(mode="w+", suffix=".png") as png_file:
			mathml_file.write(f"<?xml version=\"1.0\" encoding=\"utf-8\"?><html xmlns=\"http://www.w3.org/1999/xhtml\"><head><meta charset=\"utf-8\"/><title>MathML</title></head><body>{mathml}</body></html>")
			mathml_file.seek(0)

			driver.get(f"file://{mathml_file.name}")
			# We have to take a screenshot of the html element, because otherwise we screenshot the viewport, which would result in a truncated image
			driver.find_element_by_tag_name("html").screenshot(png_file.name)

			# Save hiDPI 2x version
			image = Image.open(png_file.name)
			image = _color_to_alpha(image, (255, 255, 255, 255))
			image = image.crop(image.getbbox())

			image.save(output_filename_2x)

			# Save normal version
			# iBooks srcset bug: once srcset works in iBooks, uncomment these lines
			# image = image.resize((image.width // 2, image.height // 2))
			# image.save(output_filename)

def remove_image_metadata(filename: Path) -> None:
	"""
	Remove exif metadata from an image.

	INPUTS
	filename: A filename of an image

	OUTPUTS
	None.
	"""

	if filename.suffix == ".xcf" or filename.suffix == ".svg":
		# Skip GIMP XCF and SVG files
		return

	if filename.suffix == ".jpg":
		# JPEG images are lossy, and PIL will recompress them on save.
		# Instead of using PIL, read the byte stream and remove all metadata that way.
		# Inspired by https://github.com/hMatoba/Piexif
		with open(filename, 'rb+') as file:
			jpeg_data = file.read()

			if jpeg_data[0:2] != b"\xff\xd8":
				raise se.InvalidFileException(f"Invalid JPEG file: [path][link=file://{filename.resolve()}]{filename}[/].")

			exif_segments = []
			head = 2

			# Get a list of metadata segments from the jpg
			while True:
				if jpeg_data[head: head + 2] == b"\xff\xda":
					break

				length = struct.unpack(">H", jpeg_data[head + 2: head + 4])[0]
				end_point = head + length + 2
				seg = jpeg_data[head: end_point]
				head = end_point

				if head >= len(jpeg_data):
					raise se.InvalidFileException(f"Invalid JPEG file: [path][link=file://{filename.resolve()}]{filename}[/].")

				# See https://www.disktuna.com/list-of-jpeg-markers/
				# and https://exiftool.org/TagNames/JPEG.html
				# These are the 15 "app" segments, EXCEPT app 14, as well as the "comment" segment.
				# This mirrors what exiftool does.
				metadata_segments = [b"\xff\xe1", b"\xff\xe2", b"\xff\xe3", b"\xff\xe4", b"\xff\xe5",
							b"\xff\xe6", b"\xff\xe7", b"\xff\xe8", b"\xff\xe9", b"\xff\xea",
							b"\xff\xeb", b"\xff\xec", b"\xff\xed", b"\xff\xef",
							b"\xff\xfe"]

				if seg[0:2] in metadata_segments:
					exif_segments.append(seg)

			# Now replace those segments with nothing
			for segment in exif_segments:
				jpeg_data = jpeg_data.replace(segment, b"")

			file.seek(0)
			file.write(jpeg_data)
			file.truncate()
	else:
		# PNG and other image types we expect are lossless so we can use PIL to remove metadata
		try:
			image = Image.open(filename)
		except UnidentifiedImageError as ex:
			raise se.InvalidFileException(f"Couldn’t identify image type of [path][link=file://{filename.resolve()}]{filename}[/].") from ex

		data = list(image.getdata())

		image_without_exif = Image.new(image.mode, image.size)
		image_without_exif.putdata(data)

		if image.format == "PNG":
			# Some metadata, like chromaticity and gamma, are useful to preserve in PNGs
			new_exif = PngImagePlugin.PngInfo()
			for key, value in image.info.items():
				if key.lower() == "gamma":
					new_exif.add(b"gAMA", struct.pack("!1I", int(value * 100000)))
				elif key.lower() == "chromaticity":
					new_exif.add(b"cHRM", struct.pack("!8I", \
							int(value[0] * 100000), \
							int(value[1] * 100000), \
							int(value[2] * 100000), \
							int(value[3] * 100000), \
							int(value[4] * 100000), \
							int(value[5] * 100000), \
							int(value[6] * 100000), \
							int(value[7] * 100000)))

			image_without_exif.save(filename, optimize=True, pnginfo=new_exif)
		elif image.format == "TIFF":
			# For some reason, when saving as TIFF we have to cast filename to str() otherwise
			# the save driver throws an exception
			image_without_exif.save(str(filename), compression="tiff_adobe_deflate")
		else:
			image_without_exif.save(str(filename))

def svg_text_to_paths(in_svg: Path, out_svg: Path, remove_style=True) -> None:
	"""
	Convert SVG <text> elements into <path> elements, using SVG
	document's <style> tag and external font files.
	(These SVG font files are built-in to the SE tools).
	Resulting SVG file will have no dependency on external fonts.

	INPUTS
	in_svg: Path for the SVG file to convert <text> elements.
	out_svg: Path for where to write the result SVG file, with <path> elements.

	OUTPUTS
	None.
	"""

	font_paths = []
	name_list = {"league-spartan": ["league-spartan-bold.svg"], "sorts-mill-goudy": ["sorts-mill-goudy-italic.svg", "sorts-mill-goudy.svg"]}
	for font_family, font_names in name_list.items():
		for font_name in font_names:
			with importlib_resources.path(f"se.data.fonts.{font_family}", font_name) as font_path:
				font_paths.append(font_path)
	fonts = []
	for font_path in font_paths:
		font = _parse_font(font_path)
		fonts.append(font)
	svg_in_raw = open(in_svg, "rt").read()

	try:
		xml = etree.fromstring(str.encode(svg_in_raw))
	except Exception as ex:
		raise se.InvalidXmlException(f"Couldn’t parse SVG file: [path][link={in_svg.resolve()}]{in_svg}[/][/]") from ex

	svg_ns = "{http://www.w3.org/2000/svg}"

	style = xml.find(svg_ns + "style")

	# Possibly remove style tag if caller wants that
	def filter_predicate(elem: etree.Element):
		if remove_style and elem.tag.endswith("style"):
			return None # Remove <style> tag
		return elem # Keep all other elements
	if remove_style:
		xml = _traverse_element(xml, filter_predicate)

	for elem in xml.iter():
		if elem.tag.endswith("text"):
			properties = _apply_css(elem, style.text)
			_get_properties_from_text_elem(properties, elem)
			_add_font_to_properties(properties, fonts)
			text = elem.text

			if not text:
				raise se.InvalidFileException(f"SVG [xml]<text>[/] element has no content. File: [path][link=file://{in_svg.resolve()}]{in_svg}[/].")

			elem.tag = "g"
			# Replace <text> tag with <g> tag
			for k in elem.attrib.keys():
				if k != "class":
					del elem.attrib[k]
				elif k == "class" and elem.attrib["class"] != "title-box": # Keep just class attribute if class="title-box"
					del elem.attrib[k]
			elem.attrib["aria-label"] = text
			elem.tail = "\n"
			elem.text = ""
			_add_svg_paths_to_group(elem, properties)

	xmlstr = etree.tostring(xml, pretty_print=True).decode("UTF-8")
	result_all_text = xmlstr.replace("ns0:", "").replace(":ns0", "")
	result_all_text = se.formatting.format_xml(result_all_text)
	open(out_svg, "wt").write(result_all_text)

def _apply_css(elem: etree.Element, css_text: str) -> dict:
	chunks = [[y.strip() for y in x.split("\n") if y.strip() != ""] for x in css_text.replace("\r", "").split("}")]
	result_css = {}

	def apply_css(kvs):
		for pair in kvs:
			k, css = [selector.strip() for selector in pair.split(":")]
			result_css[k] = css.replace("\"", "") # Values may have quotes, like font-family: "League Spartan"

	for chunk in chunks:
		if len(chunk) < 2:
			continue

		selector = chunk[0].replace("{", "")
		kvs = [x.replace(";", "") for x in chunk[1:]]

		if selector[0] == "." and len(selector) >= 2:
			if selector[1:] == elem.get("class"):
				apply_css(kvs)
		elif elem.tag.endswith(selector):
			apply_css(kvs)

	return result_css

# Assumes return_elem is a new copy with no children
# e.g.  xml = _traverse_element(xml, traverser)
# This returns the original tree when traverser is lambda x: x
def _traverse_children(return_elem: etree.Element, old_elem: etree.Element, traverser: Callable) -> None:
	for child in old_elem:
		new_child = traverser(child)
		if new_child is None:
			continue
		# Append child if non-None
		final_child = etree.Element(new_child.tag, new_child.attrib) # empty copy
		final_child.text = new_child.text
		final_child.tail = new_child.tail
		return_elem.append(final_child)

def _traverse_element(elem: etree.Element, traverser: Callable) -> etree.Element:
	return_elem = traverser(elem)
	if return_elem is None:
		return None
	# Make an empty copy of the returned element, if non-None
	return_elem = etree.Element(elem.tag, attrib=elem.attrib)
	return_elem.text = elem.text
	return_elem.tail = elem.tail
	_traverse_children(return_elem, elem, traverser)
	return return_elem

def _get_properties_from_text_elem(properties: Dict, elem: etree.Element) -> None:
	properties["text"] = elem.text
	if elem.get("x"):
		properties["x"] = elem.get("x")
	if elem.get("y"):
		properties["y"] = elem.get("y")

def _add_font_to_properties(properties: Dict, fonts: List) -> None:
	# Wire up with actual font object
	for font in fonts:
		face = font["meta"]["font-face"]
		if face["font-family"] != properties["font-family"]:
			continue
		if "font-style" in face and "font-style" in properties: # Fine if either do not mention style, so defaults to regular or not italic
			if face["font-style"] != properties["font-style"]:
				continue
		properties["font"] = font
		return # One chunk of text can only have one font/variant

def _float_to_str(float_value: float) -> str:
	return "{0:.2f}".format(round(float_value, 2))

def _add_svg_paths_to_group(g_elem: etree.Element, text_properties: Dict) -> None:
	# Required properties to make any progress
	for key in "x y font text font-size".split():
		if not key in text_properties:
			raise se.InvalidCssException(f"svg_text_to_paths: Missing key [text]{key}[/] in [text]text_properties[/] for [xml]<{g_elem.tag}>[/] element in [path]./images/titlepage.svg[/] or [path]./images/cover.svg[/].")
	# We know we have x, y, text, font-size, and font so we can render vectors.
	# Now set up some defaults if not specified.
	text_properties["font-size"] = float(text_properties["font-size"].replace("px", "")) # NOTE assumes pixels and ignores it
	font = text_properties["font"]
	if not "letter-spacing" in text_properties:
		text_properties["letter-spacing"] = 0
	text_properties["letter-spacing"] = float(text_properties["letter-spacing"].replace("px", ""))
	if not "text-anchor" in text_properties:
		text_properties["text-anchor"] = "left"
	if not "units-per-em" in text_properties:
		text_properties["units-per-em"] = float(font["meta"]["font-face"]["units-per-em"])
	if not "horiz-adv-x" in text_properties:
		text_properties["horiz-adv-x"] = float(font["meta"]["horiz-adv-x"])
	font = text_properties["font"]
	text_string = text_properties["text"]

	width = 0.0
	if text_properties["text-anchor"] == "middle" or text_properties["text-anchor"] == "center" or \
		text_properties["text-anchor"] == "right" or text_properties["text-anchor"] == "end":
		width = _get_text_width(text_string, font, text_properties)

	last_xy = [0.0, 0.0]
	last_xy[0] = float(text_properties["x"])
	if text_properties["text-anchor"] == "middle" or text_properties["text-anchor"] == "center":
		last_xy[0] -= width / 2.0
	elif text_properties["text-anchor"] == "right" or text_properties["text-anchor"] == "end":
		last_xy[0] -= width
	last_xy[1] = float(text_properties["y"])

	path_ds = []
	def walker(d_attrib: str, size: float, delta_x: float, delta_y: float) -> None:
		# Render a glyph (text representaiton of a path outline) to a properly
		# translated and scaled path outline.
		d_attrib = _d_translate_and_scale(d_attrib, last_xy[0], last_xy[1], size, -size)
		if d_attrib != "":
			path_ds.append(d_attrib)
		last_xy[0] += delta_x
		last_xy[1] += delta_y
	_walk_characters(text_string, font, text_properties, last_xy[0], last_xy[1], walker)
	# Append each glyph outline as its own <path> tag, as Inkscape would do.
	for d_attr in path_ds:
		path_elem = etree.Element("path", {"d": d_attr})
		path_elem.tail = "\n"
		g_elem.append(path_elem) # ?

def _get_text_width(text_string: str, font: Dict, text_properties: Dict) -> float:
	last_xy = [0, 0]
	def callback(_d, _size, delta_x, delta_y):
		last_xy[0] += delta_x
		last_xy[1] += delta_y
	_walk_characters(text_string, font, text_properties, last_xy[0], last_xy[1], callback)
	return last_xy[0]

def _walk_characters(text_string: str, font: Dict, text_properties: Dict, last_x: float, last_y: float, use_glyph_callback: Callable) -> None:
	for index, ch0 in enumerate(text_string):
		ch1 = text_string[index + 1] if index < len(text_string) - 1 else ""
		ch2 = text_string[index + 2] if index < len(text_string) - 2 else ""
		combo = None
		ch0_ch1 = ch0 + ch1
		if ch0_ch1 in font["glyphs"]:
			combo = font["glyphs"][ch0_ch1]
		if text_properties["letter-spacing"] == 0 and index < len(text_string) - 2 and combo:
			# if ligature or "wide" unicode character exists -- don't use ligature if letter-spacing set to something interesting :-)
			# Found combined characters ch+ch1
			_advance_by_glyph(font, text_properties, last_x, last_y, ch0 + ch1, ch2, use_glyph_callback)
			index += 1
		if text_properties["letter-spacing"] == 0 and index < len(text_string) and combo:
			# If ligature or "wide" unicode character exists -- don't use ligature if letter-spacing set to something interesting :-)
			_advance_by_glyph(font, text_properties, last_x, last_y, ch0 + ch1, "", use_glyph_callback)
		else:
			_advance_by_glyph(font, text_properties, last_x, last_y, ch0, ch1, use_glyph_callback)

def _advance_by_glyph(font: Dict, text_properties: Dict, _last_x, _last_y, uni: str, uni_next: str, callback: Callable) -> None:
	glyphs = font["glyphs"]
	glyph = {} # Default, but not None, to appease type-checker
	if uni in glyphs:
		glyph = glyphs[uni]
	if not uni:
		glyph = font["meta"]["missing-glyph"]
	d_attrib = None
	if "d" in glyph:
		d_attrib = glyph["d"]
	if not d_attrib:
		# "" for Space character, not None
		d_attrib = ""
	size = text_properties["font-size"] / text_properties["units-per-em"]
	horiz_adv_x = float(glyph["horiz-adv-x"]) if "horiz-adv-x" in glyph else text_properties["horiz-adv-x"]
	hkern = 0.0
	kern_key = uni + "," + uni_next
	if kern_key in font["hkern"]:
		advance_x = float(font["hkern"][kern_key])
		hkern = advance_x
	horiz_adv_x -= hkern
	delta_x = horiz_adv_x * size + (text_properties["letter-spacing"] if uni_next != "" else 0)
	callback(d_attrib, size, delta_x, 0) # --> result outline d. Input = ("d"), delta_x, delta_y

def _d_translate_and_scale(d_attrib: str, translate_x: float, translate_y: float, scale_x: float, scale_y: float) -> str:
	return _d_apply_matrix(d_attrib, [scale_x, 0, 0, scale_y, translate_x, translate_y])

def _d_scale(d_attrib: str, scale_x=1.0, scale_y=1.0) -> str:
	return _d_apply_matrix(d_attrib, [scale_x, 0.0, 0.0, scale_y, 0.0, 0.0])

# This is the main interesting part of SVG glyph rendering process.
# The d attribute (path outline data, see https://www.w3.org/TR/SVG/paths.html#DProperty)
# from a single glyph or ligature will have its coordinates translated and scaled by the
# matrix transform passed in, and a return d attribute string will be created, showing the
# glyph in the correct location and size.
M_NOTZ_Z_REGEX = regex.compile("M[^zZ]*[zZ]")
AZ_NOTAZ_REGEX = regex.compile("[a-zA-Z]+[^a-zA-Z]*")
NOTAZ_REGEX = regex.compile("[^a-zA-Z]*")
NUMBER_REGEX = regex.compile("-?[0-9.]+")
COMMA_MINUS_REGEX = regex.compile(",-")

def _clean_comma_minus(d_attrib: str) -> str:
	return COMMA_MINUS_REGEX.sub("-", d_attrib)

def _d_apply_matrix_one_shape(d_attrib: str, matrix: List) -> str:
	new_coords: List = []
	matrix_a = 0
	matrix_b = 0
	matrix_c = 0
	matrix_d = 0
	matrix_e = 0
	matrix_f = 0
	ret = []
	for instruction in AZ_NOTAZ_REGEX.findall(d_attrib):
		i = NOTAZ_REGEX.sub("", instruction)
		coords = [float(x) for x in NUMBER_REGEX.findall(instruction)]
		new_coords = []
		while coords and len(coords) > 0:
			[matrix_a, matrix_b, matrix_c, matrix_d, matrix_e, matrix_f] = matrix
			if i == i.lower(): # Do not translate relative instructions (lowercase)
				matrix_e = 0
				matrix_f = 0
			def push_point(point_x: float, point_y: float) -> None:
				new_coords.append(matrix_a * point_x + matrix_c * point_y + matrix_e)
				new_coords.append(matrix_b * point_x + matrix_d * point_y + matrix_f)
			# Convert horizontal lineto to lineto (relative)
			if i == "h":
				i = "l"
				push_point(coords.pop(0), 0)
			# Convert vertical lineto to lineto (relative)
			elif i == "v":
				i = "l"
				push_point(0, coords.pop(0))
			# NOTE: We do not handle "a,A" (elliptic arc curve) commands in the SVG font d="..." attribute definitions
			# cf. http://www.w3.org/TR/SVG/paths.html#PathDataCurveCommands
			# Every other command -- M m L l c C s S Q q T t -- come in multiples of two numbers (coordinate pair (x,y)):
			else:
				push_point(coords.pop(0), coords.pop(0))
		new_instruction = i + _clean_comma_minus(",".join([_float_to_str(num) for num in new_coords]))
		ret.append(new_instruction)
	return "".join(ret) + " "

def _d_apply_matrix(d_attrib: str, matrix: List) -> str:
	matches = M_NOTZ_Z_REGEX.findall(d_attrib)
	shapes = [_d_apply_matrix_one_shape(shape, matrix) for shape in matches if shape]
	return " ".join(shapes).strip()

def _parse_font(font_path: Path) -> dict:
	font_svg_raw = open(font_path, "rt").read()
	xml = etree.fromstring(str.encode(font_svg_raw))
	font: Dict = {"glyphs": {}, "hkern": {}, "meta": {}}
	glyphs = font["glyphs"]
	hkern = font["hkern"]
	meta = font["meta"]
	g_name_to_unicode = {}
	for elem in xml.iter():
		tag = elem.tag.replace("{http://www.w3.org/2000/svg}", "")
		if tag == "font":
			meta["id"] = elem.attrib["id"]
			meta["horiz-adv-x"] = float(elem.attrib["horiz-adv-x"])
		elif tag == "font-face":
			meta["font-face"] = dict(elem.attrib)
		elif tag == "missing-glyph":
			meta["missing-glyph"] = dict(elem.attrib)
		elif tag == "glyph" and elem.attrib:
			# normalize keys for glyphs dictionary to be unicode strings and not
			# glyph-name (which we presume are entity names, e.g. rdquo as in &rdquo;)
			if "unicode" in elem.attrib:
				g_name = elem.attrib["glyph-name"] if "glyph-name" in elem.attrib else None
				uni = elem.attrib["unicode"]
				if uni.startswith("&#x") and uni.endswith(";"):
					uni = uni.replace(";", "")
					uni = chr(int(uni[2:], 16))
				if g_name:
					g_name_to_unicode[g_name] = uni
				else:
					g_name_to_unicode[uni] = uni
				glyphs[uni] = {}
				if "horiz-adv-x" in elem.attrib:
					glyphs[uni]["horiz-adv-x"] = elem.attrib["horiz-adv-x"]
				if "d" in elem.attrib:
					glyphs[uni]["d"] = elem.attrib["d"]
			elif "glyph-name" in elem.attrib:
				g_name = elem.attrib["glyph-name"]
				if g_name.find(".") >= 0:
					g_name = g_name[:g_name.find(".")] # remove .1 .002 .sc   etc.
				fake_entity = "&" + g_name + ";"
				uni = unescape(fake_entity)
				if uni and fake_entity != uni and len(uni) <= 2:
					g_name_to_unicode[g_name] = uni
					glyphs[uni] = {}
					if "horiz-adv-x" in elem.attrib:
						glyphs[uni]["horiz-adv-x"] = elem.attrib["horiz-adv-x"]
					if "d" in elem.attrib:
						glyphs[uni]["d"] = elem.attrib["d"]
	# Must parse hkern (horizontal kerning) elements after glyphs so we have g_name_to_unicode map available
	for elem in xml.iter():
		tag = elem.tag.replace("{http://www.w3.org/2000/svg}", "")
		if tag == "hkern":
			if "k" in elem.attrib:
				kerning = elem.attrib["k"]
			else:
				continue
			if "g1" in elem.attrib and "g2" in elem.attrib:
				glyphs1 = elem.attrib["g1"].split(",")
				glyphs2 = elem.attrib["g2"].split(",")
				kerning = elem.attrib["k"]
				for glyph1 in glyphs1:
					if not glyph1 in g_name_to_unicode:
						continue
					for glyph2 in glyphs2:
						if not glyph2 in g_name_to_unicode:
							continue
						pair = g_name_to_unicode[glyph1] +"," + g_name_to_unicode[glyph2]
						hkern[pair] = kerning
			if "u1" in elem.attrib and "u2" in elem.attrib:
				unicodes1 = elem.attrib["u1"].split(",")
				unicodes2 = elem.attrib["u2"].split(",")
				for uni1 in unicodes1:
					for uni2 in unicodes2:
						pair = uni1 + "," + uni2
						hkern[pair] = kerning
	return font
