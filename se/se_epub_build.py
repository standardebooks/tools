#!/usr/bin/env python3
"""
This module contains the build function.

Strictly speaking, the build() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put it in a separate file.
"""

import json
import os
import shutil
import subprocess
import tempfile
from copy import deepcopy
from hashlib import sha1
from html import unescape
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import importlib_resources

from cairosvg import svg2png
from PIL import Image, ImageOps
import lxml.cssselect
from lxml import etree
import regex

import se
import se.easy_xml
import se.epub
import se.formatting
import se.images
import se.typography
from se.vendor.kobo_touch_extended import kobo
from se.vendor.mobi import mobi


COVER_THUMBNAIL_WIDTH = int(se.COVER_WIDTH / 4) # Cast to int required for PIL
COVER_THUMBNAIL_HEIGHT = int(se.COVER_HEIGHT / 4) # Cast to int required for PIL
SVG_OUTER_STROKE_WIDTH = 2
SVG_TITLEPAGE_OUTER_STROKE_WIDTH = 4
ENDNOTE_CHUNK_SIZE = 500

# See https://www.w3.org/TR/dpub-aria-1.0/
# Without preceding `doc-`
ARIA_ROLES = ["abstract", "acknowledgments", "afterword", "appendix", "backlink", "bibliography", "biblioref", "chapter", "colophon", "conclusion", "cover", "credit", "credits", "dedication", "endnotes", "epigraph", "epilogue", "errata", "example", "footnote", "foreword", "glossary", "glossref", "index", "introduction", "noteref", "notice", "pagebreak", "pagelist", "part", "preface", "prologue", "pullquote", "qna", "subtitle", "tip", "toc"]

class BuildMessage:
	"""
	An object representing an output message for the build function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	def __init__(self, source: str, code: str, text: str, filename: Optional[Path] = None, line: Optional[int] = None, col: Optional[int] = None, submessages: Optional[List] = None):
		self.source = source
		self.code = code
		self.text = text.strip()
		self.filename = filename
		self.line = line
		self.col = col
		self.location = f"({line}:{col})" if self.line and self.col else None
		self.submessages = submessages if submessages else []

def __save_debug_epub(work_compatible_epub_dir: Path) -> Path:
	"""
	Copy the given epub directory to a fixed SE temp directory, and
	return the path to that directory.
	"""

	se_temp_dir = Path(tempfile.gettempdir() + "/se")
	se_temp_dir.mkdir(exist_ok=True)
	epub_temp_dir = se_temp_dir / work_compatible_epub_dir.name

	# Remove the dir if it currently exists
	shutil.rmtree(epub_temp_dir, ignore_errors=True)

	# Copy the epub output into the temp dir
	shutil.copytree(work_compatible_epub_dir, str(epub_temp_dir))

	return epub_temp_dir

def build(self, run_epubcheck: bool, check_only: bool, build_kobo: bool, build_kindle: bool, output_dir: Path, proof: bool) -> None:
	"""
	Entry point for `se build`
	"""

	ibooks_srcset_bug_exists = True

	if check_only:
		run_epubcheck = True
		build_kobo = False
		build_kindle = False

	# Check for some required tools
	if build_kindle:
		which_ebook_convert = shutil.which("ebook-convert")
		if which_ebook_convert:
			ebook_convert_path = Path(which_ebook_convert)
		else:
			# Look for default Mac calibre app path if none found in path
			ebook_convert_path = Path("/Applications/calibre.app/Contents/MacOS/ebook-convert")
			if not ebook_convert_path.exists():
				raise se.MissingDependencyException("Couldn’t locate [bash]ebook-convert[/]. Is [bash]calibre[/] installed?")

	run_ace = False
	if run_epubcheck:
		java_present = True
		if not shutil.which("java"):
			java_present = False
		# Mac Big Sur+ has a "dummy" /usr/bin/java; test -version to see if java is really installed
		elif os.uname()[0] == "Darwin":
			try:
				java_check = subprocess.run(["java", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
				if java_check.stderr.decode().find("Unable to locate") >= 0:
					java_present = False
			except Exception:
				java_present = False

		if not java_present:
			raise se.MissingDependencyException("Couldn’t locate [bash]java[/]. Is it installed?")

		if shutil.which("ace"):
			run_ace = True

	# Check the output directory and create it if it doesn't exist
	try:
		output_dir = output_dir.resolve()
		output_dir.mkdir(parents=True, exist_ok=True)
	except Exception as ex:
		raise se.FileExistsException(f"Couldn’t create output directory: [path][link=file://{output_dir}]{output_dir}[/][/].") from ex

	# All clear to start building!

	# Make a copy of the metadata dom because we'll be making changes
	metadata_dom = deepcopy(self.metadata_dom)

	# Initiate the various filenames we'll be using for output
	# By convention the ASIN is set to the SHA-1 sum of the book's identifying URL
	try:
		identifier = metadata_dom.xpath("//dc:identifier")[0].inner_xml().replace("url:", "")
		if identifier == "":
			identifier = self.generated_identifier

		asin = sha1(identifier.encode("utf-8")).hexdigest()

		identifier = identifier.replace("https://standardebooks.org/ebooks/", "").replace("/", "_")
	except Exception as ex:
		raise se.InvalidSeEbookException(f"Missing [xml]<dc:identifier>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/].") from ex

	if not metadata_dom.xpath("//dc:title"):
		raise se.InvalidSeEbookException(f"Missing [xml]<dc:title>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/].")

	compatible_epub_output_filename = f"{identifier}{'.proof' if proof else ''}.epub"
	advanced_epub_output_filename = f"{identifier}{'.proof' if proof else ''}_advanced.epub"
	kobo_output_filename = f"{identifier}{'.proof' if proof else ''}.kepub.epub"
	kindle_output_filename = f"{identifier}{'.proof' if proof else ''}.azw3"
	endnote_files_to_be_chunked = []

	# Create our temp work directory
	with tempfile.TemporaryDirectory() as temp_dir:
		work_dir = Path(temp_dir)
		work_compatible_epub_dir = work_dir / self.path.name

		shutil.copytree(self.epub_root_path, str(work_compatible_epub_dir), dirs_exist_ok=True)

		shutil.rmtree(work_compatible_epub_dir / ".git", ignore_errors=True)

		# We may have a .gitignore file in the epub root if this is a white-label epub. If so, remove it before continuing
		(work_compatible_epub_dir / ".gitignore").unlink(True)

		# Clean up old output files if any
		(output_dir / f"thumbnail_{asin}_EBOK_portrait.jpg").unlink(True)
		(output_dir / compatible_epub_output_filename).unlink(True)
		(output_dir / advanced_epub_output_filename).unlink(True)
		(output_dir / kobo_output_filename).unlink(True)
		(output_dir / kindle_output_filename).unlink(True)

		# Are we including proofreading CSS?
		if proof:
			with open(work_compatible_epub_dir / "epub" / "css" / "local.css", "a", encoding="utf-8") as local_css_file:
				with importlib_resources.open_text("se.data.templates", "proofreading.css", encoding="utf-8") as proofreading_css_file:
					local_css_file.write("\n" + proofreading_css_file.read())

		# Update the release date in the metadata and colophon
		if self.last_commit:
			for file_path in work_compatible_epub_dir.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)

				if dom.xpath("/html/body//section[contains(@epub:type, 'colophon')]"):
					last_updated_iso = regex.sub(r"\.[0-9]+$", "", self.last_commit.timestamp.isoformat()) + "Z"
					last_updated_iso = regex.sub(r"\+.+?Z$", "Z", last_updated_iso)
					# In the line below, we can't use %l (unpadded 12 hour clock hour) because it isn't portable to Windows.
					# Instead we use %I (padded 12 hour clock hour) and then do a string replace to remove leading zeros.
					last_updated_friendly = f"{self.last_commit.timestamp:%B %e, %Y, %I:%M <abbr class=\"eoc\">%p</abbr>}".replace(" 0", " ")
					last_updated_friendly = regex.sub(r"\s+", " ", last_updated_friendly).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

					# Set modified date in the metadata file
					for node in metadata_dom.xpath("//meta[@property='dcterms:modified']"):
						node.set_text(last_updated_iso)

					with open(work_compatible_epub_dir / "epub" / self.metadata_file_path.name, "w", encoding="utf-8") as file:
						file.write(metadata_dom.to_string())

					# Update the colophon with release info
					with open(file_path, "r+", encoding="utf-8") as file:
						xhtml = file.read()

						xhtml = xhtml.replace("<p>The first edition of this ebook was released on<br/>", f"<p>This edition was released on<br/>\n\t\t\t<b>{last_updated_friendly}</b><br/>\n\t\t\tand is based on<br/>\n\t\t\t<b>revision {self.last_commit.short_sha}</b>.<br/>\n\t\t\tThe first edition of this ebook was released on<br/>")

						file.seek(0)
						file.write(xhtml)
						file.truncate()

					self.flush_dom_cache_entry(file_path)
					break

		# Output the pure epub3 file
		if not check_only:
			se.epub.write_epub(work_compatible_epub_dir, output_dir / advanced_epub_output_filename)

		# Now add compatibility fixes for older ereaders.

		# Include compatibility CSS
		compatibility_css_filename = "compatibility.css"
		if not self.metadata_dom.xpath("//dc:identifier[starts-with(., 'url:https://standardebooks.org')]"):
			compatibility_css_filename = "compatibility-white-label.css"

		with open(work_compatible_epub_dir / "epub" / "css" / "core.css", "a", encoding="utf-8") as core_css_file:
			with importlib_resources.open_text("se.data.templates", compatibility_css_filename, encoding="utf-8") as compatibility_css_file:
				core_css_file.write("\n" + compatibility_css_file.read())

		# Simplify CSS and tags
		total_css = ""

		# Simplify the CSS first.  Later we'll update the document to match our simplified selectors.
		# While we're doing this, we store the original css into a single variable so we can extract the original selectors later.
		for file_path in work_compatible_epub_dir.glob("**/*.css"):
			with open(file_path, "r+", encoding="utf-8") as file:
				css = file.read()

				total_css = total_css + css + "\n"
				file.seek(0)
				file.write(se.formatting.simplify_css(css))
				file.truncate()

		# Now get a list of original selectors
		# Remove @supports and @media queries
		total_css = regex.sub(r"@\s*(?:supports|media).+?{(.+?)}\s*}", r"\1}", total_css, flags=regex.DOTALL)

		# Remove CSS rules
		total_css = regex.sub(r"{[^}]+}", "", total_css)

		# Remove trailing commas
		total_css = regex.sub(r",", "", total_css)

		# Remove comments
		total_css = regex.sub(r"/\*.+?\*/", "", total_css, flags=regex.DOTALL)

		# Remove @ defines
		total_css = regex.sub(r"^@.+", "", total_css, flags=regex.MULTILINE)

		# Construct a dictionary of the original selectors
		selectors = {line for line in total_css.splitlines() if line != ""}

		# Get a list of .xhtml files to simplify
		for file_path in work_compatible_epub_dir.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			# Don't mess with the ToC, since if we have ol/li > first-child selectors we could screw it up
			if dom.xpath("/html/body//nav[contains(@epub:type, 'toc')]"):
				continue

			# Now iterate over each CSS selector and see if it's used in any of the files we found
			for selector in selectors:
				try:
					# Add classes to elements that match any of our selectors to simplify. For example, if we select :first-child, add a "first-child" class to all elements that match that.
					for selector_to_simplify in se.SELECTORS_TO_SIMPLIFY:
						while selector_to_simplify in selector:
							# Potentially the pseudoclass we’ll simplify isn’t at the end of the selector,
							# so we need to temporarily remove the trailing part to target the right elements.
							split_selector = regex.split(fr"({selector_to_simplify}(\(.*?\))?)", selector, 1)
							target_element_selector = "".join(split_selector[0:2])

							replacement_class = split_selector[1].replace(":", "").replace("(", "-").replace("n-", "n-minus-").replace("n+", "n-plus-").replace(")", "")
							selector = selector.replace(split_selector[1], "." + replacement_class, 1)
							for element in dom.css_select(target_element_selector):
								current_class = element.get_attr("class") or ""

								if replacement_class not in current_class:
									element.set_attr("class", f"{current_class} {replacement_class}".strip())

				except lxml.cssselect.ExpressionError:
					# This gets thrown if we use pseudo-elements, which lxml doesn't support
					pass
				except lxml.cssselect.SelectorSyntaxError as ex:
					raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: [css]{selector}[/]. Exception: {ex}")

				# We've already replaced attribute/namespace selectors with classes in the CSS, now add those classes to the matching elements
				if regex.search(r"\[[a-z]+\|[a-z]+", selector):
					for namespace_selector in regex.findall(r"\[[a-z]+\|[a-z]+(?:[\~\^\|\$\*]?\=\"[^\"]*?\")?\]", selector):
						new_class = regex.sub(r"^\.", "", se.formatting.namespace_to_class(namespace_selector))

						for element in dom.css_select(namespace_selector):
							# If we're targeting xml:lang attributes, never add the class to `<html>` or `<body>`.
							# We were most likely targeting `body [xml|lang]` but since by default we add classes to
							# everything, that could result in `<html>` getting the `xml-lang` class and making everything
							# italics.
							if namespace_selector == "[xml|lang]" and element.tag in ("html", "body"):
								continue

							current_class = element.get_attr("class") or ""

							if new_class not in current_class:
								current_class = f"{current_class} {new_class}".strip()
								element.set_attr("class", current_class)

		# Done simplifying CSS and tags!

		# Extract cover and cover thumbnail
		cover_local_path = metadata_dom.xpath("/package/manifest/item[@properties='cover-image'][1]/@href", True)

		# If we have a cover, convert it to JPG
		if cover_local_path:
			cover_work_path = work_compatible_epub_dir / "epub" / cover_local_path

			if cover_work_path.suffix in (".svg", ".png"):
				# If the cover is SVG, convert to PNG first
				if cover_work_path.suffix == ".svg":
					svg2png(url=str(cover_work_path), unsafe=True, write_to=str(work_dir / "cover.png")) # remove unsafe flag when cairosvg > 2.7.0

				# Now convert PNG to JPG
				cover = Image.open(work_dir / "cover.png")
				cover = cover.convert("RGB") # Remove alpha channel from PNG if necessary
				cover.save(work_compatible_epub_dir / "epub" / "images" / "cover.jpg")

				cover_work_path.unlink()

				# Replace .svg/.png with .jpg in the metadata
				for node in metadata_dom.xpath(f"/package/manifest//item[contains(@href, '{cover_local_path}')]"):
					for name, value in node.lxml_element.items():
						node.set_attr(name, regex.sub(r"\.(svg|png)$", ".jpg", value))

					node.set_attr("media-type", "image/jpeg")

		# Add an element noting the version of the se tools that built this ebook, but only if the se vocab prefix is present
		for node in metadata_dom.xpath("/package[contains(@prefix, 'se:')]/metadata"):
			node.append(etree.fromstring(f"<meta property=\"se:built-with\">{se.VERSION}</meta>"))

		# Loop over files to make some compatibility replacements
		for file_path in work_compatible_epub_dir.glob("**/*"):
			if file_path.suffix == ".svg":
				# For night mode compatibility, give the logo/titlepage a 1px white stroke attribute
				dom = self.get_dom(file_path)

				# If we're adding stroke to the logo, make sure it's SE files only.
				# 3rd party files will get mangled.
				if dom.xpath("/svg/title[contains(., 'Standard Ebooks')]"):
					if dom.xpath("/svg/title[contains(., 'titlepage')]"):
						stroke_width = SVG_TITLEPAGE_OUTER_STROKE_WIDTH
					else:
						stroke_width = SVG_OUTER_STROKE_WIDTH

					new_elements = []

					# First remove some useless elements
					for node in dom.xpath("/svg/*[name() != 'g' and name() != 'path']"):
						node.remove()

					# Get all path elements and add a white stroke to each one.
					# We clone each node and add it to a list, which we will insert into
					# the original SVG later
					for node in dom.xpath("//path"):
						style = node.get_attr("style") or ""
						style = style + f" stroke: #ffffff; stroke-width: {stroke_width}px;"

						node_clone = deepcopy(node)
						node_clone.set_attr("style", style)

						new_elements.append(node_clone.lxml_element)

					# Now insert the elements we just cloned, before the first <g> or <path> so that
					# they appear below the original paths
					for node in dom.xpath("(//*[name()='g' or name()='path'])[1]"):
						for element in new_elements:
							node.lxml_element.addprevious(element)

					if dom.xpath("/svg[@height or @width]"):
						# If this SVG specifies height/width, then increase height and width by 2 pixels
						for node in dom.xpath("/svg[@height]"):
							new_value = int(node.get_attr("height")) + stroke_width
							node.set_attr("height", str(new_value))

						for node in dom.xpath("/svg[@width]"):
							new_value = int(node.get_attr("width")) + stroke_width
							node.set_attr("width", str(new_value))

						# Add a <g> element to translate everything by 1px
						fragment = etree.fromstring(str.encode(f"""<g transform="translate({stroke_width / 2}, {stroke_width / 2})"></g>"""))

						for element in reversed(dom.xpath("/svg/*")):
							fragment.insert(0, element.lxml_element)

						for element in dom.xpath("/svg"):
							element.lxml_element.insert(0, fragment)

					# All done, write the SVG so that we can convert to PNG
					with open(file_path, "w", encoding="utf-8") as file:
						file.write(dom.to_string())

			if file_path.suffix == ".xhtml":
				dom = self.get_dom(file_path)

				# Fix any references in the markup to the cover SVG
				for node in dom.xpath("/html/body//img[re:test(@src, '\\.svg$')]"):
					src = node.get_attr("src")
					if self.cover_path and self.cover_path.name in src:
						node.set_attr("src", src.replace(".svg", ".jpg"))

				# Check if there's any MathML to convert from "content" to "presentational" type
				# We expect MathML to be the "content" type (versus the "presentational" type).
				# We use an XSL transform to convert from "content" to "presentational" MathML.
				# If we start with presentational, then nothing will be changed.
				# Kobo supports presentational MathML. After we build kobo, we convert the presentational MathML to PNG for the rest of the builds.
				mathml_transform = None
				for node in dom.xpath("/html/body//m:math"):
					mathml_without_namespaces = regex.sub(r"<(/?)m:", r"<\1", node.to_string())
					mathml_without_namespaces = regex.sub(r"<math", '<math xmlns="http://www.w3.org/1998/Math/MathML\"', mathml_without_namespaces)
					mathml_content_tree = etree.fromstring(str.encode(f"""<?xml version="1.0" encoding="utf-8"?>{mathml_without_namespaces}"""))

					# Initialize the transform object, if we haven't yet
					if not mathml_transform:
						with importlib_resources.path("se.data", "mathmlcontent2presentation.xsl") as mathml_xsl_filename:
							mathml_transform = etree.XSLT(etree.parse(str(mathml_xsl_filename)))

					# Transform the mathml and get a string representation
					# XSLT comes from https://github.com/fred-wang/webextension-content-mathml-polyfill
					mathml_presentation_tree = mathml_transform(mathml_content_tree)
					mathml_presentation_xhtml = etree.tostring(mathml_presentation_tree, encoding="unicode", pretty_print=True, with_tail=False).strip()

					# The output adds a new namespace definition to the root <math> element. Remove it and re-add the m: namespace instead
					mathml_presentation_xhtml = regex.sub(r" xmlns=", " xmlns:m=", mathml_presentation_xhtml)
					mathml_presentation_xhtml = regex.sub(r"<(/)?", r"<\1m:", mathml_presentation_xhtml)

					# Plop our presentational mathml back in to the XHTML we're processing
					node.replace_with(etree.fromstring(str.encode(mathml_presentation_xhtml)))

				# Since we added an outlining stroke to the titlepage/publisher logo images, we
				# want to remove the se:image.color-depth.black-on-transparent semantic
				for node in dom.xpath("/html/body//img[ (contains(@epub:type, 'z3998:publisher-logo') or ancestor-or-self::*[re:test(@epub:type, '\\btitlepage\\b')]) and contains(@epub:type, 'se:image.color-depth.black-on-transparent')]"):
					node.remove_attr_value("epub:type", "se:image.color-depth.black-on-transparent")

				# Add ARIA roles, which are just mostly duplicate attributes to epub:type
				for role in ARIA_ROLES:
					# Exclude landmarks because while their semantics indicate what their *links* contain, not what *they themselves are*.
					# Skip elements that already have a `role` attribute, as more than one role will cause ace to fail
					for node in dom.xpath(f"/html//*[not(@role) and not(ancestor-or-self::nav[contains(@epub:type, 'landmarks')]) and re:test(@epub:type, '\\b{role}\\b')]"):
						# <article>s generally aren't allowed aria roles, so skip them
						if node.tag == "article":
							continue

						attr_values = regex.split(r"\s", node.get_attr("epub:type"))

						if len(attr_values) > 1:
							# If there is more than one value for epub:type, ace expects the `role` attribute
							# to be set to the first aria-valid epub:type value. Iterate over the epub:type values
							# and break when we find our first match.
							for attr_value in attr_values:
								if attr_value in ARIA_ROLES:
									node.set_attr("role", f"doc-{attr_value}")
									break
						else:
							node.set_attr("role", f"doc-{attr_values[0]}")

				# To get popup footnotes in iBooks, we have to add the `footnote` and `footnotes` semantic
				# Still required as of 2021-05
				# Matching `endnote` will also catch `endnotes`
				for node in dom.xpath("/html/body//*[contains(@epub:type, 'endnote')]"):
					plural = ""
					if "endnotes" in node.get_attr("epub:type"):
						plural = "s"

					node.add_attr_value("epub:type", "footnote" + plural)

					# Remember to get our custom style selectors that we added, too
					if "epub-type-endnote" + plural in (node.get_attr("class") or ""):
						node.add_attr_value("class", "epub-type-footnote" + plural)

				# If this file is an endnotes file, add it to our list for later processing
				if float(dom.xpath("count(/html/body//section[contains(@epub:type, 'endnotes')]/ol/li)", True)) > ENDNOTE_CHUNK_SIZE + 100:
					endnote_files_to_be_chunked.append(file_path)

				# Include extra lang tag for accessibility compatibility
				for node in dom.xpath("//*[@xml:lang]"):
					node.set_attr("lang", node.get_attr("xml:lang"))

				processed_xhtml = se.formatting.format_xhtml(dom.to_string())

				if dom.xpath("/html/body//section[contains(@epub:type, 'endnotes')]"):
					# iOS renders the left-arrow-hook character as an emoji; this fixes it and forces it to render as text.
					# See https://github.com/standardebooks/tools/issues/73
					# See http://mts.io/2015/04/21/unicode-symbol-render-text-emoji/
					processed_xhtml = processed_xhtml.replace("\u21a9", "\u21a9\ufe0e")

				# Typography: replace double and triple em dash characters with extra em dashes.
				processed_xhtml = processed_xhtml.replace("⸺", f"—{se.WORD_JOINER}—")
				processed_xhtml = processed_xhtml.replace("⸻", f"—{se.WORD_JOINER}—{se.WORD_JOINER}—")

				# Typography: replace some other less common characters.
				processed_xhtml = processed_xhtml.replace("⅒", "1/10")
				processed_xhtml = processed_xhtml.replace("℅", "c/o")
				processed_xhtml = processed_xhtml.replace("✗", "×")
				processed_xhtml = processed_xhtml.replace("〃", "“")
				processed_xhtml = processed_xhtml.replace(" ", f"{se.NO_BREAK_SPACE}{se.NO_BREAK_SPACE}") # em-space to two nbsps
				processed_xhtml = processed_xhtml.replace("∶", ":")
				processed_xhtml = processed_xhtml.replace("℅", "c/o")

				# Replace combining vertical line above, used to indicate stressed syllables, with combining acute accent
				processed_xhtml = processed_xhtml.replace(fr"{se.COMBINING_VERTICAL_LINE_ABOVE}", fr"{se.COMBINING_ACUTE_ACCENT}")

				# Many e-readers don't support the word joiner character (U+2060).
				# They DO, however, support the now-deprecated zero-width non-breaking space (U+FEFF)
				# For epubs, do this replacement.  Kindle now seems to handle everything fortunately.
				processed_xhtml = processed_xhtml.replace(se.WORD_JOINER, se.ZERO_WIDTH_SPACE)

				# We've disabled quote-align for now, because it causes more problems than expected.
				# # Move quotation marks over periods and commas
				# # The negative lookahead is to prevent matching `.&hairsp;…`
				# processed_xhtml = regex.sub(fr"([\\.…,])([’”{se.HAIR_SPACE}]+)(?!…)", r"""\1<span class="quote-align">\2</span>""", processed_xhtml)

				# # The above replacement may replace text within <img alt> attributes. Remove those now until no replacements remain, since we may have
				# # many matches in the same line
				# replacements = 1
				# while replacements > 0:
				# 	processed_xhtml, replacements = regex.subn(r"alt=\"([^<>\"]+?)<span class=\"quote-align\">([^<>\"]+?)</span>", r"""alt="\1\2""", processed_xhtml)

				# # Do the same for <title> elements
				# replacements = 1
				# while replacements > 0:
				# 	processed_xhtml, replacements = regex.subn(r"<title>([^<>]+?)<span class=\"quote-align\">([^<>]+?)</span>", r"""<title>\1\2""", processed_xhtml)

				with open(file_path, "w", encoding="utf-8") as file:
					file.write(processed_xhtml)

				# Since we changed the dom string using regex, we have to flush its cache entry so we can re-build it later
				self.flush_dom_cache_entry(file_path)

			if file_path.suffix == ".css":
				with open(file_path, "r+", encoding="utf-8") as file:
					css = file.read()
					processed_css = css

					# To get popup footnotes in iBooks, we have to change epub:endnote to epub:footnote.
					# Remember to get our custom style selectors too.
					processed_css = processed_css.replace("endnote", "footnote")

					# page-break-* is deprecated in favor of break-*. Add page-break-* aliases for compatibility in older ereaders.
					processed_css = regex.sub(r"(\s+)break-(.+?:\s.+?;)", "\\1break-\\2\t\\1page-break-\\2", processed_css)

					# `page-break-*: page;` should be come `page-break-*: always;`
					processed_css = regex.sub(r"(\s+)page-break-(before|after):\s+page;", "\\1page-break-\\2: always;", processed_css)

					# Replace `vw` or `vh` units with percent, a reasonable approximation
					processed_css = regex.sub(r"([0-9\.]+\s*)v(w|h);", r"\1%;", processed_css)

					if processed_css != css:
						file.seek(0)
						file.write(processed_css)
						file.truncate()

		# If we have any endnote files, split them if they contain more than 500 endnotes.
		for endnote_file in endnote_files_to_be_chunked:
			endnote_manifest_href = regex.sub(fr"^{regex.escape(str(work_compatible_epub_dir / 'epub') + os.sep)}", "", str(endnote_file.parent))

			dom = self.get_dom(endnote_file)
			# Before we continue, update any a@href that are only anchors
			for node in dom.xpath("/html/body//a[re:test(@href, '^#')]"):
				node.set_attr("href", f"{endnote_file.name}{node.get_attr('href')}")

			endnotes = dom.xpath("/html/body//*[re:test(@epub:type, '\\bendnote\\b')]")

			# Split our endnotes into chunks of 500 endnotes each
			chunked_endnotes = []
			for i in range(0, len(endnotes), ENDNOTE_CHUNK_SIZE):
				chunked_endnotes.append(endnotes[i:i + ENDNOTE_CHUNK_SIZE])

			# We use our endnotes file dom as as base for the split endnotes. Remove all endnotes and add an empty <ol> to start.
			endnotes_base = deepcopy(dom)
			endnotes_base.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/ol")[0].remove()
			endnotes_base.xpath("/html/body/section[contains(@epub:type, 'endnotes')]")[0].append(se.easy_xml.EasyXmlElement("<ol></ol>"))
			chunk_number = 1
			toc_relative_path = metadata_dom.xpath("/package/manifest/item[re:test(@properties, '\\bnav\\b')]/@href", True)
			toc_dom = self.get_dom(work_compatible_epub_dir / "epub" / toc_relative_path)
			endnotes_manifest_entry = metadata_dom.xpath(f"/package/manifest/item[@href='{endnote_manifest_href}/{endnote_file.name}']")[0]
			endnotes_spine_entry = metadata_dom.xpath(f"/package/spine/itemref[@idref='{endnotes_manifest_entry.get_attr('id')}']")[0]
			endnotes_toc_entry = toc_dom.xpath(f"/html/body//*[re:test(@epub:type, '\\btoc\\b')]//li[./a[re:test(@href, '^{endnote_manifest_href}/{endnote_file.name}')]]")[0]
			endnotes_id_map = {}

			# Update the landmarks entry right away; we only want to point it to the first endnotes file
			# on the assumption that the rest will be in sequence
			endnotes_landmarks_entry = toc_dom.xpath(f"/html/body//*[re:test(@epub:type, '\\blandmarks\\b')]//a[re:test(@href, '^{endnote_manifest_href}/{endnote_file.name}')]")[0]
			endnotes_landmarks_entry.set_attr("href", f"{endnote_manifest_href}/{endnote_file.stem}-1.xhtml")

			# Chunk the endnotes and write the new endnote files to disk
			for chunk in chunked_endnotes:
				current_endnotes_file = deepcopy(endnotes_base)
				ol_node = current_endnotes_file.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/ol")[0]
				chunk_start = ((chunk_number - 1) * ENDNOTE_CHUNK_SIZE) + 1
				chunk_end = chunk_start - 1 + len(chunk)
				new_filename = f"{endnote_file.stem}-{chunk_number}.xhtml"

				if chunk_number > 1:
					ol_node.set_attr("start", str(chunk_start))

				# Add the endnotes to the new endnotes file
				for endnote in chunk:
					ol_node.append(endnote)

				# Generate and set the new title element of the new endnotes file
				endnotes_title = f"Endnotes {format(chunk_start, ',d')}⁠–⁠{format(chunk_end, ',d')}"
				endnotes_header_node = current_endnotes_file.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/*[re:test(@epub:type, '\\btitle\\b')]")[0]
				endnotes_header_node.set_text(endnotes_title)
				endnotes_title_node = current_endnotes_file.xpath("/html/head/title")[0]
				endnotes_title_node.set_text(endnotes_title.replace("⁠", ""))

				# Generate our ID map so that we can update links in the ebook later
				# We inspect ALL IDs, because we might have an ID that isn't on an endnote
				for node in current_endnotes_file.xpath("//*[@id]"):
					endnotes_id_map[node.get_attr("id")] = new_filename

				# Write the new file
				with open(endnote_file.parent / new_filename, "w", encoding="utf-8") as file:
					file.write(current_endnotes_file.to_string())

				# Update the manifest and spine
				endnotes_manifest_entry.lxml_element.addprevious(etree.XML(f"""<item href="{endnote_manifest_href}/{new_filename}" id="{new_filename}" media-type="application/xhtml+xml"/>"""))
				endnotes_spine_entry.lxml_element.addprevious(etree.XML(f"""<itemref idref="{new_filename}"/>"""))

				# Update the ToC
				node_clone = deepcopy(endnotes_toc_entry)
				node_clone_link = node_clone.xpath(".//a")[0]
				node_clone_link.set_attr("href", f"{endnote_manifest_href}/{new_filename}")
				node_clone_link.set_text(endnotes_title.replace("⁠", ""))
				endnotes_toc_entry.lxml_element.addprevious(node_clone.lxml_element)

				chunk_number = chunk_number + 1

			# Update the metadata file with new manifest/spine
			endnotes_manifest_entry.remove()
			endnotes_spine_entry.remove()
			endnotes_toc_entry.remove()

			# Remove the old endnotes file
			endnote_file.unlink()

			# Iterate over all XHTML files to replace ID refs
			for file_path in work_compatible_epub_dir.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)
				has_anchor = False
				for ref in dom.xpath(f"/html/body//a[re:test(@href, '{regex.escape(endnote_file.name)}#')]"):
					anchor = regex.sub("^.+?#", "", ref.get_attr("href"))
					ref.set_attr("href", endnotes_id_map[anchor] + "#" + anchor)
					has_anchor = True

				if has_anchor:
					with open(file_path, "w", encoding="utf-8") as file:
						file.write(dom.to_string())

			# Output the modified the ToC file
			with open(work_compatible_epub_dir / "epub" / toc_relative_path, "w", encoding="utf-8") as file:
				file.write(se.formatting.format_xhtml(toc_dom.to_string()))

		# Output the modified the metadata file so that we can build the kobo book before making more compatibility hacks that aren’t needed on that platform.
		with open(work_compatible_epub_dir / "epub" / self.metadata_file_path.name, "w", encoding="utf-8") as file:
			file.write(se.formatting.format_opf(metadata_dom.to_string()))

		if build_kobo:
			work_kepub_dir = Path(work_dir / (work_compatible_epub_dir.name + ".kepub"))
			shutil.copytree(work_compatible_epub_dir, str(work_kepub_dir), dirs_exist_ok=True)

			for file_path in work_kepub_dir.glob("**/*"):
				# Add a note to the metadata file indicating this is a transform build
				if file_path.name == self.metadata_file_path.name:
					dom = self.get_dom(file_path)

					for node in dom.xpath("/package[contains(@prefix, 'se:')]/metadata"):
						node.append(etree.fromstring("""<meta property="se:transform">kobo</meta>"""))

					with open(file_path, "w", encoding="utf-8") as file:
						file.write(dom.to_string())

				# Kobo .kepub files need each clause wrapped in a special <span> tag to enable highlighting.
				# Do this here. Hopefully Kobo will get their act together soon and drop this requirement.
				if file_path.suffix == ".xhtml":
					kobo.paragraph_counter = 1
					kobo.segment_counter = 1

					# Note: Kobo supports CSS hyphenation, but it can be improved with soft hyphens.
					# However we can't insert them, because soft hyphens break the dictionary search when
					# a word is highlighted.
					dom = self.get_dom(file_path)

					# Don't add spans to the ToC
					if dom.xpath("/html/body//nav[contains(@epub:type, 'toc')]"):
						continue

					# # Remove quote-align spans we inserted above, since Kobo has weird spacing problems with them
					# for node in dom.xpath("/html/body//span[contains(@class, 'quote-align')]"):
					# 	node.unwrap()

					# Inserted koboSpans do not play nicely with CSS that targets all spans, especially poetry.
					# Mark up spans with 'se' so that we can rewrite CSS rules to target only spans we inserted.
					for node in dom.xpath("//span"):
						if node.get_attr("class"):
							node.set_attr("class", node.get_attr("class") + " se")
						else:
							node.set_attr("class", "se")

					# Change 'noteref' to 'endnote' so that popup endnotes work in Kobo. Kobo doesn't understand 'noteref', only 'endnote'.
					for node in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
						node.set_attr("epub:type", node.get_attr("epub:type") + " endnote")

					# Now add the kobo spans
					kobo.add_kobo_spans_to_node(dom.xpath("/html/body")[0].lxml_element)

					# The above will often nest spans within spans, which can surprise CSS selectors present in local.css
					# Try to remove those kinds of nested spans, which are the only children of other spans
					# The xpath uses `local-name()` instead of directly selecting `span` because the `add_kobo_spans_to_node` function
					# adds its spans with the html namespace (i.e. added spans are `html:span`), and EasyXml can't cope with new namespaces
					# after the object has already been instantiated
					for node in dom.xpath("/html/body//*[local-name() = 'span' and parent::span and contains(@class, 'koboSpan') and not(following-sibling::node()[normalize-space(.)] or preceding-sibling::node()[normalize-space(.)])]"):
						if node.get_attr("id"):
							node.parent.set_attr("id", node.get_attr("id"))

						if node.get_attr("class"):
							parent_class = node.parent.get_attr("class")
							if parent_class:
								parent_class = parent_class + " "
							else:
								parent_class = ""

							node.parent.set_attr("class", parent_class + node.get_attr("class"))

						node.unwrap()

					# Kobos don't have fonts that support the ↩ character in endnotes, so replace it with ←
					if dom.xpath("/html/body//section[contains(@epub:type, 'endnotes')]"):
						# We use xpath to select the kobo spans that we just inserted
						for node in dom.xpath("/html/body//a[contains(@epub:type, 'backlink')]/*[local-name()='span']"):
							node.set_text("←")

					xhtml = dom.to_string()

					# Kobos replace no-break hyphens with a weird high hyphen character, so replace that here
					xhtml = xhtml.replace("‑", f"{se.WORD_JOINER}-{se.WORD_JOINER}")

					# Remove namespaces from the output that were added by kobo.add_kobo_spans_to_node
					xhtml = xhtml.replace(" xmlns:html=\"http://www.w3.org/1999/xhtml\"", "")
					xhtml = regex.sub(r"<(/?)html:span", r"<\1span", xhtml)

					with open(file_path, "w", encoding="utf-8") as file:
						file.write(xhtml)

				if file_path.suffix == ".css":
					with open(file_path, "r+", encoding="utf-8") as file:
						css = file.read()
						processed_css = css

						# Retarget span selectors at se spans (i.e. not koboSpans) only.
						# Ignore span followed by a colon (this would be a CSS property like column-span).
						processed_css = regex.sub(r"""(?<=\s)span(?=[^\w:])""", r"""span.se""", processed_css)

						if processed_css != css:
							file.seek(0)
							file.write(processed_css)
							file.truncate()

			# All done, clean the output
			# Note that we don't clean .xhtml files, because the way kobo spans are added means that it will screw up spaces inbetween endnotes.
			for file_path in work_kepub_dir.glob("**/*.opf"):
				se.formatting.format_xml_file(file_path)

			se.epub.write_epub(work_kepub_dir, output_dir / kobo_output_filename)

		# Now work on more compatibility fixes

		# Prep for SVG to PNG conversion. First, remove SVG item properties in the metadata file
		for node in metadata_dom.xpath("/package/manifest/item[contains(@properties, 'svg')]"):
			node.remove_attr_value("properties", "svg")

		# Replace SVGs with PNGs in the manifest
		for node in metadata_dom.xpath("/package/manifest/item[@media-type='image/svg+xml']"):
			node.set_attr("media-type", "image/png")

			for name, value in node.lxml_element.items():
				node.set_attr(name, regex.sub(r"\.svg$", ".png", value))

			# Once iBooks allows srcset we can remove this check
			if not ibooks_srcset_bug_exists:
				filename_2x = Path(regex.sub(r"\.png$", "-2x.png", node.get_attr("href")))
				node.lxml_element.addnext(etree.fromstring(f"""<item href="{filename_2x}" id="{filename_2x.stem}-2x.png" media-type="image/png"/>"""))

		# Now convert the SVGs
		for file_path in work_compatible_epub_dir.glob("**/*.svg"):
			# Convert SVGs to PNGs at 2x resolution
			# Path arguments must be cast to string
			svg2png(url=str(file_path), write_to=str(file_path.parent / (str(file_path.stem) + ".png")))

			if not ibooks_srcset_bug_exists:
				svg2png(url=str(file_path), write_to=str(file_path.parent / (str(file_path.stem) + "-2x.png")), scale=2)

			# Remove the SVG
			(file_path).unlink()

		# We converted svgs to pngs, so replace references
		for file_path in work_compatible_epub_dir.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)
			has_svg = False

			for node in dom.xpath("/html/body//img[re:test(@src, '\\.svg$')]"):
				has_svg = True
				src = node.get_attr("src")
				node.set_attr("src", src.replace(".svg", ".png"))

				if not ibooks_srcset_bug_exists:
					filename = regex.search(r"(?<=/)[^/]+(?=\.svg)", src)[0]
					node.set_attr("srcset", f"{filename}-2x.png 2x, {filename}.png 1x")

			if has_svg:
				with open(file_path, "w", encoding="utf-8") as file:
					file.write(dom.to_string())

		# Recurse over css files to make some compatibility replacements.
		for file_path in work_compatible_epub_dir.glob("**/*.css"):
			with open(file_path, "r+", encoding="utf-8") as file:
				css = file.read()
				processed_css = css

				processed_css = regex.sub(r"^\s*hyphens\s*:\s*(.+)", "\thyphens: \\1\n\tadobe-hyphenate: \\1\n\t-webkit-hyphens: \\1\n\t-moz-hyphens: \\1", processed_css, flags=regex.MULTILINE)
				processed_css = regex.sub(r"^\s*hyphens\s*:\s*none;", "\thyphens: none;\n\tadobe-text-layout: optimizeSpeed; /* For Nook */", processed_css, flags=regex.MULTILINE)

				# We add a 20vh margin to sections without heading elements to drop them down on the page a little.
				# As of 01-2021 the vh unit is not supported on Nook or Kindle (but is on kepub and ibooks).
				processed_css = regex.sub(r"^(\s*)margin-top\s*:\s*20vh;", r"\1margin-top: 5em;", processed_css, flags=regex.MULTILINE)

				# We converted svgs to pngs, so replace references
				processed_css = regex.sub(r"""url\("(.*?)\.svg"\)""", r"""url("\1.png")""", processed_css)

				if processed_css != css:
					file.seek(0)
					file.write(processed_css)
					file.truncate()

		# Replace MathML with either plain characters or an image of the equation
		if metadata_dom.xpath("/package/manifest/*[contains(@properties, 'mathml')]"):
			# We import this late because we don't want to load selenium if we're not going to use it!
			from se import browser # pylint: disable=import-outside-toplevel

			# Remove MathML / describedMath accessibilityFeatures as we’re not going to use MathML
			for node in metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and (text() = 'describedMath' or text() = 'MathML')]"):
				node.remove()

			# We wrap this whole thing in a try block, because we need to call
			# driver.quit() if execution is interrupted (like by ctrl + c, or by an unhandled exception). If we don't call driver.quit(),
			# Firefox will stay around as a zombie process even if the Python script is dead.
			try:
				driver = browser.initialize_selenium_firefox_webdriver()

				mathml_count = 1
				for metadata_item_node in metadata_dom.xpath("//item[contains(@properties, 'mathml')]"):
					filename = Path(work_compatible_epub_dir) / "epub" / metadata_item_node.get_attr("href")

					dom = self.get_dom(filename)

					# Iterate over mathml nodes and try to make some basic replacements to achieve the same appearance
					# but without mathml. If we're able to remove all mathml namespaced elements, we don't need to render it as png.
					for node in dom.xpath("/html/body//m:math"):
						node_clone = deepcopy(node)

						for child in node_clone.xpath("//comment()"):
							child.remove()

						for child in node_clone.xpath(".//m:msup/*[2]"):
							replacement_node = se.easy_xml.EasyXmlElement("<sup/>", {"m": "http://www.w3.org/1998/Math/MathML"})

							child.parent.unwrap()

							mrows = child.xpath(".//m:mrow")
							for mrow in mrows:
								mrow.wrap_with(replacement_node)
								mrow.unwrap()

							if not mrows:
								child.wrap_with(replacement_node)

						for child in node_clone.xpath(".//m:msub/*[2]"):
							replacement_node = se.easy_xml.EasyXmlElement("<sub/>", {"m": "http://www.w3.org/1998/Math/MathML"})

							child.parent.unwrap()

							mrows = child.xpath(".//m:mrow")
							for mrow in mrows:
								mrow.wrap_with(replacement_node)
								mrow.unwrap()

							if not mrows:
								child.wrap_with(replacement_node)

						for child in node_clone.xpath(".//m:mi[not(./*)]"):
							replacement_node = se.easy_xml.EasyXmlElement("<var/>")
							replacement_node.text = child.text
							child.replace_with(replacement_node)

						for child in node_clone.xpath(f".//m:mo[re:test(., '^[{se.INVISIBLE_TIMES}{se.FUNCTION_APPLICATION}]$')]"):
							child.remove()

						for child in node_clone.xpath(".//m:mo[re:test(., '^.$')]"):
							child.text = f"|se:mo|{child.text}|se:mo|"
							child.unwrap()

						for child in node_clone.xpath(".//m:mn"):
							child.unwrap()

						for child in node_clone.xpath(".//m:mrow"):
							child.unwrap()

						# If there are no more mathml-namespaced elements, we succeeded; replace the mathml node
						# with our modified clone
						if not node_clone.xpath(".//*[namespace-uri()='http://www.w3.org/1998/Math/MathML']"):
							# Success!
							node_clone.lxml_element.tail = ""
							# Strip white space we may have added in previous operations,
							# and re-add white space around operators
							for child in node_clone.lxml_element.iter("*"):
								if child.text is not None:
									child.text = child.text.strip()
									child.text = child.text.replace("|se:mo|", " ")
									child.text = regex.sub(r"\s+([\)\]])", r"\1", child.text)
									child.text = regex.sub(r"([\(\[])\s+", r"\1", child.text)
									child.text = regex.sub(r"([0-9])\s+\(", r"\1(", child.text)
								if child.tail is not None:
									child.tail = child.tail.strip()
									child.tail = child.tail.replace("|se:mo|", " ")
									child.tail = regex.sub(r"\s+([\)\]])", r"\1", child.tail)
									child.tail = regex.sub(r"([\(\[])\s+", r"\1", child.tail)
									child.tail = regex.sub(r"([0-9])\s+\(", r"\1(", child.tail)

									if child.tag == "var":
										child.tail = regex.sub(r"\s+([\(\[])", r"\1", child.tail)

							# Remove leading spaces from the root
							if node_clone.lxml_element.text is not None:
								node_clone.lxml_element.text = node_clone.lxml_element.text.lstrip()

							# Remove trailing spaces from the tail of the last element
							for child in node_clone.xpath("./*[last()]"):
								if child.lxml_element.tail is not None:
									child.lxml_element.tail = child.lxml_element.tail.rstrip()

							# If the node has no children, strip its text value
							if not node_clone.children:
								node_clone.lxml_element.text = node_clone.lxml_element.text.strip()

							node.replace_with(node_clone)
							node_clone.unwrap()
						else:
							# Failure! Abandon all hope, and use Firefox to convert the MathML to PNG.
							# First, remove the m: namespace shorthand and add the actual namespace to our fragment
							namespaced_line = regex.sub(r"<(/?)m:", "<\\1", node.to_string())
							namespaced_line = namespaced_line.replace("<math", "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"")

							# Have Firefox render the fragment
							se.images.render_mathml_to_png(driver, namespaced_line, work_compatible_epub_dir / "epub" / "images" / f"mathml-{mathml_count}.png", work_compatible_epub_dir / "epub" / "images" / f"mathml-{mathml_count}-2x.png")

							img_node = se.easy_xml.EasyXmlElement("<img/>", {"epub": "http://www.idpf.org/2007/ops"})
							img_node.set_attr("class", "mathml epub-type-se-image-color-depth-black-on-transparent")
							img_node.set_attr("epub:type", "se:image.color-depth.black-on-transparent")
							img_node.set_attr("src", f"../images/mathml-{mathml_count}-2x.png")
							if node.get_attr("alttext"):
								img_node.set_attr("alt", node.get_attr("alttext"))

							if ibooks_srcset_bug_exists:
								# Calculate the "normal" height/width from the 2x image
								ifile = work_compatible_epub_dir / "epub" / "images" / f"mathml-{mathml_count}-2x.png"
								image = Image.open(ifile)
								img_width = image.size[0]
								img_height = image.size[1]

								# If either dimension is odd, add a pixel
								right = img_width % 2
								bottom = img_height % 2

								# If either dimension was odd, expand the canvas
								if (right != 0 or bottom != 0):
									border = (0, 0, right, bottom)
									image = ImageOps.expand(image, border)
									image.save(ifile)

								# Get the "display" dimensions
								img_width = img_width // 2
								img_height = img_height // 2

								img_node.set_attr("width", str(img_width))
								img_node.set_attr("height", str(img_height))

								# We don't need the 1x file if we're not using srcset
								os.unlink(work_compatible_epub_dir / "epub" / "images" / f"mathml-{mathml_count}.png")

								# Add any new MathML images we generated to the manifest
								for metadata_manifest_node in metadata_dom.xpath("/package/manifest"):
									metadata_manifest_node.append(etree.fromstring(f"""<item href="images/mathml-{mathml_count}-2x.png" id="mathml-{mathml_count}-2x.png" media-type="image/png"/>"""))
							else:
								img_node.set_attr("srcset", f"../images/mathml-{mathml_count}-2x.png 2x, ../images/mathml-{mathml_count}.png 1x")

								# Add any new MathML images we generated to the manifest
								for metadata_manifest_node in metadata_dom.xpath("/package/manifest"):
									metadata_manifest_node.append(etree.fromstring(f"""<item href="images/mathml-{mathml_count}.png" id="mathml-{mathml_count}.png" media-type="image/png"/>"""))
									metadata_manifest_node.append(etree.fromstring(f"""<item href="images/mathml-{mathml_count}-2x.png" id="mathml-{mathml_count}-2x.png" media-type="image/png"/>"""))

							node.replace_with(img_node)

							mathml_count = mathml_count + 1

					# Do we still have mathml in this file?. If not, remove the namespace and also the `mathml` propery from the metadata file.
					if not dom.xpath("/html/body//*[namespace-uri()='http://www.w3.org/1998/Math/MathML']"):
						# Remove unused namespaces, e.g. mathml
						etree.cleanup_namespaces(dom.etree)

						# Update the metadata file to remove the `mathml` property
						metadata_item_node.remove_attr_value("properties", "mathml")

					with open(filename, "w", encoding="utf-8") as file:
						file.write(dom.to_string())

			except KeyboardInterrupt as ex:
				# Bubble the exception up, but proceed to `finally` so we quit the driver
				raise ex
			finally:
				try:
					driver.quit()
				except Exception:
					# We might get here if we ctrl + c before selenium has finished initializing the driver
					pass

		# Include cover metadata for older ereaders
		for cover_id in metadata_dom.xpath("//item[@properties=\"cover-image\"]/@id"):
			for node in metadata_dom.xpath("/package/metadata"):
				node.append(etree.fromstring(f"""<meta content="{cover_id}" name="cover"/>"""))

		# Add metadata to the metadata file indicating this file is a Standard Ebooks compatibility build
		for node in metadata_dom.xpath("/package[contains(@prefix, 'se:')]/metadata"):
			node.append(etree.fromstring("""<meta property="se:transform">compatibility</meta>"""))

		# Generate our NCX file for compatibility with older ereaders.
		# First find the ToC file.
		toc_filename = metadata_dom.xpath("//item[@properties=\"nav\"][1]/@href", True)
		for node in metadata_dom.xpath("/package/spine"):
			node.set_attr("toc", "ncx")

		for node in metadata_dom.xpath("/package/manifest"):
			node.append(etree.fromstring("""<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml"/>"""))

		# Now use an XSLT transform to generate the NCX
		with importlib_resources.path("se.data", "navdoc2ncx.xsl") as navdoc2ncx_xsl_filename:
			toc_tree = se.epub.convert_toc_to_ncx(work_compatible_epub_dir, toc_filename, navdoc2ncx_xsl_filename)

		# Convert the <nav> landmarks element to the <guide> element in the metadata file
		guide_root_node = se.easy_xml.EasyXmlElement("<guide/>")
		for node in toc_tree.xpath("//nav[@epub:type=\"landmarks\"]/ol/li/a"):
			ref_node = se.easy_xml.EasyXmlElement("<reference/>")

			ref_node.set_attr("title", node.text)
			ref_node.set_attr("href", node.get_attr("href"))
			if node.get_attr("epub:type"):
				# Set the `type` attribute and remove any z3998 items, as well as front/body/backmatter
				ref_node.set_attr("type", node.get_attr("epub:type"))
				ref_node.set_attr("type", regex.sub(r"\s*\b(front|body|back)matter\b\s*", "", ref_node.get_attr("type")))
				ref_node.set_attr("type", regex.sub(r"\s*\bz3998:.+\b\s*", "", ref_node.get_attr("type")))

			if ref_node.get_attr("type"):
				# Remove epub:types that are not in the allow list, see http://idpf.org/epub/20/spec/OPF_2.0.1_draft.htm#Section2.6
				new_node_types = []

				for node_type in ref_node.get_attr("type").split():
					if node_type in ("acknowledgements", "bibliography", "colophon", "copyright-page", "cover", "dedication", "epigraph", "foreword", "glossary", "index", "loi", "lot", "notes", "preface", "bodymatter", "titlepage", "toc"):
						new_node_types.append(node_type)
					else:
						new_node_types.append(f"other.{node_type}")

				ref_node.set_attr("type", " ".join(new_node_types))

				# We add the `text` attribute to the titlepage to tell the reader to start there
				if ref_node.get_attr("type") == "titlepage":
					ref_node.set_attr("type", "title-page text")

				guide_root_node.append(ref_node)

		# Append the guide to the <package> element
		if guide_root_node.children:
			for node in metadata_dom.xpath("/package"):
				node.append(guide_root_node)

		# Guide is done, now write the metadata file and clean it.
		# Output the modified metadata file before making more compatibility hacks.
		with open(work_compatible_epub_dir / "epub" / self.metadata_file_path.name, "w", encoding="utf-8") as file:
			# Nook has a bug where the cover image <meta> element MUST have attributes in a certain order
			# See:
			# https://nachtimwald.com/2011/08/21/nook-covers-not-showing-up/
			# https://github.com/standardebooks/tools/issues/577
			# Change the order with a regex before writing out the file
			xml = se.formatting.format_opf(metadata_dom.to_string())
			xml = regex.sub(r"""<meta content="([^"]+?)" name="cover"/>""", r"""<meta name="cover" content="\1"/>""", xml)
			file.write(xml)

		# All done, clean the output
		for filepath in se.get_target_filenames([work_compatible_epub_dir], (".xhtml", ".ncx")):
			try:
				se.formatting.format_xml_file(filepath)
			except se.SeException as ex:
				raise se.InvalidXhtmlException(f"{ex}. File: [path][link={filepath}]{filepath}[/][/]") from ex

		# Write the compatible epub
		if not check_only:
			se.epub.write_epub(work_compatible_epub_dir, output_dir / compatible_epub_output_filename)

		# Run checks, if specified
		build_messages = []

		if run_epubcheck:
			# Path arguments must be cast to string for Windows compatibility.
			with importlib_resources.path("se.data.epubcheck", "epubcheck.jar") as jar_path:
				# We have to use a temp file to hold stdout, because if the output is too large for the output buffer in subprocess.run() (and thus popen()) it will be truncated
				with tempfile.TemporaryFile() as stdout:
					# We can't check the return code, because if only warnings are returned then epubcheck will return 0 (success)
					subprocess.run(["java", "-jar", str(jar_path), "--quiet", "--out", "-", "--mode", "exp", str(work_compatible_epub_dir)], stdout=stdout, stderr=subprocess.DEVNULL, check=False)

					stdout.seek(0)
					output = stdout.read().decode().strip()

					epubcheck_dom = se.easy_xml.EasyXmlTree(output)

					messages = epubcheck_dom.xpath("/jhove/repInfo/messages/message")

					if messages:
						# Save the epub output so the user can inspect it
						epub_debug_dir = __save_debug_epub(work_compatible_epub_dir)

						# Replace instances of the temp epub path with our permanent epub path
						# Note that epubcheck always appends ".epub" to the dir name
						output = output.replace(str(work_compatible_epub_dir) + ".epub", str(epub_debug_dir))

						for message in messages:
							error_text = regex.search(r"(\[(.+)\]), ", message.text)
							file_text = regex.search(r"\], (.+?) \(([0-9]+)-([0-9]+)\)$", message.text)

							if file_text:
								file_path = epub_debug_dir / file_text[1]
								build_messages.append(BuildMessage("epubcheck", message.get_attr("id"), error_text[2], file_path, file_text[2], file_text[3]))
							else:
								build_messages.append(BuildMessage("epubcheck", message.get_attr("id"), error_text[2]))

						raise se.BuildFailedException("[bash]epubcheck[/] failed.", build_messages)

			# Now run the Nu Validator
			with importlib_resources.path("se.data.vnu", "vnu.jar") as jar_path:
				# We have to use a temp file to hold stdout, because if the output is too large for the output buffer in subprocess.run() (and thus popen()) it will be truncated
				with tempfile.TemporaryFile() as stdout:
					subprocess.run(["java", "-jar", str(jar_path), "--format", "xml", str(self.epub_root_path / "epub" / "text")], stdout=stdout, stderr=stdout, check=False)

					stdout.seek(0)
					vnu_dom = se.easy_xml.EasyXmlTree(stdout.read().decode().strip())

					# The Nu Validator will return errors for epub-specific attributes (like `epub:prefix` and `epub:type`) because they're
					# not defined in the XHTML5 spec. So, we simply filter out those errors.
					# We also filter out "section lacks heading" messages, because they are warnings and we may have sections without headings (like dedications, frontispieces)
					# Also filter out warnings about potentially bad values for datetimes, which are raised for years < 1000. This can occur in works like Omega by Camille Flammarion.
					# Also filter out errors about <p> being a child of <hgroup>. The spec changed but our current VNU version has not caught up.
					messages = vnu_dom.xpath("/messages/*[not(re:test(./message, '^(Attribute (prefix|type) not allowed|(Section|Article) lacks heading.|Potentially bad value.+datetime|Element p not allowed as child of element hgroup in this context.)'))]")

					for message in messages:
						message_text = message.xpath("./message")[0].inner_xml()
						submessage = None

						# Colorize output
						message_text = regex.sub(r"([Aa]ttribute) <code>", r"\1 [attr]", message_text)
						message_text = regex.sub(r"([Ee]lement) <code>(.+?)</code>", r"\1 [xhtml]<\2>[/]", message_text)
						message_text = message_text.replace("<code>", "[xhtml]")
						message_text = message_text.replace("</code>", "[/]")
						message_text = unescape(message_text)

						# Do we have a submessage?
						extract = message.xpath("./extract")

						if extract:
							# The extract will contain the offending line plus some lines around it.
							# The offending line is marked up with <m> so pull it out and discard the surrounding lines.
							target = extract[0].xpath("./m")
							if target:
								submessage = target[0].inner_xml()
							else:
								submessage = extract[0].inner_xml()

							submessage = unescape(submessage).strip()
							submessage = [submessage]

						file_path = Path(regex.sub(r"^file:", "", message.get_attr("url")))
						build_messages.append(BuildMessage("vnu", "", message_text, file_path, message.get_attr("last-line"), message.get_attr("first-column"), submessage))

					if messages:
						raise se.BuildFailedException("[bash]vnu[/] failed.", build_messages)

		# Now run Ace
		if run_ace:
			# We have to use a temp file to hold stdout, because if the output is too large for the output buffer in subprocess.run() (and thus popen()) it will be truncated
			with tempfile.TemporaryFile() as stdout:
				try:
					ace_result = subprocess.run(["ace", "--silent", str(work_compatible_epub_dir)], stdout=stdout, stderr=subprocess.DEVNULL, check=False)
					ace_result.check_returncode()

					stdout.seek(0)
					ace_dom = json.loads(stdout.read().decode().strip())
					output = ""

					# If Ace failed, print Ace output to the console in a nice way
					if ace_dom["earl:result"]["earl:outcome"] != "pass":
						# Save the epub output so the user can inspect it
						epub_debug_dir = __save_debug_epub(work_compatible_epub_dir)

						# Ace outputs a flat list of errors, so here we try to arrange them so that each combination of (file, error)
						# has a list of errors below it, instead of repeating the filename and code over and over.
						# A dict whose keys are a tuple of (filename, code) and whose values are an array of (message, html)
						file_messages: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}

						for assertion in ace_dom["assertions"]:
							if assertion["earl:result"]["earl:outcome"] != "pass":
								file = epub_debug_dir / self.content_path.name / assertion["earl:testSubject"]["url"]

								for file_assertion in assertion["assertions"]:
									if file_assertion["earl:result"]["earl:outcome"] != "pass":
										emit_result = True

										# Ace fails a test if the language tag is a private-use subtag, like lang="x-alien"
										# Don't include those false positives in the results.
										# See https://github.com/daisy/ace/issues/169
										if file_assertion["earl:test"]["dct:title"] == "valid-lang" and "lang=\"x-" in file_assertion["earl:result"]["html"]:
											emit_result = False

										# Ace fails if an <article> doesn't have a `role` that matches its `epub:type`; but epubcheck
										# will complain if the `role` is not allowed on that element. This mostly affects <article>s.
										# We choose to satisfy epubcheck first by not including `role` on <article>, then ignoring Ace's complaint.
										# See https://github.com/daisy/ace/issues/354
										# See https://standardebooks.org/ebooks/robert-frost/north-of-boston
										if file_assertion["earl:test"]["dct:title"] == "epub-type-has-matching-role" and "<article" in file_assertion["earl:result"]["html"]:
											emit_result = False

										if emit_result:
											code = file_assertion["earl:test"]["dct:title"]
											if (str(file), code) not in file_messages:
												file_messages[(str(file), code)] = []

											file_messages[(str(file), code)].append((file_assertion["earl:result"]["dct:description"], file_assertion["earl:result"]["html"] if "html" in file_assertion["earl:result"].keys() else ""))

						# Unpack our sorted messages for output
						for (file_path_str, code), message_list in file_messages.items():
							item_messages = []
							for (message, html) in message_list:
								if html:
									# Ace output includes namespaces on each element, remove them
									html = regex.sub(r" xmlns(?::.*?)?=\"[^\"]+?\"", "", html)
									item_messages.append(html)

							# message_list[0][n] will always be the same so [0][0] suffices
							build_messages.append(BuildMessage("ace", code, message_list[0][0], Path(file_path_str), None, None, item_messages))

						if build_messages:
							raise se.BuildFailedException("[bash]ace[/] failed.", build_messages)

						# We had to copy the epub dir to a temp dir so that we could get the real file paths for ace messages.
						# But if we got here, then Ace had no real messages to emit, so we have to clean up the temp dir we created.
						shutil.rmtree(epub_debug_dir, ignore_errors=True)

						if output:
							raise se.BuildFailedException(f"[bash]ace[/] failed with:\n\n{output.strip()}")

				except subprocess.CalledProcessError as ex:
					raise se.BuildFailedException("[bash]ace[/] failed.") from ex

		# Epubcheck and Ace passed!

		# If we're only checking, quit now
		if check_only:
			return

		if build_kindle:
			# Kindle doesn't go more than 2 levels deep for ToC, so flatten it here.
			with open(work_compatible_epub_dir / "epub" / toc_filename, "r+", encoding="utf-8") as file:
				dom = se.easy_xml.EasyXmlTree(file.read())

				for node in dom.xpath("//ol/li/ol/li/ol"):
					node.lxml_element.getparent().addnext(node.lxml_element)
					node.unwrap()

				file.seek(0)
				file.write(dom.to_string())
				file.truncate()

			# Rebuild the NCX
			with importlib_resources.path("se.data", "navdoc2ncx.xsl") as navdoc2ncx_xsl_filename:
				se.epub.convert_toc_to_ncx(work_compatible_epub_dir, toc_filename, navdoc2ncx_xsl_filename)

			# Clean just the ToC and NCX
			for filepath in [work_compatible_epub_dir / "epub" / "toc.ncx", work_compatible_epub_dir / "epub" / toc_filename]:
				se.formatting.format_xml_file(filepath)

			# Do some compatibility replacements
			for file_path in work_compatible_epub_dir.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)
				replace_shy_hyphens = False

				# Remove se:image.color-depth.black-on-transparent, as Calibre removes media queries so this will *always* be invisible
				for node in dom.xpath("/html/body//img[contains(@class, 'epub-type-se-image-color-depth-black-on-transparent') or contains(@epub:type, 'se:image.color-depth.black-on-transparent')]"):
					if node.get_attr("class"):
						node.set_attr("class", node.get_attr("class").replace("epub-type-se-image-color-depth-black-on-transparent", "").replace("epub-type-se-image-style-realistic", ""))

					if node.get_attr("epub:type"):
						node.set_attr("epub:type", node.get_attr("epub:type").replace("se:image.color-depth.black-on-transparent", "").replace("se:image.style.realistic", ""))

				# If the only element on the page is an absolutely positioned image, Kindle will ignore the file in the reading order.
				# So, in that case we add a `<div>` with some text content to fool Kindle.
				# However, Calibre will remove `font-size: 0` so we have to use `overflow` to hide the div.
				if dom.xpath("/html/body/*[(name() = 'section' or name() = 'article') and not(contains(@epub:type, 'titlepage'))]/*[(name() = 'figure' or name() = 'img') and not(preceding-sibling::node()[normalize-space(.)] or following-sibling::node()[normalize-space(.)])]"):
					for node in dom.xpath("/html/body"):
						node.prepend(etree.fromstring("""<div style="height: 0; width: 0; overflow: hidden; line-height: 0; font-size: 0;">x</div>"""))

				# If this is the endnotes file, convert endnotes to Kindle popup compatible notes
				# To do this, we move the backlink to the front of the endnote's first <p> (or we create a first <p> if there
				# isn't one) and change its text to the note number instead of a back arrow.
				# Then, we remove all endnote <li> wrappers and put their IDs on the first <p> child, leaving just a series of <p>s
				if dom.xpath("/html/body//section[contains(@epub:type, 'endnotes')]"):
					# While Kindle now supports soft hyphens, popup endnotes break words but don't insert the hyphen characters.  So for now, remove soft hyphens from the endnotes file.
					replace_shy_hyphens = True

					# Loop over each endnote and move the ending backlink to the front of the endnote for Kindles
					note_container = dom.xpath("/html/body//section[contains(@epub:type, 'endnotes')]/ol")[0]

					note_number = 1

					if note_container.get_attr("start"):
						note_number = int(note_container.get_attr("start"))

					for endnote in dom.xpath("//li[re:test(@epub:type, '\\b(endnote|footnote)\\b')]"):
						first_p = endnote.xpath("(./p[not(preceding-sibling::*)])[1]")

						# Sometimes there is no leading <p> tag (for example, if the endnote starts with a blockquote
						# If that's the case, just insert one in front.
						if first_p:
							first_p = first_p[0]
						else:
							first_p = se.easy_xml.EasyXmlElement("<p/>")
							endnote.prepend(first_p)

						first_p.set_attr("id", endnote.get_attr("id"))

						for node in endnote.xpath(".//a[contains(@epub:type, 'backlink')]"):
							node.set_text(str(note_number))
							node.lxml_element.tail = ". "
							first_p.prepend(node)

						# Sometimes backlinks were in their own <p> tag, which is now empty. Remove those.
						for node in endnote.xpath(".//p[not(normalize-space(.))]"):
							node.remove()

						# Now remove the wrapping li node from the note
						endnote.unwrap()

						note_number = note_number + 1

					# Remove the containing <ol>, since the children are just <p>s now
					note_container.unwrap()

				# Remove the epub:type attribute, as Calibre turns it into just "type"
				for node in dom.xpath("//*[@epub:type]"):
					node.remove_attr("epub:type")

				# Kindle doesn't recognize most zero-width spaces or word joiners, so just remove them.
				# It does recognize the word joiner character, but only in the old mobi7 format.  The new format renders them as spaces.
				xhtml = dom.to_string().replace(se.ZERO_WIDTH_SPACE, "")

				if replace_shy_hyphens:
					xhtml = xhtml.replace(se.SHY_HYPHEN, "")

				# Add soft hyphens, but not to the ToC
				if not dom.xpath("/html[re:test(@epub:prefix, '[\\s\\b]se:[\\s\\b]')]/body/nav[contains(@epub:type, 'toc')]"):
					xhtml = se.typography.hyphenate(xhtml, None, True)

				with open(file_path, "w", encoding="utf-8") as file:
					file.write(se.formatting.format_xhtml(xhtml))

			# Include compatibility CSS
			with open(work_compatible_epub_dir / "epub" / "css" / "core.css", "a", encoding="utf-8") as core_css_file:
				with importlib_resources.open_text("se.data.templates", "kindle.css", encoding="utf-8") as compatibility_css_file:
					core_css_file.write("\n" + compatibility_css_file.read())

			# Build an epub file we can send to Calibre
			se.epub.write_epub(work_compatible_epub_dir, work_dir / compatible_epub_output_filename)

			# Generate the Kindle file
			# We place it in the work directory because later we have to update the asin, and the mobi.update_asin() function will write to the final output directory
			cover_path = None
			for href in metadata_dom.xpath("//item[@properties=\"cover-image\"]/@href"):
				cover_path = work_compatible_epub_dir / "epub" / href

			# Path arguments must be cast to string for Windows compatibility.
			try:
				calibre_args = [str(ebook_convert_path), str(work_dir / compatible_epub_output_filename), str(work_dir / kindle_output_filename), "--pretty-print", "--no-inline-toc", "--max-toc-links=0", "--prefer-metadata-cover"]

				if cover_path:
					calibre_args.append(f"--cover={cover_path}")

				calibre_result = subprocess.run(calibre_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
				calibre_result.check_returncode()
			except subprocess.CalledProcessError as ex:
				output = calibre_result.stdout.decode().strip()

				raise se.BuildFailedException(f"[bash]ebook-convert[/] failed with:\n{output}") from ex

			# Success, extract the Kindle cover thumbnail

			# Update the ASIN in the generated file
			mobi.update_asin(asin, work_dir / kindle_output_filename, output_dir / kindle_output_filename)

			# Extract the thumbnail
			if os.path.isfile(work_compatible_epub_dir / "epub" / "images" / "cover.jpg"):
				kindle_cover_thumbnail = Image.open(work_compatible_epub_dir / "epub" / "images" / "cover.jpg")
				kindle_cover_thumbnail = kindle_cover_thumbnail.convert("RGB") # Remove alpha channel from PNG if necessary
				kindle_cover_thumbnail = kindle_cover_thumbnail.resize((432, 648))
				kindle_cover_thumbnail.save(output_dir / f"thumbnail_{asin}_EBOK_portrait.jpg")

	# Build is all done!
	# Since we made heavy changes to the ebook's dom, flush the dom cache in case we use this class again
	self._dom_cache = [] # pylint: disable=protected-access
	self._file_cache = [] # pylint: disable=protected-access
