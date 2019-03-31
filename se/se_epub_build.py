#!/usr/bin/env python3
"""
This module contains the build function.

Strictly speaking, the build() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

import sys
import os
import errno
import shutil
from distutils.dir_util import copy_tree
import tempfile
from hashlib import sha1
import glob
import subprocess
import fnmatch
import regex
from pkg_resources import resource_filename
import lxml.cssselect
import lxml.etree as etree
from bs4 import BeautifulSoup
import se
import se.formatting
import se.easy_xml
import se.epub
import se.mobi
import se.typography
import se.images
import se.kobo


COVER_SVG_WIDTH = 1400
COVER_SVG_HEIGHT = 2100
COVER_THUMBNAIL_WIDTH = COVER_SVG_WIDTH / 4
COVER_THUMBNAIL_HEIGHT = COVER_SVG_HEIGHT / 4
SVG_OUTER_STROKE_WIDTH = 2
SVG_TITLEPAGE_OUTER_STROKE_WIDTH = 4

def build(self, metadata_xhtml, metadata_tree, run_epubcheck, build_kobo, build_kindle, output_directory, proof, build_covers, verbose):
	"""
	Entry point for `se build`
	"""

	calibre_app_mac_path = "/Applications/calibre.app/Contents/MacOS/"
	epubcheck_path = shutil.which("epubcheck")
	ebook_convert_path = shutil.which("ebook-convert")
	# Look for default Mac calibre app path if none found in path
	if ebook_convert_path is None and os.path.exists(calibre_app_mac_path):
		ebook_convert_path = os.path.join(calibre_app_mac_path, "ebook-convert")
	rsvg_convert_path = shutil.which("rsvg-convert")
	convert_path = shutil.which("convert")
	navdoc2ncx_xsl_filename = resource_filename("se", os.path.join("data", "navdoc2ncx.xsl"))
	mathml_xsl_filename = resource_filename("se", os.path.join("data", "mathmlcontent2presentation.xsl"))

	# Check for some required tools
	if run_epubcheck and epubcheck_path is None:
		raise se.MissingDependencyException("Couldn’t locate epubcheck. Is it installed?")

	if rsvg_convert_path is None:
		raise se.MissingDependencyException("Couldn’t locate rsvg-convert. Is librsvg2-bin installed?")

	if build_kindle and ebook_convert_path is None:
		raise se.MissingDependencyException("Couldn’t locate ebook-convert. Is Calibre installed?")

	if build_kindle and convert_path is None:
		raise se.MissingDependencyException("Couldn’t locate convert. Is Imagemagick installed?")

	# Check the output directory and create it if it doesn't exist
	if output_directory is None:
		output_directory = os.getcwd()
	else:
		output_directory = output_directory

	output_directory = os.path.abspath(output_directory)

	if os.path.exists(output_directory):
		if not os.path.isdir(output_directory):
			raise se.InvalidInputException("Not a directory: {}".format(output_directory))
	else:
		# Doesn't exist, try to create it
		try:
			os.makedirs(output_directory)
		except OSError as exception:
			if exception.errno != errno.EEXIST:
				raise se.FileExistsException("Couldn’t create output directory.")

	# All clear to start building!
	if verbose:
		print("Building {} ...".format(self.directory))

	with tempfile.TemporaryDirectory() as work_directory:
		work_epub_root_directory = os.path.join(work_directory, "src")

		copy_tree(self.directory, work_directory)
		try:
			shutil.rmtree(os.path.join(work_directory, ".git"))
		except Exception:
			pass

		# By convention the ASIN is set to the SHA-1 sum of the book's identifying URL
		identifier = metadata_tree.xpath("//dc:identifier")[0].inner_html().replace("url:", "")
		asin = sha1(identifier.encode("utf-8")).hexdigest()

		title = metadata_tree.xpath("//dc:title")[0].inner_html()
		url_title = se.formatting.make_url_safe(title)

		url_author = ""
		for author in metadata_tree.xpath("//dc:creator"):
			url_author = url_author + se.formatting.make_url_safe(author.inner_html()) + "_"

		url_author = url_author.rstrip("_")

		epub_output_filename = "{}_{}{}.epub".format(url_author, url_title, ".proof" if proof else "")
		epub3_output_filename = "{}_{}{}.epub3".format(url_author, url_title, ".proof" if proof else "")
		kobo_output_filename = "{}_{}{}.kepub.epub".format(url_author, url_title, ".proof" if proof else "")
		kindle_output_filename = "{}_{}{}.azw3".format(url_author, url_title, ".proof" if proof else "")

		# Clean up old output files if any
		for kindle_thumbnail in glob.glob(os.path.join(output_directory, "thumbnail_{}_EBOK_portrait.jpg".format(asin))):
			se.quiet_remove(kindle_thumbnail)
		se.quiet_remove(os.path.join(output_directory, "cover.jpg"))
		se.quiet_remove(os.path.join(output_directory, "cover-thumbnail.jpg"))
		se.quiet_remove(os.path.join(output_directory, epub_output_filename))
		se.quiet_remove(os.path.join(output_directory, epub3_output_filename))
		se.quiet_remove(os.path.join(output_directory, kobo_output_filename))
		se.quiet_remove(os.path.join(output_directory, kindle_output_filename))

		# Are we including proofreading CSS?
		if proof:
			with open(os.path.join(work_epub_root_directory, "epub", "css", "local.css"), "a", encoding="utf-8") as local_css_file:
				with open(resource_filename("se", os.path.join("data", "templates", "proofreading.css")), "r", encoding="utf-8") as proofreading_css_file:
					local_css_file.write(proofreading_css_file.read())

		# Update the release date in the metadata and colophon
		if self.last_commit:
			last_updated_iso = regex.sub(r"\.[0-9]+$", "", self.last_commit.timestamp.isoformat()) + "Z"
			last_updated_iso = regex.sub(r"\+.+?Z$", "Z", last_updated_iso)
			last_updated_friendly = "{0:%B %e, %Y, %l:%M <abbr class=\"time eoc\">%p</abbr>}".format(self.last_commit.timestamp)
			last_updated_friendly = regex.sub(r"\s+", " ", last_updated_friendly).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

			# Set modified date in content.opf
			self.metadata_xhtml = regex.sub(r"<meta property=\"dcterms:modified\">[^<]+?</meta>", "<meta property=\"dcterms:modified\">{}</meta>".format(last_updated_iso), self.metadata_xhtml)

			with open(os.path.join(work_epub_root_directory, "epub", "content.opf"), "w", encoding="utf-8") as file:
				file.seek(0)
				file.write(self.metadata_xhtml)
				file.truncate()

			# Update the colophon with release info
			with open(os.path.join(work_epub_root_directory, "epub", "text", "colophon.xhtml"), "r+", encoding="utf-8") as file:
				xhtml = file.read()

				xhtml = xhtml.replace("<p>The first edition of this ebook was released on<br/>", "<p>This edition was released on<br/>\n\t\t\t<b>{}</b><br/>\n\t\t\tand is based on<br/>\n\t\t\t<b>revision {}</b>.<br/>\n\t\t\tThe first edition of this ebook was released on<br/>".format(last_updated_friendly, self.last_commit.short_sha))

				file.seek(0)
				file.write(xhtml)
				file.truncate()

		# Output the pure epub3 file
		if verbose:
			print("\tBuilding {} ...".format(epub3_output_filename), end="", flush=True)

		se.epub.write_epub(work_epub_root_directory, os.path.join(output_directory, epub3_output_filename))

		if verbose:
			print(" OK")

		if build_kobo:
			if verbose:
				print("\tBuilding {} ...".format(kobo_output_filename), end="", flush=True)
		else:
			if verbose:
				print("\tBuilding {} ...".format(epub_output_filename), end="", flush=True)

		# Now add epub2 compatibility.

		# Include compatibility CSS
		with open(os.path.join(work_epub_root_directory, "epub", "css", "core.css"), "a", encoding="utf-8") as core_css_file:
			with open(resource_filename("se", os.path.join("data", "templates", "compatibility.css")), "r", encoding="utf-8") as compatibility_css_file:
				core_css_file.write(compatibility_css_file.read())

		# Simplify CSS and tags
		total_css = ""

		# Simplify the CSS first.  Later we'll update the document to match our simplified selectors.
		# While we're doing this, we store the original css into a single variable so we can extract the original selectors later.
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename in fnmatch.filter(filenames, "*.css"):
				with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
					css = file.read()

					# Before we do anything, we process a special case in core.css
					if "core.css" in filename:
						css = regex.sub(r"abbr{.+?}", "", css, flags=regex.DOTALL)

					total_css = total_css + css + "\n"
					file.seek(0)
					file.write(se.formatting.simplify_css(css))
					file.truncate()

		# Now get a list of original selectors
		# Remove @supports(){}
		total_css = regex.sub(r"@supports.+?{(.+?)}\s*}", "\\1}", total_css, flags=regex.DOTALL)

		# Remove CSS rules
		total_css = regex.sub(r"{[^}]+}", "", total_css)

		# Remove trailing commas
		total_css = regex.sub(r",", "", total_css)

		# Remove comments
		total_css = regex.sub(r"/\*.+?\*/", "", total_css, flags=regex.DOTALL)

		# Remove @ defines
		total_css = regex.sub(r"^@.+", "", total_css, flags=regex.MULTILINE)

		# Construct a dictionary of the original selectors
		selectors = set([line for line in total_css.splitlines() if line != ""])

		# Get a list of .xhtml files to simplify
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename in fnmatch.filter(filenames, "*.xhtml"):
				# Don't mess with the ToC, since if we have ol/li > first-child selectors we could screw it up
				if filename == "toc.xhtml":
					continue

				with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
					# We have to remove the default namespace declaration from our document, otherwise
					# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
					xhtml = file.read().replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")
					processed_xhtml = xhtml
					try:
						tree = etree.fromstring(str.encode(xhtml))
					except Exception as ex:
						raise se.InvalidXhtmlException("Error parsing XHTML file: {}\n{}".format(filename, ex))

					# Now iterate over each CSS selector and see if it's used in any of the files we found
					force_convert = False
					for selector in selectors:
						try:
							sel = lxml.cssselect.CSSSelector(selector, translator="xhtml", namespaces=se.XHTML_NAMESPACES)

							# Add classes to elements that match any of our selectors to simplify. For example, if we select :first-child, add a "first-child" class to all elements that match that.
							for selector_to_simplify in se.SELECTORS_TO_SIMPLIFY:
								if selector_to_simplify in selector:
									selector_to_simplify = selector_to_simplify.replace(":", "")
									for element in tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
										current_class = element.get("class")
										if current_class is not None and selector_to_simplify not in current_class:
											current_class = current_class + " " + selector_to_simplify
										else:
											current_class = selector_to_simplify

										element.set("class", current_class)

						except lxml.cssselect.ExpressionError:
							# This gets thrown if we use pseudo-elements, which lxml doesn't support
							# We force a check if we get thrown this because we might miss some important ::before elements
							force_convert = True

						# We've already replaced attribute/namespace selectors with classes in the CSS, now add those classes to the matching elements
						if force_convert or "[epub|type" in selector:
							for namespace_selector in regex.findall(r"\[epub\|type\~\=\"[^\"]*?\"\]", selector):
								sel = lxml.cssselect.CSSSelector(namespace_selector, translator="xhtml", namespaces=se.XHTML_NAMESPACES)

								for element in tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
									new_class = regex.sub(r"^\.", "", se.formatting.namespace_to_class(namespace_selector))
									current_class = element.get("class", "")

									if new_class not in current_class:
										current_class = "{} {}".format(current_class, new_class).strip()
										element.set("class", current_class)

					processed_xhtml = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + etree.tostring(tree, encoding=str, pretty_print=True)

					# We do this round in a second pass because if we modify the tree like this, it screws up how lxml does processing later.
					# If it's all done in one pass, we wind up in a race condition where some elements are fixed and some not
					tree = etree.fromstring(str.encode(processed_xhtml))

					for selector in selectors:
						try:
							sel = lxml.cssselect.CSSSelector(selector, translator="xhtml", namespaces=se.XHTML_NAMESPACES)
						except lxml.cssselect.ExpressionError:
							# This gets thrown if we use pseudo-elements, which lxml doesn't support
							continue

						# Convert <abbr> to <span>
						if "abbr" in selector:
							for element in tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
								# Why would you want the tail to output by default?!?
								raw_string = etree.tostring(element, encoding=str, with_tail=False)

								# lxml--crap as usual--includes a bunch of namespace information in every element we print.
								# Remove it here.
								raw_string = raw_string.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")
								raw_string = raw_string.replace(" xmlns:epub=\"http://www.idpf.org/2007/ops\"", "")

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
		# We used to be able to use `convert` to convert svg -> jpg in one step, but at some point a bug
		# was introduced to `convert` that caused it to crash in this situation. Now, we first use rsvg-convert
		# to convert to svg -> png, then `convert` to convert png -> jpg.
		subprocess.run([rsvg_convert_path, "--keep-aspect-ratio", "--format", "png", "--output", os.path.join(work_directory, 'cover.png'), os.path.join(work_epub_root_directory, "epub", "images", "cover.svg")])
		subprocess.run([convert_path, "-format", "jpg", os.path.join(work_directory, 'cover.png'), os.path.join(work_epub_root_directory, "epub", "images", "cover.jpg")])
		os.remove(os.path.join(work_directory, 'cover.png'))

		if build_covers:
			shutil.copy2(os.path.join(work_epub_root_directory, "epub", "images", "cover.jpg"), os.path.join(output_directory, "cover.jpg"))
			shutil.copy2(os.path.join(work_epub_root_directory, "epub", "images", "cover.svg"), os.path.join(output_directory, "cover-thumbnail.svg"))
			subprocess.run([rsvg_convert_path, "--keep-aspect-ratio", "--format", "png", "--output", os.path.join(work_directory, 'cover-thumbnail.png'), os.path.join(output_directory, "cover-thumbnail.svg")])
			subprocess.run([convert_path, "-resize", "{}x{}".format(COVER_THUMBNAIL_WIDTH, COVER_THUMBNAIL_HEIGHT), "-quality", "100", "-format", "jpg", os.path.join(work_directory, 'cover-thumbnail.png'), os.path.join(output_directory, "cover-thumbnail.jpg")])
			os.remove(os.path.join(work_directory, 'cover-thumbnail.png'))
			os.remove(os.path.join(output_directory, "cover-thumbnail.svg"))

		os.remove(os.path.join(work_epub_root_directory, "epub", "images", "cover.svg"))

		# Massage image references in content.opf
		metadata_xhtml = metadata_xhtml.replace("cover.svg", "cover.jpg")
		metadata_xhtml = metadata_xhtml.replace(".svg", ".png")
		metadata_xhtml = metadata_xhtml.replace("id=\"cover.jpg\" media-type=\"image/svg+xml\"", "id=\"cover.jpg\" media-type=\"image/jpeg\"")
		metadata_xhtml = metadata_xhtml.replace("image/svg+xml", "image/png")
		metadata_xhtml = regex.sub(r"properties=\"([^\"]*?)svg([^\"]*?)\"", "properties=\"\\1\\2\"", metadata_xhtml) # We may also have the `mathml` property

		# NOTE: even though the a11y namespace is reserved by the epub spec, we must declare it because epubcheck doesn't know that yet.
		# Once epubcheck understands the a11y namespace is reserved, we can remove it from the namespace declarations.
		metadata_xhtml = metadata_xhtml.replace(" prefix=\"se: https://standardebooks.org/vocab/1.0\"", " prefix=\"se: https://standardebooks.org/vocab/1.0, a11y: https://www.idpf.org/epub/vocab/package/a11y/\"")

		# Google Play Books chokes on https XML namespace identifiers (as of at least 2017-07)
		metadata_xhtml = metadata_xhtml.replace("https://standardebooks.org/vocab/1.0", "http://standardebooks.org/vocab/1.0")
		metadata_xhtml = metadata_xhtml.replace("https://www.idpf.org/epub/vocab/package/a11y/", "http://www.idpf.org/epub/vocab/package/a11y/")

		# Output the modified content.opf so that we can build the kobo book before making more epub2 compatibility hacks
		with open(os.path.join(work_epub_root_directory, "epub", "content.opf"), "w", encoding="utf-8") as file:
			file.write(metadata_xhtml)
			file.truncate()

		# Recurse over xhtml files to make some compatibility replacements
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename in filenames:
				if filename.lower().endswith(".svg"):
					# For night mode compatibility, give the titlepage a 1px white stroke attribute
					if filename.lower() == "titlepage.svg" or filename.lower() == "logo.svg":
						with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
							svg = file.read()
							paths = svg

							# What we're doing here is faking the `stroke-align: outside` property, which is an unsupported draft spec right now.
							# We do this by duplicating all the SVG paths, and giving the duplicates a 2px stroke.  The originals are directly on top,
							# so the 2px stroke becomes a 1px stroke that's *outside* of the path instead of being *centered* on the path border.
							# This looks much nicer, but we also have to increase the image size by 2px in both directions, and re-center the whole thing.

							if filename.lower() == "titlepage.svg":
								stroke_width = SVG_TITLEPAGE_OUTER_STROKE_WIDTH
							else:
								stroke_width = SVG_OUTER_STROKE_WIDTH

							# First, strip out non-path, non-group elements
							paths = regex.sub(r"<\?xml[^<]+?\?>", "", paths)
							paths = regex.sub(r"</?svg[^<]*?>", "", paths)
							paths = regex.sub(r"<title>[^<]+?</title>", "", paths)
							paths = regex.sub(r"<desc>[^<]+?</desc>", "", paths)

							# `paths` is now our "duplicate".  Add a 2px stroke.
							paths = paths.replace("<path", "<path style=\"stroke: #ffffff; stroke-width: {}px;\"".format(stroke_width))

							# Inject the duplicate under the old SVG paths.  We do this by only replacing the first regex match for <g> or <path>
							svg = regex.sub(r"(<g|<path)", "{}\\1".format(paths), svg, 1)

							# If this SVG specifies height/width, then increase height and width by 2 pixels and translate everything by 1px
							try:
								height = int(regex.search(r"<svg[^>]+?height=\"([0-9]+)\"", svg).group(1)) + stroke_width
								svg = regex.sub(r"<svg([^<]*?)height=\"[0-9]+\"", "<svg\\1height=\"{}\"".format(height), svg)

								width = int(regex.search(r"<svg[^>]+?width=\"([0-9]+)\"", svg).group(1)) + stroke_width
								svg = regex.sub(r"<svg([^<]*?)width=\"[0-9]+\"", "<svg\\1width=\"{}\"".format(width), svg)

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
					# We use `rsvg-convert` instead of `inkscape` or `convert` because it gives us an easy way of zooming in at 2x
					subprocess.run([rsvg_convert_path, "--zoom", "2", "--keep-aspect-ratio", "--format", "png", "--output", regex.sub(r"\.svg$", ".png", os.path.join(root, filename)), os.path.join(root, filename)])
					os.remove(os.path.join(root, filename))

				if filename.lower().endswith(".xhtml"):
					with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
						xhtml = file.read()
						processed_xhtml = xhtml

						# Check if there's any MathML to convert.
						# We expect MathML to be the "content" type (versus the "presentational" type).
						# We use an XSL transform to convert from "content" to "presentational" MathML.
						# If we start with presentational, then nothing will be changed.
						# Kobo supports presentational MathML. After we build kobo, we convert the presentational MathML to PNG for the rest of the builds.
						mathml_transform = None
						for line in regex.findall(r"<(?:m:)?math[^>]*?>(.+?)</(?:m:)?math>", processed_xhtml, flags=regex.DOTALL):
							mathml_content_tree = se.easy_xml.EasyXmlTree("<?xml version=\"1.0\" encoding=\"utf-8\"?><math xmlns=\"http://www.w3.org/1998/Math/MathML\">{}</math>".format(regex.sub(r"<(/?)m:", "<\\1", line)))

							# Initialize the transform object, if we haven't yet
							if not mathml_transform:
								mathml_transform = etree.XSLT(etree.parse(mathml_xsl_filename))

							# Transform the mathml and get a string representation
							# XSLT comes from https://github.com/fred-wang/webextension-content-mathml-polyfill
							mathml_presentation_tree = mathml_transform(mathml_content_tree.etree)
							mathml_presentation_xhtml = etree.tostring(mathml_presentation_tree, encoding="unicode", pretty_print=True, with_tail=False).strip()

							# Plop our string back in to the XHTML we're processing
							processed_xhtml = regex.sub(r"<math[^>]*?>\{}\</math>".format(regex.escape(line)), mathml_presentation_xhtml, processed_xhtml, flags=regex.MULTILINE)

						# Add ARIA roles, which are just mostly duplicate attributes to epub:type (with the exception of rearnotes -> endnotes, and adding the `backlink` role which is not yet in epub 3.0)
						processed_xhtml = regex.sub(r"(epub:type=\"[^\"]*?rearnote(s?)[^\"]*?\")", "\\1 role=\"doc-endnote\\2\"", processed_xhtml)

						if filename == "endnotes.xhtml":
							processed_xhtml = processed_xhtml.replace(" epub:type=\"se:referrer\"", " role=\"doc-backlink\" epub:type=\"se:referrer\"")

							# iOS renders the left-arrow-hook character as an emoji; this fixes it and forces it to renderr as text.
							# See https://github.com/standardebooks/tools/issues/73
							# See http://mts.io/2015/04/21/unicode-symbol-render-text-emoji/
							processed_xhtml = processed_xhtml.replace("\u21a9", "\u21a9\ufe0e")

						for role in se.ARIA_ROLES:
							processed_xhtml = regex.sub(r"(epub:type=\"[^\"]*?{}[^\"]*?\")".format(role), "\\1 role=\"doc-{}\"".format(role), processed_xhtml)

						# Since we convert SVGs to raster, here we add the color-depth semantic for night mode
						processed_xhtml = processed_xhtml.replace("z3998:publisher-logo", "z3998:publisher-logo se:image.color-depth.black-on-transparent")
						processed_xhtml = regex.sub(r"class=\"([^\"]*?)epub-type-z3998-publisher-logo([^\"]*?)\"", "class=\"\\1epub-type-z3998-publisher-logo epub-type-se-image-color-depth-black-on-transparent\\2\"", processed_xhtml)

						# Special case for the titlepage
						if filename == "titlepage.xhtml":
							processed_xhtml = processed_xhtml.replace("<img", "<img class=\"epub-type-se-image-color-depth-black-on-transparent\" epub:type=\"se:image.color-depth.black-on-transparent\"")

						# Google Play Books chokes on https XML namespace identifiers (as of at least 2017-07)
						processed_xhtml = processed_xhtml.replace("https://standardebooks.org/vocab/1.0", "http://standardebooks.org/vocab/1.0")

						# We converted svgs to pngs, so replace references
						processed_xhtml = processed_xhtml.replace("cover.svg", "cover.jpg")
						processed_xhtml = processed_xhtml.replace(".svg", ".png")

						# To get popup footnotes in iBooks, we have to change epub:rearnote to epub:footnote.
						# Remember to get our custom style selectors too.
						processed_xhtml = regex.sub(r"epub:type=\"([^\"]*?)rearnote([^\"]*?)\"", "epub:type=\"\\1footnote\\2\"", processed_xhtml)
						processed_xhtml = regex.sub(r"class=\"([^\"]*?)epub-type-rearnote([^\"]*?)\"", "class=\"\\1epub-type-footnote\\2\"", processed_xhtml)

						# Include extra lang tag for accessibility compatibility.
						processed_xhtml = regex.sub(r"xml:lang\=\"([^\"]+?)\"", "lang=\"\\1\" xml:lang=\"\\1\"", processed_xhtml)

						# Typography: replace double and triple em dash characters with extra em dashes.
						processed_xhtml = processed_xhtml.replace("⸺", "—{}—".format(se.WORD_JOINER))
						processed_xhtml = processed_xhtml.replace("⸻", "—{}—{}—".format(se.WORD_JOINER, se.WORD_JOINER))

						# Typography: replace some other less common characters.
						processed_xhtml = processed_xhtml.replace("⅒", "1/10")
						processed_xhtml = processed_xhtml.replace("℅", "c/o")
						processed_xhtml = processed_xhtml.replace("✗", "×")
						processed_xhtml = processed_xhtml.replace(" ", "{}{}".format(se.NO_BREAK_SPACE, se.NO_BREAK_SPACE)) # em-space to two nbsps

						# Many e-readers don't support the word joiner character (U+2060).
						# They DO, however, support the now-deprecated zero-width non-breaking space (U+FEFF)
						# For epubs, do this replacement.  Kindle now seems to handle everything fortunately.
						processed_xhtml = processed_xhtml.replace(se.WORD_JOINER, se.ZERO_WIDTH_SPACE)

						if processed_xhtml != xhtml:
							file.seek(0)
							file.write(processed_xhtml)
							file.truncate()

				if filename.lower().endswith(".css"):
					with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
						css = file.read()
						processed_css = css

						# To get popup footnotes in iBooks, we have to change epub:rearnote to epub:footnote.
						# Remember to get our custom style selectors too.
						processed_css = processed_css.replace("rearnote", "footnote")

						# Add new break-* aliases for compatibilty with newer readers.
						processed_css = regex.sub(r"(\s+)page-break-(.+?:\s.+?;)", "\\1page-break-\\2\t\\1break-\\2", processed_css)

						if processed_css != css:
							file.seek(0)
							file.write(processed_css)
							file.truncate()

		if build_kobo:
			with tempfile.TemporaryDirectory() as kobo_work_directory:
				copy_tree(work_epub_root_directory, kobo_work_directory)

				for root, _, filenames in os.walk(kobo_work_directory):
					# Add a note to content.opf indicating this is a transform build
					for filename in fnmatch.filter(filenames, "content.opf"):
						with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
							xhtml = file.read()

							xhtml = regex.sub(r"<dc:publisher", "<meta property=\"se:transform\">kobo</meta>\n\t\t<dc:publisher", xhtml)

							file.seek(0)
							file.write(xhtml)
							file.truncate()

					# Kobo .kepub files need each clause wrapped in a special <span> tag to enable highlighting.
					# Do this here. Hopefully Kobo will get their act together soon and drop this requirement.
					for filename in fnmatch.filter(filenames, "*.xhtml"):
						se.kobo.paragraph_counter = 1
						se.kobo.segment_counter = 1

						# Don't add spans to the ToC
						if filename == "toc.xhtml":
							continue

						with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
							xhtml = file.read()
							# Kobos don't have fonts that support the ↩ character in endnotes, so replace it with «
							if filename == "endnotes.xhtml":
								# Note that we replaced ↩ with \u21a9\ufe0e in an earlier iOS compatibility fix
								xhtml = regex.sub(r"epub:type=\"se:referrer\">\u21a9\ufe0e</a>", "epub:type=\"se:referrer\">«</a>", xhtml)

							# We have to remove the default namespace declaration from our document, otherwise
							# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
							try:
								tree = etree.fromstring(str.encode(xhtml.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")))
							except Exception as ex:
								raise se.InvalidXhtmlException("Error parsing XHTML file: {}\n{}".format(filename, ex), verbose)

							se.kobo.add_kobo_spans_to_node(tree.xpath("./body", namespaces=se.XHTML_NAMESPACES)[0])

							xhtml = etree.tostring(tree, encoding="unicode", pretty_print=True, with_tail=False)
							xhtml = regex.sub(r"<html:span", "<span", xhtml)
							xhtml = regex.sub(r"html:span>", "span>", xhtml)
							xhtml = regex.sub(r"<span xmlns:html=\"http://www.w3.org/1999/xhtml\"", "<span", xhtml)
							xhtml = regex.sub(r"<html", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<html xmlns=\"http://www.w3.org/1999/xhtml\"", xhtml)

							file.seek(0)
							file.write(xhtml)
							file.truncate()

				se.epub.write_epub(kobo_work_directory, os.path.join(output_directory, kobo_output_filename))

			if verbose:
				print(" OK")
				print("\tBuilding {} ...".format(epub_output_filename), end="", flush=True)

		# Now work on more epub2 compatibility

		# Recurse over css files to make some compatibility replacements.
		for root, _, filenames in os.walk(work_epub_root_directory):
			for filename in filenames:
				if filename.lower().endswith(".css"):
					with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
						css = file.read()
						processed_css = css

						processed_css = regex.sub(r"(page\-break\-(before|after|inside)\s*:\s*(.+))", "\\1\n\t-webkit-column-break-\\2: \\3 /* For Readium */", processed_css)
						processed_css = regex.sub(r"^\s*hyphens\s*:\s*(.+)", "\thyphens: \\1\n\tadobe-hyphenate: \\1\n\t-webkit-hyphens: \\1\n\t-epub-hyphens: \\1\n\t-moz-hyphens: \\1", processed_css, flags=regex.MULTILINE)
						processed_css = regex.sub(r"^\s*hyphens\s*:\s*none;", "\thyphens: none;\n\tadobe-text-layout: optimizeSpeed; /* For Nook */", processed_css, flags=regex.MULTILINE)

						if processed_css != css:
							file.seek(0)
							file.write(processed_css)
							file.truncate()

		# Sort out MathML compatibility
		has_mathml = "mathml" in metadata_xhtml
		if has_mathml:
			firefox_path = shutil.which("firefox")
			if firefox_path is None:
				raise se.MissingDependencyException("firefox is required to process MathML, but firefox couldn't be located. Is it installed?")

			mathml_count = 1
			for root, _, filenames in os.walk(work_epub_root_directory):
				for filename in filenames:
					if filename.lower().endswith(".xhtml"):
						with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
							xhtml = file.read()
							processed_xhtml = xhtml
							replaced_mathml = []

							# Check if there's MathML we want to convert
							# We take a naive approach and use some regexes to try to simplify simple MathML expressions.
							# For each MathML expression, if our round of regexes finishes and there is still MathML in the processed result, we abandon the attempt and render to PNG using Firefox.
							for line in regex.findall(r"<(?:m:)math[^>]*?>(?:.+?)</(?:m:)math>", processed_xhtml, flags=regex.DOTALL):
								if line not in replaced_mathml:
									replaced_mathml.append(line) # Store converted lines to save time in case we have multiple instances of the same MathML
									mathml_tree = se.easy_xml.EasyXmlTree("<?xml version=\"1.0\" encoding=\"utf-8\"?>{}".format(regex.sub(r"<(/?)m:", "<\\1", line)))
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
										processed_line = regex.sub(r"<(?:m:)?mo>{}</(?:m:)?mo>".format(se.FUNCTION_APPLICATION), "", processed_line, flags=regex.IGNORECASE) # The ignore case flag is required to match here with the special FUNCTION_APPLICATION character, it's unclear why
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
										se.images.render_mathml_to_png(regex.sub(r"<(/?)m:", "<\\1", line), os.path.join(work_epub_root_directory, "epub", "images", "mathml-{}.png".format(mathml_count)))

										processed_xhtml = processed_xhtml.replace(line, "<img class=\"mathml epub-type-se-image-color-depth-black-on-transparent\" epub:type=\"se:image.color-depth.black-on-transparent\" src=\"../images/mathml-{}.png\" />".format(mathml_count))
										mathml_count = mathml_count + 1
									else:
										# Success! Replace the MathML with our new string.
										processed_xhtml = processed_xhtml.replace(line, processed_line)

							if processed_xhtml != xhtml:
								file.seek(0)
								file.write(processed_xhtml)
								file.truncate()

		# Include epub2 cover metadata
		cover_id = metadata_tree.xpath("//opf:item[@properties=\"cover-image\"]/@id")[0].replace(".svg", ".jpg")
		metadata_xhtml = regex.sub(r"(<metadata[^>]+?>)", "\\1\n\t\t<meta content=\"{}\" name=\"cover\" />".format(cover_id), metadata_xhtml)

		# Add metadata to content.opf indicating this file is a Standard Ebooks compatibility build
		metadata_xhtml = metadata_xhtml.replace("<dc:publisher", "<meta property=\"se:transform\">compatibility</meta>\n\t\t<dc:publisher")

		# Add any new MathML images we generated to the manifest
		if has_mathml:
			for root, _, filenames in os.walk(os.path.join(work_epub_root_directory, "epub", "images")):
				filenames = se.natural_sort(filenames)
				filenames.reverse()
				for filename in filenames:
					if filename.lower().startswith("mathml-"):
						metadata_xhtml = metadata_xhtml.replace("<manifest>", "<manifest><item href=\"images/{}\" id=\"{}\" media-type=\"image/png\"/>".format(filename, filename))

			metadata_xhtml = regex.sub(r"properties=\"([^\"]*?)mathml([^\"]*?)\"", "properties=\"\\1\\2\"", metadata_xhtml)

		metadata_xhtml = regex.sub(r"properties=\"\s*\"", "", metadata_xhtml)

		# Generate our NCX file for epub2 compatibility.
		# First find the ToC file.
		toc_filename = metadata_tree.xpath("//opf:item[@properties=\"nav\"]/@href")[0]
		metadata_xhtml = metadata_xhtml.replace("<spine>", "<spine toc=\"ncx\">")
		metadata_xhtml = metadata_xhtml.replace("<manifest>", "<manifest><item href=\"toc.ncx\" id=\"ncx\" media-type=\"application/x-dtbncx+xml\" />")

		# Now use an XSLT transform to generate the NCX
		toc_tree = se.epub.convert_toc_to_ncx(work_epub_root_directory, toc_filename, navdoc2ncx_xsl_filename)

		# Convert the <nav> landmarks element to the <guide> element in content.opf
		guide_xhtml = "<guide>"
		for element in toc_tree.xpath("//xhtml:nav[@epub:type=\"landmarks\"]/xhtml:ol/xhtml:li/xhtml:a"):
			element_xhtml = element.tostring()
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

		metadata_xhtml = metadata_xhtml.replace("</package>", "") + guide_xhtml + "</package>"

		# Guide is done, now write content.opf and clean it.
		# Output the modified content.opf before making more epub2 compatibility hacks.
		with open(os.path.join(work_epub_root_directory, "epub", "content.opf"), "w", encoding="utf-8") as file:
			file.write(metadata_xhtml)
			file.truncate()

		# All done, clean the output
		for filename in se.get_target_filenames([work_epub_root_directory], (".xhtml", ".svg", ".opf", ".ncx")):
			se.formatting.format_xhtml_file(filename, False, filename.endswith("content.opf"), filename.endswith("endnotes.xhtml"))

		# Write the compatible epub
		se.epub.write_epub(work_epub_root_directory, os.path.join(output_directory, epub_output_filename))

		if verbose:
			print(" OK")

		if run_epubcheck:
			if verbose:
				print("\tRunning epubcheck on {} ...".format(epub_output_filename), end="", flush=True)

			output = subprocess.run([epubcheck_path, "--quiet", os.path.join(output_directory, epub_output_filename)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode().strip()

			# epubcheck on Ubuntu 18.04 outputs some seemingly harmless warnings; flush them here.
			if output:
				output = regex.sub(r"\s*Warning at char 3 in xsl:param/@select on line.+", "", output)
				output = regex.sub(r"\s*SXWN9000: The parent axis starting at a document node will never select anything", "", output)

			if output:
				if verbose:
					print("\n\t\t" + "\t\t".join(output.splitlines(True)), file=sys.stderr)
				else:
					print(output, file=sys.stderr)
				return

			if verbose:
				print(" OK")


		if build_kindle:
			if verbose:
				print("\tBuilding {} ...".format(kindle_output_filename), end="", flush=True)

			# Kindle doesn't go more than 2 levels deep for ToC, so flatten it here.
			with open(os.path.join(work_epub_root_directory, "epub", toc_filename), "r+", encoding="utf-8") as file:
				xhtml = file.read()

				soup = BeautifulSoup(xhtml, "lxml")

				for match in soup.select("ol > li > ol > li > ol"):
					match.unwrap()

				xhtml = str(soup)

				pattern = regex.compile(r"(<li>\s*<a href=\"[^\"]+?\">.+?</a>\s*)<li>")
				matches = 1
				while matches > 0:
					xhtml, matches = pattern.subn(r"\1</li><li>", xhtml)

				pattern = regex.compile(r"</li>\s*</li>")
				matches = 1
				while matches > 0:
					xhtml, matches = pattern.subn("</li>", xhtml)

				file.seek(0)
				file.write(xhtml)
				file.truncate()

			# Rebuild the NCX
			toc_tree = se.epub.convert_toc_to_ncx(work_epub_root_directory, toc_filename, navdoc2ncx_xsl_filename)

			# Clean just the ToC and NCX
			for filename in [os.path.join(work_epub_root_directory, "epub", "toc.ncx"), os.path.join(work_epub_root_directory, "epub", toc_filename)]:
				se.formatting.format_xhtml_file(filename, False)

			# Convert endnotes to Kindle popup compatible notes
			if os.path.isfile(os.path.join(work_epub_root_directory, "epub", "text", "endnotes.xhtml")):
				with open(os.path.join(work_epub_root_directory, "epub", "text", "endnotes.xhtml"), "r+", encoding="utf-8") as file:
					xhtml = file.read()

					# We have to remove the default namespace declaration from our document, otherwise
					# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
					try:
						tree = etree.fromstring(str.encode(xhtml.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")))
					except Exception as ex:
						raise se.InvalidXhtmlException("Error parsing XHTML file: endnotes.xhtml\n{}".format(ex))

					notes = tree.xpath("//li[@epub:type=\"rearnote\" or @epub:type=\"footnote\"]", namespaces=se.XHTML_NAMESPACES)

					processed_endnotes = ""

					for note in notes:
						note_id = note.get("id")
						note_number = note_id.replace("note-", "")

						# First, fixup the reference link for this endnote
						try:
							ref_link = etree.tostring(note.xpath("p[last()]/a[last()]")[0], encoding="unicode", pretty_print=True, with_tail=False).replace(" xmlns:epub=\"http://www.idpf.org/2007/ops\"", "").strip()
						except Exception:
							raise se.InvalidXhtmlException("Can’t find ref link for #{}.".format(note_id))

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
				with open(os.path.join(work_epub_root_directory, "epub", "text", "endnotes.xhtml"), "r+", encoding="utf-8") as file:
					xhtml = file.read()
					processed_xhtml = xhtml

					processed_xhtml = processed_xhtml.replace(se.SHY_HYPHEN, "")

					if processed_xhtml != xhtml:
						file.seek(0)
						file.write(processed_xhtml)
						file.truncate()

			# Do some compatibility replacements
			for root, _, filenames in os.walk(work_epub_root_directory):
				for filename in filenames:
					if filename.lower().endswith(".xhtml"):
						with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
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
			with open(os.path.join(work_epub_root_directory, "epub", "css", "core.css"), "a", encoding="utf-8") as core_css_file:
				with open(resource_filename("se", os.path.join("data", "templates", "kindle.css")), "r", encoding="utf-8") as compatibility_css_file:
					core_css_file.write(compatibility_css_file.read())

			# Add soft hyphens
			for filename in se.get_target_filenames([work_epub_root_directory], (".xhtml")):
				se.typography.hyphenate_file(filename, None, True)

			# Build an epub file we can send to Calibre
			se.epub.write_epub(work_epub_root_directory, os.path.join(work_directory, epub_output_filename))

			# Generate the Kindle file
			# We place it in the work directory because later we have to update the asin, and the se.mobi.update_asin() function will write to the final output directory
			cover_path = os.path.join(work_epub_root_directory, "epub", metadata_tree.xpath("//opf:item[@properties=\"cover-image\"]/@href")[0].replace(".svg", ".jpg"))
			return_code = subprocess.run([ebook_convert_path, os.path.join(work_directory, epub_output_filename), os.path.join(work_directory, kindle_output_filename), "--pretty-print", "--no-inline-toc", "--max-toc-links=0", "--prefer-metadata-cover", "--cover={}".format(cover_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode

			if return_code:
				raise se.InvalidSeEbookException("ebook-convert failed.")
			else:
				# Success, extract the Kindle cover thumbnail

				# Update the ASIN in the generated file
				se.mobi.update_asin(asin, os.path.join(work_directory, kindle_output_filename), os.path.join(output_directory, kindle_output_filename))

				# Extract the thumbnail
				subprocess.run([convert_path, os.path.join(work_epub_root_directory, "epub", "images", "cover.jpg"), "-resize", "432x660", os.path.join(output_directory, "thumbnail_{}_EBOK_portrait.jpg".format(asin))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

			if verbose:
				print(" OK")
