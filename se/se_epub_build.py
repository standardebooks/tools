#!/usr/bin/env python3
"""
This module contains the build function.

Strictly speaking, the build() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put it in a separate file.
"""

import fnmatch
import os
import shutil
import subprocess
import tempfile
from distutils.dir_util import copy_tree
from copy import deepcopy
from hashlib import sha1
from pathlib import Path
import importlib_resources

from cairosvg import svg2png
from natsort import natsorted
from PIL import Image, ImageOps
import lxml.cssselect
import lxml.etree as etree
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
ARIA_ROLES = ["afterword", "appendix", "biblioentry", "bibliography", "chapter", "colophon", "conclusion", "dedication", "epilogue", "foreword", "introduction", "noteref", "part", "preface", "prologue", "subtitle", "toc"]

def build(self, run_epubcheck: bool, build_kobo: bool, build_kindle: bool, output_directory: Path, proof: bool, build_covers: bool) -> None:
	"""
	Entry point for `se build`
	"""

	ibooks_srcset_bug_exists = True

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

	if run_epubcheck:
		if not shutil.which("java"):
			raise se.MissingDependencyException("Couldn’t locate [bash]java[/]. Is it installed?")

	# Check the output directory and create it if it doesn't exist
	try:
		output_directory = output_directory.resolve()
		output_directory.mkdir(parents=True, exist_ok=True)
	except Exception as ex:
		raise se.FileExistsException(f"Couldn’t create output directory: [path][link=file://{output_directory}]{output_directory}[/][/].") from ex

	# All clear to start building!

	# Make a copy of the metadata dom because we'll be making changes
	metadata_dom = deepcopy(self.metadata_dom)

	with tempfile.TemporaryDirectory() as temp_directory:
		work_directory = Path(temp_directory)
		work_epub_root_directory = work_directory / "src"

		copy_tree(self.path, str(work_directory))
		try:
			shutil.rmtree(work_directory / ".git")
		except Exception:
			pass

		# By convention the ASIN is set to the SHA-1 sum of the book's identifying URL
		try:
			identifier = metadata_dom.xpath("//dc:identifier")[0].inner_xml().replace("url:", "")
			asin = sha1(identifier.encode("utf-8")).hexdigest()
		except Exception as ex:
			raise se.InvalidSeEbookException(f"Missing [xml]<dc:identifier>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/].") from ex

		if not metadata_dom.xpath("//dc:title"):
			raise se.InvalidSeEbookException(f"Missing [xml]<dc:title>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/].")

		output_filename = identifier.replace("https://standardebooks.org/ebooks/", "").replace("/", "_")
		url_author = ""
		for author in metadata_dom.xpath("//dc:creator"):
			url_author = url_author + se.formatting.make_url_safe(author.inner_xml()) + "_"

		url_author = url_author.rstrip("_")

		compatible_epub_output_filename = f"{output_filename}{'.proof' if proof else ''}.epub"
		epub_output_filename = f"{output_filename}{'.proof' if proof else ''}_advanced.epub"
		kobo_output_filename = f"{output_filename}{'.proof' if proof else ''}.kepub.epub"
		kindle_output_filename = f"{output_filename}{'.proof' if proof else ''}.azw3"

		# Clean up old output files if any
		se.quiet_remove(output_directory / f"thumbnail_{asin}_EBOK_portrait.jpg")
		se.quiet_remove(output_directory / "cover.jpg")
		se.quiet_remove(output_directory / "cover-thumbnail.jpg")
		se.quiet_remove(output_directory / compatible_epub_output_filename)
		se.quiet_remove(output_directory / epub_output_filename)
		se.quiet_remove(output_directory / kobo_output_filename)
		se.quiet_remove(output_directory / kindle_output_filename)

		# Are we including proofreading CSS?
		if proof:
			with open(work_epub_root_directory / "epub" / "css" / "local.css", "a", encoding="utf-8") as local_css_file:
				with importlib_resources.open_text("se.data.templates", "proofreading.css", encoding="utf-8") as proofreading_css_file:
					local_css_file.write(proofreading_css_file.read())

		# Update the release date in the metadata and colophon
		if self.last_commit:
			last_updated_iso = regex.sub(r"\.[0-9]+$", "", self.last_commit.timestamp.isoformat()) + "Z"
			last_updated_iso = regex.sub(r"\+.+?Z$", "Z", last_updated_iso)
			# In the line below, we can't use %l (unpadded 12 hour clock hour) because it isn't portable to Windows.
			# Instead we use %I (padded 12 hour clock hour) and then do a string replace to remove leading zeros.
			last_updated_friendly = f"{self.last_commit.timestamp:%B %e, %Y, %I:%M <abbr class=\"time eoc\">%p</abbr>}".replace(" 0", " ")
			last_updated_friendly = regex.sub(r"\s+", " ", last_updated_friendly).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

			# Set modified date in the metadata file
			for node in metadata_dom.xpath("//meta[@property='dcterms:modified']"):
				node.set_text(last_updated_iso)

			with open(work_epub_root_directory / "epub" / self.metadata_file_path.name, "w", encoding="utf-8") as file:
				file.seek(0)
				file.write(metadata_dom.to_string())
				file.truncate()

			# Update the colophon with release info
			# If there's no colophon, skip this
			if os.path.isfile(work_epub_root_directory / "epub" / "text" / "colophon.xhtml"):
				with open(work_epub_root_directory / "epub" / "text" / "colophon.xhtml", "r+", encoding="utf-8") as file:
					xhtml = file.read()

					xhtml = xhtml.replace("<p>The first edition of this ebook was released on<br/>", f"<p>This edition was released on<br/>\n\t\t\t<b>{last_updated_friendly}</b><br/>\n\t\t\tand is based on<br/>\n\t\t\t<b>revision {self.last_commit.short_sha}</b>.<br/>\n\t\t\tThe first edition of this ebook was released on<br/>")

					file.seek(0)
					file.write(xhtml)
					file.truncate()

		# Output the pure epub3 file
		se.epub.write_epub(work_epub_root_directory, output_directory / epub_output_filename)

		# Now add compatibility fixes for older ereaders.

		# Include compatibility CSS
		with open(work_epub_root_directory / "epub" / "css" / "core.css", "a", encoding="utf-8") as core_css_file:
			with importlib_resources.open_text("se.data.templates", "compatibility.css", encoding="utf-8") as compatibility_css_file:
				core_css_file.write(compatibility_css_file.read())

		# Simplify CSS and tags
		total_css = ""

		# Simplify the CSS first.  Later we'll update the document to match our simplified selectors.
		# While we're doing this, we store the original css into a single variable so we can extract the original selectors later.
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename_string in fnmatch.filter(filenames, "*.css"):
				filename = Path(root) / filename_string
				with open(filename, "r+", encoding="utf-8") as file:
					css = file.read()

					# Before we do anything, we process a special case in core.css
					if filename.name == "core.css":
						css = regex.sub(r"abbr{.+?}", "", css, flags=regex.DOTALL)

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
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename_string in fnmatch.filter(filenames, "*.xhtml"):
				filename = (Path(root) / filename_string).resolve()

				dom = self.get_dom(filename)

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
								target_element_selector = ''.join(split_selector[0:2])

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
					if "[epub|type" in selector:
						for namespace_selector in regex.findall(r"\[epub\|type\~\=\"[^\"]*?\"\]", selector):

							for element in dom.css_select(namespace_selector):
								new_class = regex.sub(r"^\.", "", se.formatting.namespace_to_class(namespace_selector))
								current_class = element.get_attr("class") or ""

								if new_class not in current_class:
									current_class = f"{current_class} {new_class}".strip()
									element.set_attr("class", current_class)

					if "abbr" in selector:
						try:
							# Convert <abbr> to <span>
							for element in dom.css_select(selector):
								# Create a new element and move this element's children in to it
								span = se.easy_xml.EasyXmlElement("<span/>")
								span.text = element.text
								span.attrs = element.attrs

								for child in element.children:
									span.append(child)

								element.replace_with(span)

						except lxml.cssselect.ExpressionError:
							# This gets thrown if we use pseudo-elements, which lxml doesn't support
							continue
						except lxml.cssselect.SelectorSyntaxError as ex:
							raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: [css]{selector}[/]. Exception: {ex}")

				# Now we just remove all remaining abbr tags that did not get converted to spans
				for node in dom.xpath("/html/body//abbr"):
					node.unwrap()

		# Done simplifying CSS and tags!

		# Extract cover and cover thumbnail
		cover_local_path = metadata_dom.xpath("/package/manifest/item[@properties='cover-image'][1]/@href", True)

		# If we have a cover, convert it to JPG
		if cover_local_path:
			cover_work_path = work_epub_root_directory / "epub" / cover_local_path

			if cover_work_path.suffix == ".svg" or cover_work_path.suffix == ".png":
				# If the cover is SVG, conver to PNG first
				if cover_work_path.suffix == ".svg":
					svg2png(url=str(cover_work_path), write_to=str(work_directory / "cover.png"))

				# Now convert PNG to JPG
				cover = Image.open(work_directory / "cover.png")
				cover = cover.convert("RGB") # Remove alpha channel from PNG if necessary
				cover.save(work_epub_root_directory / "epub" / "images" / "cover.jpg")

				# Save <output-dir>/cover-thumbnail.jpg while we're here
				if build_covers:
					cover = cover.resize((COVER_THUMBNAIL_WIDTH, COVER_THUMBNAIL_HEIGHT))
					cover.save(output_directory / "cover-thumbnail.jpg")

				cover_work_path.unlink()

				# Replace .svg/.png with .jpg in the metadata
				for node in metadata_dom.xpath(f"/package/manifest//item[contains(@href, '{cover_local_path}')]"):
					for name, value in node.lxml_element.items():
						node.set_attr(name, regex.sub(r"\.(svg|png)$", ".jpg", value))

					node.set_attr("media-type", "image/jpeg")

			elif cover_work_path.suffix == ".jpg":
				# If we start from JPG then it's much easier, just resize the thumbnail
				if build_covers:
					cover = Image.open(cover_work_path)
					cover = cover.resize((COVER_THUMBNAIL_WIDTH, COVER_THUMBNAIL_HEIGHT))
					cover.save(output_directory / "cover-thumbnail.jpg")

			if build_covers:
				# Copy the final cover.jpg to the output dir
				cover_work_path = Path(regex.sub(r"\.(svg|png)$", ".jpg", str(cover_work_path)))
				shutil.copy2(cover_work_path, output_directory / cover_work_path.name)

		# Remove SVG item properties in the metadata file since we will convert all SVGs to PNGs further down
		for node in metadata_dom.xpath("/package/manifest/item[contains(@properties, 'svg')]"):
			node.remove_attr_value("properties", "svg")

		# Add an element noting the version of the se tools that built this ebook, but only if the se vocab prefix is present
		for node in metadata_dom.xpath("/package[contains(@prefix, 'se:')]/metadata"):
			node.append(etree.fromstring(f"<meta property=\"se:built-with\">{se.VERSION}</meta>"))

		# Google Play Books chokes on https XML namespace identifiers (as of at least 2017-07)
		for node in metadata_dom.xpath("/package[contains(@prefix, 'se:')]"):
			node.set_attr('prefix', node.get_attr('prefix').replace("https://standardebooks.org/vocab/1.0", "http://standardebooks.org/vocab/1.0"))

		# Add replace SVGs with PNGs in the manifest
		# The actual conversion occurs later
		for node in metadata_dom.xpath("/package/manifest/item[@media-type='image/svg+xml']"):
			node.set_attr("media-type", "image/png")

			for name, value in node.lxml_element.items():
				node.set_attr(name, regex.sub(r"\.svg$", ".png", value))

			# Once iBooks allows srcset we can remove this check
			if not ibooks_srcset_bug_exists:
				filename_2x = Path(regex.sub(r"\.png$", "-2x.png", node.get_attr("href")))
				node.lxml_element.addnext(etree.fromstring(f"""<item href="{filename_2x}" id="{filename_2x.stem}-2x.png" media-type="image/png"/>"""))

		# Recurse over xhtml files to make some compatibility replacements
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename_string in filenames:
				filename = Path(root) / filename_string

				if filename.suffix == ".svg":
					# For night mode compatibility, give the logo/titlepage a 1px white stroke attribute
					dom = self.get_dom(filename)

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
						with open(filename, "w+", encoding="utf-8") as file:
							file.write(dom.to_string())
							file.truncate()

					# Convert SVGs to PNGs at 2x resolution
					# Path arguments must be cast to string
					svg2png(url=str(filename), write_to=str(filename.parent / (str(filename.stem) + ".png")))

					if not ibooks_srcset_bug_exists:
						svg2png(url=str(filename), write_to=str(filename.parent / (str(filename.stem) + "-2x.png")), scale=2)

					# Remove the SVG
					(filename).unlink()

				if filename.suffix == ".xhtml":
					dom = self.get_dom(filename)

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
					# want to remove the se:color-depth.black-on-transparent semantic
					for node in dom.xpath("/html/body//img[ (contains(@epub:type, 'z3998:publisher-logo') or ancestor-or-self::*[re:test(@epub:type, '\\btitlepage\\b')]) and contains(@epub:type, 'se:color-depth.black-on-transparent')]"):
						node.remove_attr_value("epub:type", "se:color-depth.black-on-transparent")

					# Add ARIA roles, which are just mostly duplicate attributes to epub:type
					for role in ARIA_ROLES:
						if role == "toc":
							for node in dom.xpath(f"/html/body//nav[re:test(@epub:type, '\\b{role}\\b')]"):
								node.add_attr_value("role", f"doc-{role}")
						elif role == "noteref":
							for node in dom.xpath(f"/html/body//a[re:test(@epub:type, '\\b{role}\\b')]"):
								node.add_attr_value("role", f"doc-{role}")
						else:
							for node in dom.xpath(f"/html/body//section[re:test(@epub:type, '\\b{role}\\b')]"):
								node.add_attr_value("role", f"doc-{role}")

					# We converted svgs to pngs, so replace references
					for node in dom.xpath("/html/body//img[re:test(@src, '\\.svg$')]"):
						src = node.get_attr("src")
						if "cover.svg" in src:
							node.set_attr("src", src.replace("cover.svg", "cover.jpg"))
						else:
							node.set_attr("src", src.replace(".svg", ".png"))

							if not ibooks_srcset_bug_exists:
								filename = regex.search(r"(?<=/)[^/]+(?=\.svg)", src)[0]
								node.set_attr("srcset", f"{filename}-2x.png 2x, {filename}.png 1x")

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

					with open(filename, "w+", encoding="utf-8") as file:
						file.write(processed_xhtml)
						file.truncate()

					# Since we changed the dom string using regex, we have to flush its cache entry so we can re-build it later
					self.flush_dom_cache_entry(filename)

				if filename.suffix == ".css":
					with open(filename, "r+", encoding="utf-8") as file:
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

		# Output the modified the metadata file so that we can build the kobo book before making more compatibility hacks that aren’t needed on that platform.
		with open(work_epub_root_directory / "epub" / self.metadata_file_path.name, "w", encoding="utf-8") as file:
			file.write(metadata_dom.to_string())
			file.truncate()

		if build_kobo:
			with tempfile.TemporaryDirectory() as temp_directory:
				kobo_work_directory = Path(temp_directory)
				copy_tree(str(work_epub_root_directory), str(kobo_work_directory))

				for root, _, filenames in os.walk(kobo_work_directory):
					# Add a note to the metadata file indicating this is a transform build
					for filename_string in fnmatch.filter(filenames, self.metadata_file_path.name):
						filename = Path(root) / filename_string
						dom = self.get_dom(filename)

						for node in dom.xpath("/package[contains(@prefix, 'se:')]/metadata"):
							node.append(etree.fromstring("""<meta property="se:transform">kobo</meta>"""))

						with open(filename, "r+", encoding="utf-8") as file:
							file.write(dom.to_string())
							file.truncate()

					# Kobo .kepub files need each clause wrapped in a special <span> tag to enable highlighting.
					# Do this here. Hopefully Kobo will get their act together soon and drop this requirement.
					for filename_string in fnmatch.filter(filenames, "*.xhtml"):
						kobo.paragraph_counter = 1
						kobo.segment_counter = 1

						filename = (Path(root) / filename_string).resolve()

						# Note: Kobo supports CSS hyphenation, but it can be improved with soft hyphens.
						# However we can't insert them, because soft hyphens break the dictionary search when
						# a word is highlighted.
						dom = self.get_dom(filename)

						# Don't add spans to the ToC
						if dom.xpath("/html/body//nav[contains(@epub:type, 'toc')]"):
							continue

						# # Remove quote-align spans we inserted above, since Kobo has weird spacing problems with them
						# for node in dom.xpath("/html/body//span[contains(@class, 'quote-align')]"):
						# 	node.unwrap()

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

						with open(filename, "r+", encoding="utf-8") as file:
							file.write(xhtml)
							file.truncate()

				# All done, clean the output
				# Note that we don't clean .xhtml files, because the way kobo spans are added means that it will screw up spaces inbetween endnotes.
				for filepath in se.get_target_filenames([kobo_work_directory], ".opf"):
					se.formatting.format_xml_file(filepath)

				se.epub.write_epub(kobo_work_directory, output_directory / kobo_output_filename)

		# Now work on more compatibility fixes

		# Recurse over css files to make some compatibility replacements.
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename_string in filenames:
				filename = Path(root) / filename_string

				if filename.suffix == ".css":
					with open(filename, "r+", encoding="utf-8") as file:
						css = file.read()
						processed_css = css

						processed_css = regex.sub(r"^\s*hyphens\s*:\s*(.+)", "\thyphens: \\1\n\tadobe-hyphenate: \\1\n\t-webkit-hyphens: \\1\n\t-moz-hyphens: \\1", processed_css, flags=regex.MULTILINE)
						processed_css = regex.sub(r"^\s*hyphens\s*:\s*none;", "\thyphens: none;\n\tadobe-text-layout: optimizeSpeed; /* For Nook */", processed_css, flags=regex.MULTILINE)

						# We add a 20vh margin to sections without heading elements to drop them down on the page a little.
						# As of 01-2021 the vh unit is not supported on Nook or Kindle (but is on kepub and ibooks).
						processed_css = regex.sub(r"^(\s*)margin-top\s*:\s*20vh;", r"\1margin-top: 5em;", processed_css, flags=regex.MULTILINE)

						if processed_css != css:
							file.seek(0)
							file.write(processed_css)
							file.truncate()

		# Sort out MathML compatibility
		has_mathml = len(metadata_dom.xpath("/package/manifest/*[contains(@properties, 'mathml')]")) > 0
		if has_mathml:
			# We import this late because we don't want to load selenium if we're not going to use it!
			from se import browser # pylint: disable=import-outside-toplevel

			# We wrap this whole thing in a try block, because we need to call
			# driver.quit() if execution is interrupted (like by ctrl + c, or by an unhandled exception). If we don't call driver.quit(),
			# Firefox will stay around as a zombie process even if the Python script is dead.
			try:
				driver = browser.initialize_selenium_firefox_webdriver()

				mathml_count = 1
				for root, _, filenames in os.walk(work_epub_root_directory):
					for filename_string in filenames:
						filename = Path(root) / filename_string

						if filename.suffix == ".xhtml":
							dom = self.get_dom(filename)

							# Iterate over mathml nodes and try to make some basic replacements to achieve the same appearance
							# but without mathml. If we're able to remove all mathml namespaced elements, we don't need to render it as png.
							mathml_nodes = dom.xpath("/html/body//m:math")
							for node in mathml_nodes:
								node_clone = deepcopy(node)

								for child in node_clone.xpath(".//m:msup/*[2]"):
									replacement_node = se.easy_xml.EasyXmlElement("<sup/>", {"m": "http://www.w3.org/1998/Math/MathML"})

									child.parent.unwrap()

									mrows = child.xpath("//m:mrow")
									for mrow in mrows:
										mrow.wrap_with(replacement_node)
										mrow.unwrap()

									if not mrows:
										child.wrap_with(replacement_node)

								for child in node_clone.xpath(".//m:msub/*[2]"):
									replacement_node = se.easy_xml.EasyXmlElement("<sub/>", {"m": "http://www.w3.org/1998/Math/MathML"})

									child.parent.unwrap()

									mrows = child.xpath("//m:mrow")
									for mrow in mrows:
										mrow.wrap_with(replacement_node)
										mrow.unwrap()

									if not mrows:
										child.wrap_with(replacement_node)

								for child in node_clone.xpath(".//m:mi[not(./*)]"):
									replacement_node = se.easy_xml.EasyXmlElement("<var/>")
									replacement_node.text = child.text
									child.replace_with(replacement_node)

								for child in node_clone.xpath(".//m:mo[re:test(., '^[⋅+\\-−=×′]$')]"):
									child.unwrap()

								for child in node_clone.xpath(".//m:mo[re:test(., '^[\\(\\)\\[\\]]$')]"):
									child.unwrap()

								for child in node_clone.xpath(f".//m:mo[re:test(., '^[{se.INVISIBLE_TIMES}{se.FUNCTION_APPLICATION}]$')]"):
									child.remove()

								for child in node_clone.xpath(".//m:mn"):
									child.unwrap()

								# If there are no more mathml-namespaced elements, we succeeded; replace the mathml node
								# with our modified clone
								if not node_clone.xpath(".//*[namespace-uri()='http://www.w3.org/1998/Math/MathML']"):
									# Success!
									node_clone.lxml_element.tail = ""
									# Strip white space we may have added in previous operations,
									# and re-add white space around some operators
									for child in node_clone.lxml_element.iter("*"):
										if child.text is not None:
											child.text = child.text.strip()
											child.text = regex.sub(r"([⋅+\-−=×′])", r" \1 ", child.text)
										if child.tail is not None:
											child.tail = child.tail.strip()
											child.tail = regex.sub(r"\s*([⋅+\-−=×′])\s*", r" \1 ", child.tail)
									node.replace_with(node_clone)
									node_clone.unwrap()
								else:
									# Failure! Abandon all hope, and use Firefox to convert the MathML to PNG.
									# First, remove the m: namespace shorthand and add the actual namespace to our fragment
									namespaced_line = regex.sub(r"<(/?)m:", "<\\1", node.to_string())
									namespaced_line = namespaced_line.replace("<math", "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"")

									# Have Firefox render the fragment
									se.images.render_mathml_to_png(driver, namespaced_line, work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}.png", work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}-2x.png")

									img_node = se.easy_xml.EasyXmlElement("<img/>", {"epub": "http://www.idpf.org/2007/ops"})
									img_node.set_attr("class", "mathml epub-type-se-image-color-depth-black-on-transparent")
									img_node.set_attr("epub:type", "se:image.color-depth.black-on-transparent")
									img_node.set_attr("src", f"../images/mathml-{mathml_count}-2x.png")

									if ibooks_srcset_bug_exists:
										# Calculate the "normal" height/width from the 2x image
										ifile = work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}-2x.png"
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
										os.unlink(work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}.png")
									else:
										img_node.set_attr("srcset", f"../images/mathml-{mathml_count}-2x.png 2x, ../images/mathml-{mathml_count}.png 1x")

									node.replace_with(img_node)

									mathml_count = mathml_count + 1

							if mathml_nodes:
								with open(filename, "w", encoding="utf-8") as file:
									file.write(dom.to_string())
									file.truncate()

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

		if has_mathml:
			# Add any new MathML images we generated to the manifest
			for root, _, filenames in os.walk(work_epub_root_directory / "epub" / "images"):
				filenames = natsorted(filenames)
				filenames.reverse()
				for filename_string in filenames:
					filename = Path(root) / filename_string
					if filename.name.startswith("mathml-"):
						for node in metadata_dom.xpath("/package/manifest"):
							node.append(etree.fromstring(f"""<item href="images/{filename.name}" id="{filename.name}" media-type="image/png"/>"""))

			# Remove mathml property from manifest items, since we converted all MathML to PNG
			for node in metadata_dom.xpath("/package/manifest/item[contains(@properties, 'mathml')]"):
				node.remove_attr_value("properties", "mathml")

		# Generate our NCX file for compatibility with older ereaders.
		# First find the ToC file.
		toc_filename = metadata_dom.xpath("//item[@properties=\"nav\"][1]/@href", True)
		for node in metadata_dom.xpath("/package/spine"):
			node.set_attr("toc", "ncx")

		for node in metadata_dom.xpath("/package/manifest"):
			node.append(etree.fromstring("""<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml"/>"""))

		# Now use an XSLT transform to generate the NCX
		with importlib_resources.path("se.data", "navdoc2ncx.xsl") as navdoc2ncx_xsl_filename:
			toc_tree = se.epub.convert_toc_to_ncx(work_epub_root_directory, toc_filename, navdoc2ncx_xsl_filename)

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

				# We add the 'text' attribute to the titlepage to tell the reader to start there
				if ref_node.get_attr("type") == "titlepage":
					ref_node.set_attr("type", "title-page text")

				guide_root_node.append(ref_node)

		# Append the guide to the <package> element
		if guide_root_node.children:
			for node in metadata_dom.xpath("/package"):
				node.append(guide_root_node)

		# Guide is done, now write the metadata file and clean it.
		# Output the modified metadata file before making more compatibility hacks.
		with open(work_epub_root_directory / "epub" / self.metadata_file_path.name, "w", encoding="utf-8") as file:
			file.write(se.formatting.format_opf(metadata_dom.to_string()))
			file.truncate()

		# All done, clean the output
		for filepath in se.get_target_filenames([work_epub_root_directory], (".xhtml", ".ncx")):
			try:
				se.formatting.format_xml_file(filepath)
			except se.SeException as ex:
				raise se.InvalidXhtmlException(f"{ex}. File: [path][link={filepath}]{filepath}[/][/]") from ex

		# Write the compatible epub
		se.epub.write_epub(work_epub_root_directory, output_directory / compatible_epub_output_filename)

		if run_epubcheck:
			# Path arguments must be cast to string for Windows compatibility.
			with importlib_resources.path("se.data.epubcheck", "epubcheck.jar") as jar_path:
				try:
					epubcheck_result = subprocess.run(["java", "-jar", str(jar_path), "--quiet", str(output_directory / compatible_epub_output_filename)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
					epubcheck_result.check_returncode()
				except subprocess.CalledProcessError as ex:
					output = epubcheck_result.stdout.decode().strip()
					# Get the epubcheck version to print to the console
					version_output = subprocess.run(["java", "-jar", str(jar_path), "--version"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.decode().strip()
					version = regex.search(r"[0-9]+\.([0-9]+\.?)*", version_output, flags=regex.MULTILINE).group(0)

					# The last two lines from epubcheck output are not necessary. Remove them here.
					# Remove them as lines instead of as a matching regex to work with localized output strings.
					split_output = output.split("\n")
					output = "\n".join(split_output[:-2])

					# Try to linkify files in output if we can find them
					try:
						output = regex.sub(r"(ERROR\(.+?\): )(.+?)(\([0-9]+,[0-9]+\))", lambda match: match.group(1) + "[path][link=file://" + str(self.path / "src" / regex.sub(fr"^\..+?\.epub{os.sep}", "", match.group(2))) + "]" + match.group(2) + "[/][/]" + match.group(3), output)
					except:
						# If something goes wrong, just pass through the usual output
						pass

					raise se.BuildFailedException(f"[bash]epubcheck[/] v{version} failed with:\n{output}") from ex

		if build_kindle:
			# Kindle doesn't go more than 2 levels deep for ToC, so flatten it here.
			with open(work_epub_root_directory / "epub" / toc_filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				dom = se.easy_xml.EasyXmlTree(xhtml)

				for node in dom.xpath("//ol/li/ol/li/ol"):
					node.lxml_element.getparent().addnext(node.lxml_element)
					node.unwrap()

				file.seek(0)
				file.write(dom.to_string())
				file.truncate()

			# Rebuild the NCX
			with importlib_resources.path("se.data", "navdoc2ncx.xsl") as navdoc2ncx_xsl_filename:
				se.epub.convert_toc_to_ncx(work_epub_root_directory, toc_filename, navdoc2ncx_xsl_filename)

			# Clean just the ToC and NCX
			for filepath in [work_epub_root_directory / "epub" / "toc.ncx", work_epub_root_directory / "epub" / toc_filename]:
				se.formatting.format_xml_file(filepath)

			# Do some compatibility replacements
			for root, _, filenames in os.walk(work_epub_root_directory):
				for filename_string in filenames:
					filename = Path(root) / filename_string
					if filename.suffix == ".xhtml":
						dom = self.get_dom(filename)
						replace_shy_hyphens = False

						# Remove se:color-depth.black-on-transparent, as Calibre removes media queries so this will *always* be invisible
						for node in dom.xpath("/html/body//img[contains(@class, 'epub-type-se-image-color-depth-black-on-transparent') or contains(@epub:type, 'se:image.color-depth.black-on-transparent')]"):
							if node.get_attr("class"):
								node.set_attr("class", node.get_attr("class").replace("epub-type-se-image-color-depth-black-on-transparent", ""))

							if node.get_attr("epub:type"):
								node.set_attr("epub:type", node.get_attr("epub:type").replace("se:image.color-depth.black-on-transparent", ""))

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
							note_number = 1
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

						with open(filename, "r+", encoding="utf-8") as file:
							file.write(se.formatting.format_xhtml(xhtml))
							file.truncate()

			# Include compatibility CSS
			with open(work_epub_root_directory / "epub" / "css" / "core.css", "a", encoding="utf-8") as core_css_file:
				with importlib_resources.open_text("se.data.templates", "kindle.css", encoding="utf-8") as compatibility_css_file:
					core_css_file.write(compatibility_css_file.read())

			# Build an epub file we can send to Calibre
			se.epub.write_epub(work_epub_root_directory, work_directory / compatible_epub_output_filename)

			# Generate the Kindle file
			# We place it in the work directory because later we have to update the asin, and the mobi.update_asin() function will write to the final output directory
			cover_path = None
			for href in metadata_dom.xpath("//item[@properties=\"cover-image\"]/@href"):
				cover_path = work_epub_root_directory / "epub" / href

			# Path arguments must be cast to string for Windows compatibility.
			try:
				calibre_args = [str(ebook_convert_path), str(work_directory / compatible_epub_output_filename), str(work_directory / kindle_output_filename), "--pretty-print", "--no-inline-toc", "--max-toc-links=0", "--prefer-metadata-cover"]

				if cover_path:
					calibre_args.append(f"--cover={cover_path}")

				calibre_result = subprocess.run(calibre_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
				calibre_result.check_returncode()
			except subprocess.CalledProcessError as ex:
				output = calibre_result.stdout.decode().strip()

				raise se.BuildFailedException(f"[bash]ebook-convert[/] failed with:\n{output}") from ex

			# Success, extract the Kindle cover thumbnail

			# Update the ASIN in the generated file
			mobi.update_asin(asin, work_directory / kindle_output_filename, output_directory / kindle_output_filename)

			# Extract the thumbnail
			if os.path.isfile(work_epub_root_directory / "epub" / "images" / "cover.jpg"):
				kindle_cover_thumbnail = Image.open(work_epub_root_directory / "epub" / "images" / "cover.jpg")
				kindle_cover_thumbnail = kindle_cover_thumbnail.convert("RGB") # Remove alpha channel from PNG if necessary
				kindle_cover_thumbnail = kindle_cover_thumbnail.resize((432, 648))
				kindle_cover_thumbnail.save(output_directory / f"thumbnail_{asin}_EBOK_portrait.jpg")

	# Build is all done!
	# Since we made heavy changes to the ebook's dom, flush the dom cache in case we use this class again
	self._dom_cache = [] # pylint: disable=protected-access
	self._file_cache = [] # pylint: disable=protected-access
