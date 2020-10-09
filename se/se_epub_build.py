#!/usr/bin/env python3
"""
This module contains the build function.

Strictly speaking, the build() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put it in a separate file.
"""

import fnmatch
import filecmp
import os
import shutil
import subprocess
import tempfile
from distutils.dir_util import copy_tree
from hashlib import sha1
from pathlib import Path
from typing import List
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
	metadata_xml = self.metadata_xml

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
			identifier = self.metadata_dom.xpath("//dc:identifier")[0].inner_xml().replace("url:", "")
			asin = sha1(identifier.encode("utf-8")).hexdigest()
		except Exception as ex:
			raise se.InvalidSeEbookException(f"Missing [xml]<dc:identifier>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/].") from ex

		if not self.metadata_dom.xpath("//dc:title"):
			raise se.InvalidSeEbookException(f"Missing [xml]<dc:title>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/].")

		output_filename = identifier.replace("https://standardebooks.org/ebooks/", "").replace("/", "_")
		url_author = ""
		for author in self.metadata_dom.xpath("//dc:creator"):
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

			# Set modified date in content.opf
			self.metadata_xml = regex.sub(r"<meta property=\"dcterms:modified\">[^<]+?</meta>", f"<meta property=\"dcterms:modified\">{last_updated_iso}</meta>", self.metadata_xml)

			with open(work_epub_root_directory / "epub" / "content.opf", "w", encoding="utf-8") as file:
				file.seek(0)
				file.write(self.metadata_xml)
				file.truncate()

			# Update the colophon with release info
			with open(work_epub_root_directory / "epub" / "text" / "colophon.xhtml", "r+", encoding="utf-8") as file:
				xhtml = file.read()

				xhtml = xhtml.replace("<p>The first edition of this ebook was released on<br/>", f"<p>This edition was released on<br/>\n\t\t\t<b>{last_updated_friendly}</b><br/>\n\t\t\tand is based on<br/>\n\t\t\t<b>revision {self.last_commit.short_sha}</b>.<br/>\n\t\t\tThe first edition of this ebook was released on<br/>")

				file.seek(0)
				file.write(xhtml)
				file.truncate()

		# Output the pure epub3 file
		se.epub.write_epub(work_epub_root_directory, output_directory / epub_output_filename)

		# Now add epub2 compatibility.

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

				# Don't mess with the ToC, since if we have ol/li > first-child selectors we could screw it up
				if filename.name == "toc.xhtml":
					continue

				with open(filename, "r+", encoding="utf-8") as file:
					# We have to remove the default namespace declaration from our document, otherwise
					# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
					xhtml = file.read().replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")
					processed_xhtml = xhtml
					try:
						tree = etree.fromstring(str.encode(xhtml))
					except Exception as ex:
						raise se.InvalidXhtmlException(f"Error parsing XHTML file: [path][link=file://{filename}]{filename}[/][/]. Exception: {ex}")

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
									sel = se.easy_xml.css_selector(target_element_selector)
									for element in tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
										current_class = element.get("class")
										if current_class is not None and replacement_class not in current_class:
											current_class = current_class + " " + replacement_class
										else:
											current_class = replacement_class

										element.set("class", current_class)

						except lxml.cssselect.ExpressionError:
							# This gets thrown if we use pseudo-elements, which lxml doesn't support
							pass
						except lxml.cssselect.SelectorSyntaxError as ex:
							raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: [css]{selector}[/]. Exception: {ex}")

						# We've already replaced attribute/namespace selectors with classes in the CSS, now add those classes to the matching elements
						if "[epub|type" in selector:
							for namespace_selector in regex.findall(r"\[epub\|type\~\=\"[^\"]*?\"\]", selector):
								sel = se.easy_xml.css_selector(namespace_selector)

								for element in tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
									new_class = regex.sub(r"^\.", "", se.formatting.namespace_to_class(namespace_selector))
									current_class = element.get("class", "")

									if new_class not in current_class:
										current_class = f"{current_class} {new_class}".strip()
										element.set("class", current_class)

					processed_xhtml = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + etree.tostring(tree, encoding=str, pretty_print=True)

					# We do this round in a second pass because if we modify the tree like this, it screws up how lxml does processing later.
					# If it's all done in one pass, we wind up in a race condition where some elements are fixed and some not
					tree = etree.fromstring(str.encode(processed_xhtml))

					for selector in selectors:
						try:
							sel = se.easy_xml.css_selector(selector)
						except lxml.cssselect.ExpressionError:
							# This gets thrown if we use pseudo-elements, which lxml doesn't support
							continue
						except lxml.cssselect.SelectorSyntaxError as ex:
							raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: [css]{selector}[/]. Exception: {ex}")

						# Convert <abbr> to <span>
						if "abbr" in selector:
							for element in tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
								# Why would you want the tail to output by default?!?
								raw_string = etree.tostring(element, encoding=str, with_tail=False)

								# lxml--crap as usual--includes a bunch of namespace information in every element we print.
								# Remove it here.
								raw_string = raw_string.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")
								raw_string = raw_string.replace(" xmlns:epub=\"http://www.idpf.org/2007/ops\"", "")
								raw_string = raw_string.replace(" xmlns:m=\"http://www.w3.org/1998/Math/MathML\"", "")

								# Now lxml doesn't let us modify the tree, so we just do a straight up regex replace to turn this into a span
								processed_string = raw_string.replace("<abbr", "<span")
								processed_string = processed_string.replace("</abbr", "</span")

								# Now we have a nice, fixed string.  But, since lxml can't replace elements, we write it ourselves.
								processed_xhtml = processed_xhtml.replace(raw_string, processed_string)

								tree = etree.fromstring(str.encode(processed_xhtml))

					# Now we just remove all stray abbr tags that were not styled by CSS
					processed_xhtml = regex.sub(r"</?abbr[^>]*?>", "", processed_xhtml)

					# Remove datetime="" attribute in <time> tags, which is not always understood by epubcheck
					processed_xhtml = regex.sub(r" datetime=\"[^\"]+?\"", "", processed_xhtml)

					tree = etree.fromstring(str.encode(processed_xhtml))

					if processed_xhtml != xhtml:
						file.seek(0)
						file.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + etree.tostring(tree, encoding=str, pretty_print=True).replace("<html", "<html xmlns=\"http://www.w3.org/1999/xhtml\""))
						file.truncate()

		# Done simplifying CSS and tags!

		# Extract cover and cover thumbnail
		cover_svg_file = work_epub_root_directory / "epub" / "images" / "cover.svg"
		if not os.path.isfile(cover_svg_file):
			raise se.MissingDependencyException("Cover image is missing. Did you run [bash]se build-images[/]?")

		svg2png(url=str(cover_svg_file), write_to=str(work_directory / "cover.png"))
		cover = Image.open(work_directory / "cover.png")
		cover = cover.convert("RGB") # Remove alpha channel from PNG if necessary
		cover.save(work_epub_root_directory / "epub" / "images" / "cover.jpg")
		(work_directory / "cover.png").unlink()

		if build_covers:
			shutil.copy2(work_epub_root_directory / "epub" / "images" / "cover.jpg", output_directory / "cover.jpg")
			shutil.copy2(cover_svg_file, output_directory / "cover-thumbnail.svg")
			# Path arguments must be cast to string
			svg2png(url=str(output_directory / "cover-thumbnail.svg"), write_to=str(work_directory / "cover-thumbnail.png"))
			cover = Image.open(work_directory / "cover-thumbnail.png")
			cover = cover.resize((COVER_THUMBNAIL_WIDTH, COVER_THUMBNAIL_HEIGHT))
			cover = cover.convert("RGB") # Remove alpha channel from PNG if necessary
			cover.save(output_directory / "cover-thumbnail.jpg")
			(work_directory / "cover-thumbnail.png").unlink()
			(output_directory / "cover-thumbnail.svg").unlink()

		cover_svg_file.unlink()

		# Massage image references in content.opf
		metadata_xml = metadata_xml.replace("cover.svg", "cover.jpg")
		metadata_xml = metadata_xml.replace("id=\"cover.jpg\" media-type=\"image/svg+xml\"", "id=\"cover.jpg\" media-type=\"image/jpeg\"")
		metadata_xml = regex.sub(r" properties=\"([^\"]*?)svg([^\"]*?)\"", r''' properties="\1\2"''', metadata_xml) # We may also have the `mathml` property
		metadata_xml = regex.sub(r" properties=\"([^\s]*?)\s\"", r''' properties="\1"''', metadata_xml) # Clean up trailing white space in property attributes introduced by the above line
		metadata_xml = regex.sub(r" properties=\"\s*\"", "", metadata_xml) # Remove any now-empty property attributes

		# Add an element noting the version of the se tools that built this ebook
		metadata_xml = regex.sub(r"<dc:publisher", f"<meta property=\"se:built-with\">{se.VERSION}</meta>\n\t\t<dc:publisher", metadata_xml)

		# Google Play Books chokes on https XML namespace identifiers (as of at least 2017-07)
		metadata_xml = metadata_xml.replace("https://standardebooks.org/vocab/1.0", "http://standardebooks.org/vocab/1.0")

		# Output the modified content.opf so that we can build the kobo book before making more epub2 compatibility hacks
		with open(work_epub_root_directory / "epub" / "content.opf", "w", encoding="utf-8") as file:
			file.write(metadata_xml)
			file.truncate()

		# Recurse over xhtml files to make some compatibility replacements
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename_string in filenames:
				filename = Path(root) / filename_string

				if filename.suffix == ".svg":
					add_stroke = False

					if filename.name == "logo.svg":
						# If we're adding stroke to the logo, make sure it's our premade logo and not a 3rd party logo file.
						# 3rd party logos will get mangled by our naive regexes.
						with importlib_resources.path("se.data.templates", "logo.svg") as logo_file_path:
							if filecmp.cmp(logo_file_path, filename):
								add_stroke = True

					if filename.name == "titlepage.svg":
						add_stroke = True

					# For night mode compatibility, give the titlepage a 1px white stroke attribute
					if add_stroke:
						with open(filename, "r+", encoding="utf-8") as file:
							svg = file.read()
							paths = svg

							# What we're doing here is faking the `stroke-align: outside` property, which is an unsupported draft spec right now.
							# We do this by duplicating all the SVG paths, and giving the duplicates a 2px stroke.  The originals are directly on top,
							# so the 2px stroke becomes a 1px stroke that's *outside* of the path instead of being *centered* on the path border.
							# This looks much nicer, but we also have to increase the image size by 2px in both directions, and re-center the whole thing.

							if filename.name == "titlepage.svg":
								stroke_width = SVG_TITLEPAGE_OUTER_STROKE_WIDTH
							else:
								stroke_width = SVG_OUTER_STROKE_WIDTH

							# First, strip out non-path, non-group elements
							paths = regex.sub(r"<\?xml[^<]+?\?>", "", paths)
							paths = regex.sub(r"</?svg[^<]*?>", "", paths)
							paths = regex.sub(r"<title>[^<]+?</title>", "", paths)
							paths = regex.sub(r"<desc>[^<]+?</desc>", "", paths)

							# `paths` is now our "duplicate".  Add a 2px stroke.
							paths = paths.replace("<path", f"<path style=\"stroke: #ffffff; stroke-width: {stroke_width}px;\"")

							# Inject the duplicate under the old SVG paths.  We do this by only replacing the first regex match for <g> or <path>
							svg = regex.sub(r"(<g|<path)", f"{paths}\\1", svg, 1)

							# If this SVG specifies height/width, then increase height and width by 2 pixels and translate everything by 1px
							try:
								height = int(regex.search(r"<svg[^>]+?height=\"([0-9]+)\"", svg).group(1)) + stroke_width
								svg = regex.sub(r"<svg([^<]*?)height=\"[0-9]+\"", f"<svg\\1height=\"{height}\"", svg)

								width = int(regex.search(r"<svg[^>]+?width=\"([0-9]+)\"", svg).group(1)) + stroke_width
								svg = regex.sub(r"<svg([^<]*?)width=\"[0-9]+\"", f"<svg\\1width=\"{width}\"", svg)

								# Add a grouping element to translate everything over 1px
								svg = regex.sub(r"(<g|<path)", "<g transform=\"translate({amount}, {amount})\">\n\\1".format(amount=(stroke_width / 2)), svg, 1)
								svg = svg.replace("</svg>", "</g>\n</svg>")
							except AttributeError:
								# Thrown when the regex doesn't match (i.e. SVG doesn't specify height/width)
								pass

							file.seek(0)
							file.write(svg)
							file.truncate()

					# Convert SVGs to PNGs at 2x resolution
					# Path arguments must be cast to string
					svg2png(url=str(filename), write_to=str(filename.parent / (str(filename.stem) + ".png")))

					# iBooks srcset bug: once srcset works in iBooks, we can uncomment this line
					# svg2png(url=str(filename), write_to=str(filename.parent / (str(filename.stem) + "-2x.png")), scale=2)

					# Add the new PNGs to the manifest
					# iBooks srcset bug: once srcset works in iBooks, we can use this line instead of the one below it
					# metadata_xml = metadata_xml.replace("<manifest>", f"""<manifest><item href="images/{filename.stem}.png" id="{filename.stem}.png" media-type="image/png"/><item href="images/{filename.stem}-2x.png" id="{filename.stem}-2x.png" media-type="image/png"/>""")
					metadata_xml = metadata_xml.replace("<manifest>", f"""<manifest><item href="images/{filename.stem}.png" id="{filename.stem}.png" media-type="image/png"/>""")

					# Remove the SVG from the manifest
					metadata_xml = regex.sub(fr"""<item href="images/{filename.name}" id="[^"]+?" media-type="image/svg\+xml"/>""", "", metadata_xml)

					# Remove the SVG
					(filename).unlink()

				if filename.suffix == ".xhtml":
					with open(filename, "r+", encoding="utf-8") as file:
						xhtml = file.read()
						processed_xhtml = xhtml

						# Check if there's any MathML to convert.
						# We expect MathML to be the "content" type (versus the "presentational" type).
						# We use an XSL transform to convert from "content" to "presentational" MathML.
						# If we start with presentational, then nothing will be changed.
						# Kobo supports presentational MathML. After we build kobo, we convert the presentational MathML to PNG for the rest of the builds.
						mathml_transform = None
						for line in regex.findall(r"<(?:m:)?math[^>]*?>(.+?)</(?:m:)?math>", processed_xhtml, flags=regex.DOTALL):
							mathml_content_tree = se.easy_xml.EasyXhtmlTree("<?xml version=\"1.0\" encoding=\"utf-8\"?><math xmlns=\"http://www.w3.org/1998/Math/MathML\">{}</math>".format(regex.sub(r"<(/?)m:", "<\\1", line)))

							# Initialize the transform object, if we haven't yet
							if not mathml_transform:
								with importlib_resources.path("se.data", "mathmlcontent2presentation.xsl") as mathml_xsl_filename:
									mathml_transform = etree.XSLT(etree.parse(str(mathml_xsl_filename)))

							# Transform the mathml and get a string representation
							# XSLT comes from https://github.com/fred-wang/webextension-content-mathml-polyfill
							mathml_presentation_tree = mathml_transform(mathml_content_tree.etree)
							mathml_presentation_xhtml = etree.tostring(mathml_presentation_tree, encoding="unicode", pretty_print=True, with_tail=False).strip()

							# Plop our string back in to the XHTML we're processing
							processed_xhtml = regex.sub(r"<(?:m:)?math[^>]*?>\{}\</(?:m:)?math>".format(regex.escape(line)), mathml_presentation_xhtml, processed_xhtml, flags=regex.MULTILINE)

						if filename.name == "endnotes.xhtml":
							# iOS renders the left-arrow-hook character as an emoji; this fixes it and forces it to render as text.
							# See https://github.com/standardebooks/tools/issues/73
							# See http://mts.io/2015/04/21/unicode-symbol-render-text-emoji/
							processed_xhtml = processed_xhtml.replace("\u21a9", "\u21a9\ufe0e")

						# Since we added an outlining stroke to the titlepage/publisher logo images, we
						# want to remove the se:color-depth.black-on-transparent semantic
						if filename.name in ("colophon.xhtml", "imprint.xhtml", "titlepage.xhtml"):
							processed_xhtml = regex.sub(r"\s*se:color-depth\.black-on-transparent\s*", "", processed_xhtml)

						# Add ARIA roles, which are just mostly duplicate attributes to epub:type
						for role in ARIA_ROLES:
							processed_xhtml = regex.sub(fr"(epub:type=\"[^\"]*?{role}[^\"]*?\")", f"\\1 role=\"doc-{role}\"", processed_xhtml)

						# Some ARIA roles can't apply to some elements.
						# For example, epilogue can't apply to <article>
						processed_xhtml = regex.sub(r"<article ([^>]*?)role=\"doc-epilogue\"", "<article \\1", processed_xhtml)

						if filename.name == "toc.xhtml":
							landmarks_xhtml = regex.findall(r"<nav epub:type=\"landmarks\">.*?</nav>", processed_xhtml, flags=regex.DOTALL)
							landmarks_xhtml = regex.sub(r" role=\"doc-.*?\"", "", landmarks_xhtml[0])
							processed_xhtml = regex.sub(r"<nav epub:type=\"landmarks\">.*?</nav>", landmarks_xhtml, processed_xhtml, flags=regex.DOTALL)

						# But, remove ARIA roles we added to h# tags, because typically those roles are for sectioning content.
						# For example, we might have an h2 that is both a title and dedication. But ARIA can't handle it being a dedication.
						# See The Man Who Was Thursday by G K Chesterton
						processed_xhtml = regex.sub(r"(<h[1-6] [^>]*) role=\".*?\">", "\\1>", processed_xhtml)



						# Google Play Books chokes on https XML namespace identifiers (as of at least 2017-07)
						processed_xhtml = processed_xhtml.replace("https://standardebooks.org/vocab/1.0", "http://standardebooks.org/vocab/1.0")

						# We converted svgs to pngs, so replace references
						processed_xhtml = processed_xhtml.replace("cover.svg", "cover.jpg")

						# iBooks srcset bug: once srcset works in iBooks, we can use this line instead of the one below it
						# processed_xhtml = regex.sub(r"src=\"([^\"]+?)\.svg\"", "src=\"\\1.png\" srcset=\"\\1-2x.png 2x, \\1.png 1x\"", processed_xhtml)
						processed_xhtml = regex.sub(r"src=\"([^\"]+?)\.svg\"", "src=\"\\1.png\"", processed_xhtml)

						# To get popup footnotes in iBooks, we have to change epub:endnote to epub:footnote.
						# Remember to get our custom style selectors too.
						processed_xhtml = regex.sub(r"epub:type=\"([^\"]*?)endnote([^\"]*?)\"", "epub:type=\"\\1footnote\\2\"", processed_xhtml)
						processed_xhtml = regex.sub(r"class=\"([^\"]*?)epub-type-endnote([^\"]*?)\"", "class=\"\\1epub-type-footnote\\2\"", processed_xhtml)

						# Include extra lang tag for accessibility compatibility.
						processed_xhtml = regex.sub(r"xml:lang\=\"([^\"]+?)\"", "lang=\"\\1\" xml:lang=\"\\1\"", processed_xhtml)

						# Typography: replace double and triple em dash characters with extra em dashes.
						processed_xhtml = processed_xhtml.replace("⸺", f"—{se.WORD_JOINER}—")
						processed_xhtml = processed_xhtml.replace("⸻", f"—{se.WORD_JOINER}—{se.WORD_JOINER}—")

						# Typography: replace some other less common characters.
						processed_xhtml = processed_xhtml.replace("⅒", "1/10")
						processed_xhtml = processed_xhtml.replace("℅", "c/o")
						processed_xhtml = processed_xhtml.replace("✗", "×")
						processed_xhtml = processed_xhtml.replace(" ", f"{se.NO_BREAK_SPACE}{se.NO_BREAK_SPACE}") # em-space to two nbsps

						# Many e-readers don't support the word joiner character (U+2060).
						# They DO, however, support the now-deprecated zero-width non-breaking space (U+FEFF)
						# For epubs, do this replacement.  Kindle now seems to handle everything fortunately.
						processed_xhtml = processed_xhtml.replace(se.WORD_JOINER, se.ZERO_WIDTH_SPACE)

						# Some minor code style cleanup
						processed_xhtml = processed_xhtml.replace(" >", ">")
						processed_xhtml = regex.sub(r"""\s*epub:type=""\s*""", "", processed_xhtml)

						# Move quotation marks over periods and commas
						processed_xhtml = regex.sub(r"([\\.,])([’”])", r"""\1<span class="quote-align">\2</span>""", processed_xhtml)

						# The above replacement may replace text within <img alt> attributes. Remove those now until no replacements remain, since we may have
						# many matches in the same line
						replacements = 1
						while replacements > 0:
							processed_xhtml, replacements = regex.subn(r"alt=\"([^<>\"]+?)<span class=\"quote-align\">([^<>\"]+?)</span>", r"""alt="\1\2""", processed_xhtml)

						# Do the same for <title> elements
						replacements = 1
						while replacements > 0:
							processed_xhtml, replacements = regex.subn(r"<title>([^<>]+?)<span class=\"quote-align\">([^<>]+?)</span>", r"""<title>\1\2""", processed_xhtml)

						if processed_xhtml != xhtml:
							file.seek(0)
							file.write(processed_xhtml)
							file.truncate()

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

						if processed_css != css:
							file.seek(0)
							file.write(processed_css)
							file.truncate()

		if build_kobo:
			with tempfile.TemporaryDirectory() as temp_directory:
				kobo_work_directory = Path(temp_directory)
				copy_tree(str(work_epub_root_directory), str(kobo_work_directory))

				for root, _, filenames in os.walk(kobo_work_directory):
					# Add a note to content.opf indicating this is a transform build
					for filename_string in fnmatch.filter(filenames, "content.opf"):
						with open(Path(root) / filename_string, "r+", encoding="utf-8") as file:
							xhtml = file.read()

							xhtml = regex.sub(r"<dc:publisher", "<meta property=\"se:transform\">kobo</meta>\n\t\t<dc:publisher", xhtml)

							file.seek(0)
							file.write(xhtml)
							file.truncate()

					# Kobo .kepub files need each clause wrapped in a special <span> tag to enable highlighting.
					# Do this here. Hopefully Kobo will get their act together soon and drop this requirement.
					for filename_string in fnmatch.filter(filenames, "*.xhtml"):
						kobo.paragraph_counter = 1
						kobo.segment_counter = 1

						filename = (Path(root) / filename_string).resolve()

						# Don't add spans to the ToC
						if filename.name == "toc.xhtml":
							continue

						with open(filename, "r+", encoding="utf-8") as file:
							xhtml = file.read()

							# Note: Kobo supports CSS hyphenation, but it can be improved with soft hyphens.
							# However we can't insert them, because soft hyphens break the dictionary search when
							# a word is highlighted.

							# Kobos don't have fonts that support the ↩ character in endnotes, so replace it with ←
							if filename.name == "endnotes.xhtml":
								# Note that we replaced ↩ with \u21a9\ufe0e in an earlier iOS compatibility fix
								xhtml = regex.sub(r"epub:type=\"backlink\">\u21a9\ufe0e</a>", "epub:type=\"backlink\">←</a>", xhtml)

							# We have to remove the default namespace declaration from our document, otherwise
							# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
							try:
								tree = etree.fromstring(str.encode(xhtml.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")))
							except Exception as ex:
								raise se.InvalidXhtmlException(f"Error parsing XHTML file: [path][link=file://{filename}]{filename}[/][/]. Exception: {ex}")

							kobo.add_kobo_spans_to_node(tree.xpath("./body", namespaces=se.XHTML_NAMESPACES)[0])

							xhtml = etree.tostring(tree, encoding="unicode", pretty_print=True, with_tail=False)
							xhtml = regex.sub(r"<html:span", "<span", xhtml)
							xhtml = regex.sub(r"html:span>", "span>", xhtml)
							xhtml = regex.sub(r"<span xmlns:html=\"http://www.w3.org/1999/xhtml\"", "<span", xhtml)
							xhtml = regex.sub(r"<html", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<html xmlns=\"http://www.w3.org/1999/xhtml\"", xhtml)

							file.seek(0)
							file.write(xhtml)
							file.truncate()

				# All done, clean the output
				# Note that we don't clean .xhtml files, because the way kobo spans are added means that it will screw up spaces inbetween endnotes.
				for filepath in se.get_target_filenames([kobo_work_directory], (".svg", ".opf", ".ncx")):
					se.formatting.format_xml_file(filepath)

				se.epub.write_epub(kobo_work_directory, output_directory / kobo_output_filename)

		# Now work on more epub2 compatibility

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

						if processed_css != css:
							file.seek(0)
							file.write(processed_css)
							file.truncate()

		# Sort out MathML compatibility
		has_mathml = len(self.metadata_dom.xpath("/package/manifest/*[contains(@properties, 'mathml')]")) > 0
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
							with open(filename, "r+", encoding="utf-8") as file:
								xhtml = file.read()
								processed_xhtml = xhtml
								replaced_mathml: List[str] = []

								# Check if there's MathML we want to convert
								# We take a naive approach and use some regexes to try to simplify simple MathML expressions.
								# For each MathML expression, if our round of regexes finishes and there is still MathML in the processed result, we abandon the attempt and render to PNG using Firefox.
								for line in regex.findall(r"<(?:m:)?math[^>]*?>(?:.+?)</(?:m:)?math>", processed_xhtml, flags=regex.DOTALL):
									if line not in replaced_mathml:
										replaced_mathml.append(line) # Store converted lines to save time in case we have multiple instances of the same MathML
										mathml_tree = se.easy_xml.EasyXhtmlTree("<?xml version=\"1.0\" encoding=\"utf-8\"?>{}".format(regex.sub(r"<(/?)m:", "<\\1", line)))
										processed_line = line

										# If the mfenced element has more than one child, they are separated by commas when rendered.
										# This is too complex for our naive regexes to work around. So, if there is an mfenced element with more than one child, abandon the attempt.
										if not mathml_tree.css_select("mfenced > * + *"):
											processed_line = regex.sub(r"</?(?:m:)?math[^>]*?>", "", processed_line)
											processed_line = regex.sub(r"<!--.+?-->", "", processed_line)
											processed_line = regex.sub(r"<(?:m:)?mfenced/>", "()", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m(sub|sup))><((?:m:)?mi)>(.+?)</\3><((?:m:)?mi)>(.+?)</\5></\1>", "<i>\\4</i><\\2><i>\\6</i></\\2>", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m(sub|sup))><((?:m:)?mi)>(.+?)</\3><((?:m:)?mn)>(.+?)</\5></\1>", "<i>\\4</i><\\2>\\6</\\2>", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m(sub|sup))><((?:m:)?mn)>(.+?)</\3><((?:m:)?mn)>(.+?)</\5></\1>", "\\4<\\2>\\6</\\2>", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m(sub|sup))><((?:m:)?mn)>(.+?)</\3><((?:m:)?mi)>(.+?)</\5></\1>", "\\4<\\2><i>\\6</i></\\2>", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m(sub|sup))><((?:m:)?mi) mathvariant=\"normal\">(.+?)</\3><((?:m:)?mi)>(.+?)</\5></\1>", "\\4<\\2><i>\\6</i></\\2>", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m(sub|sup))><((?:m:)?mi) mathvariant=\"normal\">(.+?)</\3><((?:m:)?mn)>(.+?)</\5></\1>", "\\4<\\2>\\6</\\2>", processed_line)
											processed_line = regex.sub(fr"<(?:m:)?mo>{se.FUNCTION_APPLICATION}</(?:m:)?mo>", "", processed_line, flags=regex.IGNORECASE) # The ignore case flag is required to match here with the special FUNCTION_APPLICATION character, it's unclear why
											processed_line = regex.sub(r"<(?:m:)?mfenced><((?:m:)(?:mo|mi|mn|mrow))>(.+?)</\1></(?:m:)?mfenced>", "(<\\1>\\2</\\1>)", processed_line)
											processed_line = regex.sub(r"<(?:m:)?mrow>([^>].+?)</(?:m:)?mrow>", "\\1", processed_line)
											processed_line = regex.sub(r"<(?:m:)?mi>([^<]+?)</(?:m:)?mi>", "<i>\\1</i>", processed_line)
											processed_line = regex.sub(r"<(?:m:)?mi mathvariant=\"normal\">([^<]+?)</(?:m:)?mi>", "\\1", processed_line)
											processed_line = regex.sub(r"<(?:m:)?mo>([+\-−=×])</(?:m:)?mo>", " \\1 ", processed_line)
											processed_line = regex.sub(r"<((?:m:)?m[no])>(.+?)</\1>", "\\2", processed_line)
											processed_line = regex.sub(r"</?(?:m:)?mrow>", "", processed_line)
											processed_line = processed_line.strip()
											processed_line = regex.sub(r"</i><i>", "", processed_line, flags=regex.DOTALL)

										# Did we succeed? Is there any more MathML in our string?
										if regex.findall("</?(?:m:)?m", processed_line):
											# Failure! Abandon all hope, and use Firefox to convert the MathML to PNG.
											se.images.render_mathml_to_png(driver, regex.sub(r"<(/?)m:", "<\\1", line), work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}.png", work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}-2x.png")
											# iBooks srcset bug: once srcset works in iBooks, this block can go away
											# calculate the "normal" height/width from the 2x image
											ifile = work_epub_root_directory / "epub" / "images" / f"mathml-{mathml_count}-2x.png"
											image = Image.open(ifile)
											img_width = image.size[0]
											img_height = image.size[1]
											# if either dimension is odd, add a pixel
											right = img_width % 2
											bottom = img_height % 2
											# if either dimension was odd, expand the canvas
											if (right != 0 or bottom != 0):
												border = (0, 0, right, bottom)
												image = ImageOps.expand(image, border)
												image.save(ifile)
											# get the "display" dimensions
											img_width = img_width // 2
											img_height = img_height // 2

											# iBooks srcset bug: once srcset works in iBooks, we can use this line instead of the one below it
											# processed_xhtml = processed_xhtml.replace(line, f"<img class=\"mathml epub-type-se-image-color-depth-black-on-transparent\" epub:type=\"se:image.color-depth.black-on-transparent\" src=\"../images/mathml-{mathml_count}.png\" srcset=\"../images/mathml-{mathml_count}-2x.png 2x, ../images/mathml-{mathml_count}.png 1x\"/>")
											processed_xhtml = processed_xhtml.replace(line, f"<img class=\"mathml epub-type-se-image-color-depth-black-on-transparent\" epub:type=\"se:image.color-depth.black-on-transparent\" src=\"../images/mathml-{mathml_count}-2x.png\" height=\"{img_height}\" width=\"{img_width}\"/>")
											mathml_count = mathml_count + 1
										else:
											# Success! Replace the MathML with our new string.
											processed_xhtml = processed_xhtml.replace(line, processed_line)

								if processed_xhtml != xhtml:
									file.seek(0)
									file.write(processed_xhtml)
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

		# Include epub2 cover metadata
		cover_id = self.metadata_dom.xpath("//item[@properties=\"cover-image\"]/@id")[0].replace(".svg", ".jpg")
		metadata_xml = regex.sub(r"(<metadata[^>]+?>)", f"\\1\n\t\t<meta content=\"{cover_id}\" name=\"cover\" />", metadata_xml)

		# Add metadata to content.opf indicating this file is a Standard Ebooks compatibility build
		metadata_xml = metadata_xml.replace("<dc:publisher", "<meta property=\"se:transform\">compatibility</meta>\n\t\t<dc:publisher")

		# Add any new MathML images we generated to the manifest
		if has_mathml:
			for root, _, filenames in os.walk(work_epub_root_directory / "epub" / "images"):
				filenames = natsorted(filenames)
				filenames.reverse()
				for filename_string in filenames:
					filename = Path(root) / filename_string
					if filename.name.startswith("mathml-"):
						metadata_xml = metadata_xml.replace("<manifest>", f"<manifest><item href=\"images/{filename.name}\" id=\"{filename.name}\" media-type=\"image/png\"/>")

			metadata_xml = regex.sub(r"properties=\"([^\"]*?)mathml([^\"]*?)\"", "properties=\"\\1\\2\"", metadata_xml)

		metadata_xml = regex.sub(r"properties=\"\s*\"", "", metadata_xml)

		# Generate our NCX file for epub2 compatibility.
		# First find the ToC file.
		toc_filename = self.metadata_dom.xpath("//item[@properties=\"nav\"]/@href")[0]
		metadata_xml = metadata_xml.replace("<spine>", "<spine toc=\"ncx\">")
		metadata_xml = metadata_xml.replace("<manifest>", "<manifest><item href=\"toc.ncx\" id=\"ncx\" media-type=\"application/x-dtbncx+xml\" />")

		# Now use an XSLT transform to generate the NCX
		with importlib_resources.path("se.data", "navdoc2ncx.xsl") as navdoc2ncx_xsl_filename:
			toc_tree = se.epub.convert_toc_to_ncx(work_epub_root_directory, toc_filename, navdoc2ncx_xsl_filename)

		# Convert the <nav> landmarks element to the <guide> element in content.opf
		guide_xhtml = "<guide>"
		for element in toc_tree.xpath("//nav[@epub:type=\"landmarks\"]/ol/li/a"):
			element_xhtml = element.to_string()
			element_xhtml = regex.sub(r"epub:type=\"([^\"]*)(\s*frontmatter\s*|\s*backmatter\s*)([^\"]*)\"", "type=\"\\1\\3\"", element_xhtml)
			element_xhtml = regex.sub(r"epub:type=\"[^\"]*(acknowledgements|bibliography|colophon|copyright-page|cover|dedication|epigraph|foreword|glossary|index|loi|lot|notes|preface|bodymatter|titlepage|toc)[^\"]*\"", "type=\"\\1\"", element_xhtml)
			element_xhtml = element_xhtml.replace("type=\"copyright-page", "type=\"copyright page")

			# We add the 'text' attribute to the titlepage to tell the reader to start there
			element_xhtml = element_xhtml.replace("type=\"titlepage", "type=\"title-page text")

			element_xhtml = regex.sub(r"type=\"\s*\"", "", element_xhtml)
			element_xhtml = element_xhtml.replace("<a", "<reference")
			element_xhtml = regex.sub(r">(.+)</a>", " title=\"\\1\" />", element_xhtml)

			# Replace instances of the `role` attribute since it's illegal in content.opf
			element_xhtml = regex.sub(r" role=\".*?\"", "", element_xhtml)

			guide_xhtml = guide_xhtml + element_xhtml

		guide_xhtml = guide_xhtml + "</guide>"

		metadata_xml = metadata_xml.replace("</package>", "") + guide_xhtml + "</package>"

		# Guide is done, now write content.opf and clean it.
		# Output the modified content.opf before making more epub2 compatibility hacks.
		with open(work_epub_root_directory / "epub" / "content.opf", "w", encoding="utf-8") as file:
			file.write(metadata_xml)
			file.truncate()

		# All done, clean the output
		for filepath in se.get_target_filenames([work_epub_root_directory], (".xhtml", ".svg", ".opf", ".ncx")):
			se.formatting.format_xml_file(filepath)

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

					# epubcheck 4.2.4 has a bug where the glossary attribute is not allowed in content.opf.
					# If that's the only error we have, continue as if we passed.
					# This check can be removed once epubcheck fixes their bug.
					split_output = output.split("\n")
					bugged_epubcheck = len(split_output) == 1 and "OPF-015" in split_output[0] and "glossary" in split_output[0]

					if not bugged_epubcheck:
						# Try to linkify files in output if we can find them
						try:
							output = regex.sub(r"(ERROR\(.+?\): )(.+?)(\([0-9]+,[0-9]+\))", lambda match: match.group(1) + "[path][link=file://" + str(self.path / "src" / regex.sub(fr"^\..+?\.epub{os.sep}", "", match.group(2))) + "]" + match.group(2) + "[/][/]" + match.group(3), output)
						except:
							# If something goes wrong, just pass through the usual output
							pass

						raise se.BuildFailedException(f"[bash]epubcheck[/] v{version} failed with:\n{output}") from ex

		if build_kindle:
			# There's a bug in Calibre <= 3.48.0 where authors who have more than one MARC relator role
			# display as "unknown author" in the Kindle interface.
			# See: https://bugs.launchpad.net/calibre/+bug/1844578
			# Until the bug is fixed, we simply remove any other MARC relator on the dc:creator element.
			# Once the bug is fixed, we can remove this block.
			with open(work_epub_root_directory / "epub" / "content.opf", "r+", encoding="utf-8") as file:
				xhtml = file.read()

				processed_xhtml = xhtml

				for match in regex.findall(r"<meta property=\"role\" refines=\"#author\" scheme=\"marc:relators\">.*?</meta>", xhtml):
					if ">aut<" not in match:
						processed_xhtml = processed_xhtml.replace(match, "")

				if processed_xhtml != xhtml:
					file.seek(0)
					file.write(processed_xhtml)
					file.truncate()

			# Kindle doesn't go more than 2 levels deep for ToC, so flatten it here.
			with open(work_epub_root_directory / "epub" / toc_filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				dom = se.formatting.EasyXhtmlTree(xhtml)

				for node in dom.xpath("//ol/li/ol/li/ol"):
					node.lxml_element.getparent().addnext(node.lxml_element)
					node.unwrap()

				file.seek(0)
				file.write(dom.to_string())
				file.truncate()

			# Rebuild the NCX
			with importlib_resources.path("se.data", "navdoc2ncx.xsl") as navdoc2ncx_xsl_filename:
				toc_tree = se.epub.convert_toc_to_ncx(work_epub_root_directory, toc_filename, navdoc2ncx_xsl_filename)

			# Clean just the ToC and NCX
			for filepath in [work_epub_root_directory / "epub" / "toc.ncx", work_epub_root_directory / "epub" / toc_filename]:
				se.formatting.format_xml_file(filepath)

			# Convert endnotes to Kindle popup compatible notes
			if (work_epub_root_directory / "epub/text/endnotes.xhtml").is_file():
				with open(work_epub_root_directory / "epub/text/endnotes.xhtml", "r+", encoding="utf-8") as file:
					xhtml = file.read()

					# We have to remove the default namespace declaration from our document, otherwise
					# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
					try:
						tree = etree.fromstring(str.encode(xhtml.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")))
					except Exception as ex:
						raise se.InvalidXhtmlException(f"Error parsing XHTML [path][link=file://{(work_epub_root_directory / 'epub/text/endnotes.xhtml').resolve()}]endnotes.xhtml[/][/]. Exception: {ex}")

					notes = tree.xpath("//li[@epub:type=\"endnote\" or @epub:type=\"footnote\"]", namespaces=se.XHTML_NAMESPACES)

					processed_endnotes = ""

					for note in notes:
						note_id = note.get("id")
						note_number = note_id.replace("note-", "")

						# First, fixup the reference link for this endnote
						try:
							ref_link = etree.tostring(note.xpath("p[last()]/a[last()]")[0], encoding="unicode", pretty_print=True, with_tail=False).replace(" xmlns:epub=\"http://www.idpf.org/2007/ops\"", "").strip()
						except Exception as ex:
							raise se.InvalidXhtmlException(f"Can’t find ref link for [url]#{note_id}[/].") from ex

						new_ref_link = regex.sub(r">.*?</a>", ">" + note_number + "</a>.", ref_link)

						# Now remove the wrapping li node from the note
						note_text = regex.sub(r"^<li[^>]*?>(.*)</li>$", r"\1", etree.tostring(note, encoding="unicode", pretty_print=True, with_tail=False), flags=regex.IGNORECASE | regex.DOTALL)

						# Insert our new ref link
						result = regex.subn(r"^\s*<p([^>]*?)>", "<p\\1 id=\"" + note_id + "\">" + new_ref_link + " ", note_text)

						# Sometimes there is no leading <p> tag (for example, if the endnote starts with a blockquote
						# If that's the case, just insert one in front.
						note_text = result[0]
						if result[1] == 0:
							note_text = "<p id=\"" + note_id + "\">" + new_ref_link + "</p>" + note_text

						# Now remove the old ref_link
						note_text = note_text.replace(ref_link, "")

						# Trim trailing spaces left over after removing the ref link
						note_text = regex.sub(r"\s+</p>", "</p>", note_text).strip()

						# Sometimes ref links are in their own p tag--remove that too
						note_text = regex.sub(r"<p>\s*</p>", "", note_text)

						processed_endnotes += note_text + "\n"

					# All done with endnotes, so drop them back in
					xhtml = regex.sub(r"<ol>.*</ol>", processed_endnotes, xhtml, flags=regex.IGNORECASE | regex.DOTALL)

					file.seek(0)
					file.write(xhtml)
					file.truncate()

				# While Kindle now supports soft hyphens, popup endnotes break words but don't insert the hyphen characters.  So for now, remove soft hyphens from the endnotes file.
				with open(work_epub_root_directory / "epub" / "text" / "endnotes.xhtml", "r+", encoding="utf-8") as file:
					xhtml = file.read()
					processed_xhtml = xhtml

					processed_xhtml = processed_xhtml.replace(se.SHY_HYPHEN, "")

					if processed_xhtml != xhtml:
						file.seek(0)
						file.write(processed_xhtml)
						file.truncate()

			# Do some compatibility replacements
			for root, _, filenames in os.walk(work_epub_root_directory):
				for filename_string in filenames:
					filename = Path(root) / filename_string
					if filename.suffix == ".xhtml":
						with open(filename, "r+", encoding="utf-8") as file:
							xhtml = file.read()
							processed_xhtml = xhtml

							# Kindle doesn't recognize most zero-width spaces or word joiners, so just remove them.
							# It does recognize the word joiner character, but only in the old mobi7 format.  The new format renders them as spaces.
							processed_xhtml = processed_xhtml.replace(se.ZERO_WIDTH_SPACE, "")

							# Remove the epub:type attribute, as Calibre turns it into just "type"
							processed_xhtml = regex.sub(r"epub:type=\"[^\"]*?\"", "", processed_xhtml)

							if processed_xhtml != xhtml:
								file.seek(0)
								file.write(processed_xhtml)
								file.truncate()

			# Include compatibility CSS
			with open(work_epub_root_directory / "epub" / "css" / "core.css", "a", encoding="utf-8") as core_css_file:
				with importlib_resources.open_text("se.data.templates", "kindle.css", encoding="utf-8") as compatibility_css_file:
					core_css_file.write(compatibility_css_file.read())

			# Add soft hyphens
			for filepath in se.get_target_filenames([work_epub_root_directory], (".xhtml",)):
				se.typography.hyphenate_file(filepath, None, True)

			# Build an epub file we can send to Calibre
			se.epub.write_epub(work_epub_root_directory, work_directory / compatible_epub_output_filename)

			# Generate the Kindle file
			# We place it in the work directory because later we have to update the asin, and the mobi.update_asin() function will write to the final output directory
			cover_path = work_epub_root_directory / "epub" / self.metadata_dom.xpath("//item[@properties=\"cover-image\"]/@href")[0].replace(".svg", ".jpg")

			# Path arguments must be cast to string for Windows compatibility.
			return_code = subprocess.run([str(ebook_convert_path), str(work_directory / compatible_epub_output_filename), str(work_directory / kindle_output_filename), "--pretty-print", "--no-inline-toc", "--max-toc-links=0", "--prefer-metadata-cover", f"--cover={cover_path}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode

			if return_code:
				raise se.InvalidSeEbookException("[bash]ebook-convert[/] failed.")

			# Success, extract the Kindle cover thumbnail

			# Update the ASIN in the generated file
			mobi.update_asin(asin, work_directory / kindle_output_filename, output_directory / kindle_output_filename)

			# Extract the thumbnail
			kindle_cover_thumbnail = Image.open(work_epub_root_directory / "epub" / "images" / "cover.jpg")
			kindle_cover_thumbnail = kindle_cover_thumbnail.convert("RGB") # Remove alpha channel from PNG if necessary
			kindle_cover_thumbnail = kindle_cover_thumbnail.resize((432, 648))
			kindle_cover_thumbnail.save(output_directory / f"thumbnail_{asin}_EBOK_portrait.jpg")
