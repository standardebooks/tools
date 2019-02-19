#!/usr/bin/env python3
"""
Defines the SeEpub class, the master class for representing and operating on
Standard Ebooks epub3 files.
"""

import os
import filecmp
import glob
import html
import tempfile
import datetime
import errno
import shutil
import fnmatch
import concurrent.futures
import base64
import unicodedata
import subprocess
import io
import regex
import roman
from pkg_resources import resource_filename
import lxml.cssselect
import lxml.etree as etree
from bs4 import Tag, BeautifulSoup, NavigableString
import se
import se.formatting
import se.easy_xml
import se.images

def _process_endnotes_in_file(filename: str, root: str, note_range: range, step: int) -> None:
	"""
	Helper function for reordering endnotes.

	This has to be outside of the class to be able to be called by `executor`.
	"""

	with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
		xhtml = file.read()
		processed_xhtml = xhtml
		processed_xhtml_is_modified = False

		for endnote_number in note_range:
			# If we’ve already changed some notes and can’t find the next then we don’t need to continue searching
			if not "id=\"noteref-{}\"".format(endnote_number) in processed_xhtml and processed_xhtml_is_modified:
				break
			processed_xhtml = processed_xhtml.replace("id=\"noteref-{}\"".format(endnote_number), "id=\"noteref-{}\"".format(endnote_number + step), 1)
			processed_xhtml = processed_xhtml.replace("#note-{}\"".format(endnote_number), "#note-{}\"".format(endnote_number + step), 1)
			processed_xhtml = processed_xhtml.replace(">{}</a>".format(endnote_number), ">{}</a>".format(endnote_number + step), 1)
			processed_xhtml_is_modified = processed_xhtml_is_modified or (processed_xhtml != xhtml)

		if processed_xhtml_is_modified:
			file.seek(0)
			file.write(processed_xhtml)
			file.truncate()

class LintMessage:
	"""
	An object representing an output message for the lint function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	text = ""
	filename = ""
	message_type = se.MESSAGE_TYPE_WARNING
	is_submessage = False

	def __init__(self, text: str, message_type=se.MESSAGE_TYPE_WARNING, filename: str = "", is_submessage: bool = False):
		self.text = text.strip()
		self.filename = filename
		self.message_type = message_type
		self.is_submessage = is_submessage

class SeEpub:
	"""
	An object representing an SE epub file.

	An SE epub can have various operations performed on it, including recomposing and linting.
	"""

	directory = ""
	_metadata_xhtml = None
	_metadata_tree = None
	_generated_identifier = None
	_generated_github_repo_url = None

	@property
	def generated_identifier(self) -> str:
		"""
		Accessor
		"""

		if not self._generated_identifier:
			self._generated_identifier = self._generate_identifier()

		return self._generated_identifier

	@property
	def generated_github_repo_url(self) -> str:
		"""
		Accessor
		"""

		if not self._generated_github_repo_url:
			self._generated_github_repo_url = self._generate_github_repo_url()

		return self._generated_github_repo_url

	def __init__(self, epub_root_directory: str):
		if not os.path.isdir(epub_root_directory):
			raise se.InvalidSeEbookException("Not a directory: {}".format(epub_root_directory))

		if not os.path.isfile(os.path.join(epub_root_directory, "src", "epub", "content.opf")):
			raise se.InvalidSeEbookException("Not a Standard Ebooks source directory: {}".format(epub_root_directory))

		self.directory = os.path.abspath(epub_root_directory)

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
			self._metadata_xhtml = file.read()

	@staticmethod
	def _get_malformed_urls(xhtml: str) -> list:
		"""
		Helper function used in self.lint()
		Get a list of URLs in the epub that do not match SE standards.

		INPUTS
		xhtml: A string of XHTML to check

		OUTPUTS
		A list of strings representing any malformed URLs in the XHTML string
		"""

		messages = []

		# Check for non-https URLs
		if "http://www.gutenberg.org" in xhtml:
			messages.append(LintMessage("Non-https gutenberg.org URL.", se.MESSAGE_TYPE_ERROR))

		if "http://www.pgdp.net" in xhtml:
			messages.append(LintMessage("Non-https pgdp.net URL.", se.MESSAGE_TYPE_ERROR))

		if "http://catalog.hathitrust.org" in xhtml:
			messages.append(LintMessage("Non-https hathitrust.org URL.", se.MESSAGE_TYPE_ERROR))

		if "http://archive.org" in xhtml:
			messages.append(LintMessage("Non-https archive.org URL.", se.MESSAGE_TYPE_ERROR))

		if "www.archive.org" in xhtml:
			messages.append(LintMessage("archive.org URL should not have leading www.", se.MESSAGE_TYPE_ERROR))

		if "http://en.wikipedia.org" in xhtml:
			messages.append(LintMessage("Non-https en.wikipedia.org URL.", se.MESSAGE_TYPE_ERROR))

		# Check for malformed canonical URLs
		if regex.search(r"books\.google\.com/books\?id=.+?[&#]", xhtml):
			messages.append(LintMessage("Non-canonical Google Books URL. Google Books URLs must look exactly like https://books.google.com/books?id=<BOOK-ID>"))

		if "babel.hathitrust.org" in xhtml:
			messages.append(LintMessage("Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like https://catalog.hathitrust.org/Record/<BOOK-ID>"))

		if ".gutenberg.org/files/" in xhtml:
			messages.append(LintMessage("Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like https://www.gutenberg.org/ebooks/<BOOK-ID>"))

		if "archive.org/stream" in xhtml:
			messages.append(LintMessage("Non-canonical archive.org URL. Internet Archive URLs must look exactly like https://archive.org/details/<BOOK-ID>"))

		return messages

	def _get_unused_selectors(self) -> set:
		"""
		Helper function used in self.lint(); merge directly into lint()?
		Get a list of CSS selectors that do not actually select HTML in the epub.

		INPUTS
		None

		OUTPUTS
		A list of strings representing CSS selectors that do not actually select HTML in the epub.
		"""

		try:
			with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), encoding="utf-8") as file:
				css = file.read()
		except Exception:
			raise FileNotFoundError("Couldn't open {}".format(os.path.join(self.directory, "src", "epub", "css", "local.css")))

		# Remove @supports directives, as the parser can't handle them
		css = regex.sub(r"^@supports\(.+?\){(.+?)}\s*}", "\\1}", css, flags=regex.MULTILINE | regex.DOTALL)

		# Remove actual content of css selectors
		css = regex.sub(r"{[^}]+}", "", css)

		# Remove trailing commas
		css = regex.sub(r",", "", css)

		# Remove comments
		css = regex.sub(r"/\*.+?\*/", "", css, flags=regex.DOTALL)

		# Remove @ defines
		css = regex.sub(r"^@.+", "", css, flags=regex.MULTILINE)

		# Construct a dictionary of selectors
		selectors = set([line for line in css.splitlines() if line != ""])
		unused_selectors = set(selectors)

		# Get a list of .xhtml files to search
		filenames = glob.glob(os.path.join(self.directory, "src", "epub", "text") + os.sep + "*.xhtml")

		# Now iterate over each CSS selector and see if it's used in any of the files we found
		for selector in selectors:
			try:
				sel = lxml.cssselect.CSSSelector(selector, translator="html", namespaces=se.XHTML_NAMESPACES)
			except lxml.cssselect.ExpressionError:
				# This gets thrown if we use pseudo-elements, which lxml doesn't support
				unused_selectors.remove(selector)
				continue

			for filename in filenames:
				if not filename.endswith("titlepage.xhtml") and not filename.endswith("imprint.xhtml") and not filename.endswith("uncopyright.xhtml"):
					# We have to remove the default namespace declaration from our document, otherwise
					# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
					with open(filename, "r") as file:
						xhtml = file.read().replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")

					try:
						tree = etree.fromstring(str.encode(xhtml))
					except Exception:
						se.print_error("Couldn't parse XHTML in file: {}".format(filename))
						exit(1)

					if tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
						unused_selectors.remove(selector)
						break

		return unused_selectors

	@staticmethod
	def _new_bs4_tag(section: Tag, output_soup: BeautifulSoup) -> Tag:
		"""
		Helper function used in self.recompose()
		Create a new BS4 tag given the current section.

		INPUTS
		section: A BS4 tag
		output_soup: A BS4 object representing the entire soup

		OUTPUTS
		A new BS4 tag.
		"""

		tag = output_soup.new_tag(section.name)
		for name, value in section.attrs.items():
			tag.attrs[name] = value

		return tag

	def _recompose_xhtml(self, section: Tag, output_soup: BeautifulSoup) -> None:
		"""
		Helper function used in self.recompose()
		Recursive function for recomposing a series of XHTML files into a single XHTML file.

		INPUTS
		section: A BS4 tag to inspect
		output_soup: A BS4 object representing the entire soup

		OUTPUTS
		None
		"""

		# Quick sanity check before we begin
		if "id" not in section.attrs or (section.parent.name.lower() != "body" and "id" not in section.parent.attrs):
			raise se.InvalidXhtmlException("Section without ID attribute")

		# Try to find our parent tag in the output, by ID.
		# If it's not in the output, then append it to the tag's closest parent by ID (or <body>), then iterate over its children and do the same.
		existing_section = output_soup.select("#" + section["id"])
		if not existing_section:
			if section.parent.name.lower() == "body":
				output_soup.body.append(self._new_bs4_tag(section, output_soup))
			else:
				output_soup.select("#" + section.parent["id"])[0].append(self._new_bs4_tag(section, output_soup))

			existing_section = output_soup.select("#" + section["id"])

		for child in section.children:
			if not isinstance(child, str):
				tag_name = child.name.lower()
				if tag_name == "section" or tag_name == "article":
					self._recompose_xhtml(child, output_soup)
				else:
					existing_section[0].append(child)

	def _generate_github_repo_url(self) -> str:
		"""
		Generate a GitHub repository URL based on the *generated* SE identifier,
		*not* the SE identifier in the metadata file.

		INPUTS
		None

		OUTPUTS
		A string representing the GitHub repository URL.
		"""

		return "https://github.com/standardebooks/" + self.generated_identifier.replace("url:https://standardebooks.org/ebooks/", "").replace("/", "_")

	def _generate_identifier(self) -> str:
		"""
		Generate an SE identifer based on the metadata in content.opf

		To access this value, use the property self.generated_identifier.

		INPUTS
		None

		OUTPUTS
		A string representing the SE identifier.
		"""
		if self._metadata_tree is None:
			self._metadata_tree = se.easy_xml.EasyXmlTree(self._metadata_xhtml)

		# Add authors
		identifier = "url:https://standardebooks.org/ebooks/"
		authors = []
		for author in self._metadata_tree.xpath("//dc:creator"):
			authors.append(author.inner_html())
			identifier += se.formatting.make_url_safe(author.inner_html()) + "_"

		identifier = identifier.strip("_") + "/"

		# Add title
		for title in self._metadata_tree.xpath("//dc:title[@id=\"title\"]"):
			identifier += se.formatting.make_url_safe(title.inner_html()) + "/"

		# For contributors, we add both translators and illustrators.
		# However, we may not include specific translators or illustrators in certain cases, namely
		# if *some* contributors have a `display-seq` property, and others do not.
		# According to the epub spec, if that is the case, we should only add those that *do* have the attribute.
		# By SE convention, any contributor with `display-seq == 0` will be excluded from the identifier string.
		translators = []
		illustrators = []
		translators_have_display_seq = False
		illustrators_have_display_seq = False
		for role in self._metadata_tree.xpath("//opf:meta[@property=\"role\"]"):
			contributor_id = role.attribute("refines").lstrip("#")
			contributor_element = self._metadata_tree.xpath("//dc:contributor[@id=\"" + contributor_id + "\"]")
			if contributor_element:
				contributor = {"name": contributor_element[0].inner_html(), "include": True, "display_seq": None}
				display_seq = self._metadata_tree.xpath("//opf:meta[@property=\"display-seq\"][@refines=\"#" + contributor_id + "\"]")

				if display_seq and int(display_seq[0].inner_html()) == 0:
					contributor["include"] = False
					display_seq = None

				if role.inner_html() == "trl":
					if display_seq:
						contributor["display_seq"] = display_seq[0]
						translators_have_display_seq = True

					translators.append(contributor)

				if role.inner_html() == "ill":
					if display_seq:
						contributor["display_seq"] = display_seq[0]
						illustrators_have_display_seq = True

					illustrators.append(contributor)

		for translator in translators:
			if (not translators_have_display_seq and translator["include"]) or translator["display_seq"]:
				identifier += se.formatting.make_url_safe(translator["name"]) + "_"

		if translators:
			identifier = identifier.strip("_") + "/"

		for illustrator in illustrators:
			if (not illustrators_have_display_seq and illustrator["include"]) or illustrator["display_seq"]:
				identifier += se.formatting.make_url_safe(illustrator["name"]) + "_"

		identifier = identifier.strip("_/")

		return identifier

	def recompose(self) -> str:
		"""
		Iterate over the XHTML files in this epub and "recompose" them into a single HTML5 string representing this ebook.

		INPUTS
		None

		OUTPUTS
		A string of HTML5 representing the entire recomposed ebook.
		"""

		# Get the ordered list of spine items
		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r", encoding="utf-8") as file:
			metadata_soup = BeautifulSoup(file.read(), "lxml")

		# Get some header data: title, core and local css
		title = html.escape(metadata_soup.find("dc:title").contents[0])
		css = ""
		with open(os.path.join(self.directory, "src", "epub", "css", "core.css"), "r", encoding="utf-8") as file:
			css = regex.sub(r"@.+?;", "", file.read()).strip()

		with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), "r", encoding="utf-8") as file:
			css = css + "\n\n\n/* local.css */" + regex.sub(r"@.+?;", "", file.read())
			css = "\t\t\t".join(css.splitlines(True))

		output_xhtml = "<?xml version=\"1.0\" encoding=\"utf-8\"?><html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" epub:prefix=\"z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0\"><head><meta charset=\"utf-8\"/><title>" + title + "</title><style/></head><body></body></html>"
		output_soup = BeautifulSoup(output_xhtml, "lxml")

		# Iterate over spine items in order and recompose them into our output
		for element in metadata_soup.select("spine itemref"):
			filename = metadata_soup.select("item#" + element["idref"])[0]["href"]

			with open(os.path.join(self.directory, "src", "epub", filename), "r", encoding="utf-8") as file:
				xhtml_soup = BeautifulSoup(file.read(), "lxml")

				for child in xhtml_soup.select("body > *"):
					self._recompose_xhtml(child, output_soup)

		# Add the ToC after the titlepage
		with open(os.path.join(self.directory, "src", "epub", "toc.xhtml"), "r", encoding="utf-8") as file:
			toc_soup = BeautifulSoup(file.read(), "lxml")
			output_soup.select("#titlepage")[0].insert_after(toc_soup.find("nav"))

		# Get the output XHTML as a string
		output_xhtml = str(output_soup)
		output_xhtml = regex.sub(r"\"(\.\./)?text/(.+?)\.xhtml\"", "\"#\\2\"", output_xhtml)
		output_xhtml = regex.sub(r"\"(\.\./)?text/.+?\.xhtml#(.+?)\"", "\"#\\2\"", output_xhtml)

		# Replace SVG images hrefs with inline SVG
		for match in regex.findall(r"src=\"../images/(.+?)\.svg\"", output_xhtml):
			with open(os.path.join(self.directory, "src", "epub", "images", match + ".svg")) as file:
				svg = file.read()

				# Remove XML declaration
				svg = regex.sub(r"<\?xml.+?\?>", "", svg)

				output_xhtml = regex.sub(r"<img.+?src=\"\.\./images/{}\.svg\".*?/>".format(match), svg, output_xhtml)

		with tempfile.NamedTemporaryFile(mode="w+", delete=False) as file:
			file.write(output_xhtml)
			file_name = file.name
			file_name_xhtml = file_name + ".xhtml"

		os.rename(file_name, file_name_xhtml)

		# All done, clean the output
		se.formatting.format_xhtml_file(file_name_xhtml, False, file_name_xhtml.endswith("content.opf"), file_name_xhtml.endswith("endnotes.xhtml"))

		with open(file_name_xhtml) as file:
			xhtml = file.read()

			# Remove xml declaration and re-add the doctype
			xhtml = regex.sub(r"<\?xml.+?\?>", "<!doctype html>", xhtml)
			xhtml = regex.sub(r" epub:prefix=\".+?\"", "", xhtml)

			# Insert our CSS. We do this after `clean` because `clean` will escape > in the CSS
			xhtml = regex.sub(r"<style/>", "<style>\n\t\t\t" + css + "\t\t</style>", xhtml)

			# Make some replacements for HTML5 compatibility
			xhtml = xhtml.replace("epub:type", "data-epub-type")
			xhtml = xhtml.replace("epub|type", "data-epub-type")
			xhtml = xhtml.replace("xml:lang", "lang")
			xhtml = xhtml.replace("<html", "<html lang=\"{}\"".format(metadata_soup.find("dc:language").string))
			xhtml = regex.sub(" xmlns.+?=\".+?\"", "", xhtml)

		os.remove(file_name_xhtml)

		return xhtml

	def generate_titlepage_svg(self) -> None:
		"""
		Generate a distributable titlepage SVG in ./src/epub/images/ based on the titlepage file in ./images/

		INPUTS
		None

		OUTPUTS
		None.
		"""

		inkscape_path = shutil.which("inkscape")

		if inkscape_path is None:
			raise se.MissingDependencyException("Couldn’t locate Inkscape. Is it installed?")

		source_images_directory = os.path.join(self.directory, "images")
		source_titlepage_svg_filename = os.path.join(source_images_directory, "titlepage.svg")
		dest_images_directory = os.path.join(self.directory, "src", "epub", "images")
		dest_titlepage_svg_filename = os.path.join(dest_images_directory, "titlepage.svg")

		if os.path.isfile(source_titlepage_svg_filename):
			# Convert text to paths
			# inkscape adds a ton of crap to the SVG and we clean that crap a little later
			subprocess.run([inkscape_path, source_titlepage_svg_filename, "--without-gui", "--export-text-to-path", "--export-plain-svg", dest_titlepage_svg_filename])

			se.images.format_inkscape_svg(dest_titlepage_svg_filename)

			# For the titlepage we want to remove all styles, since they are not used anymore
			with open(dest_titlepage_svg_filename, "r+", encoding="utf-8") as file:
				svg = regex.sub(r"<style.+?</style>[\n\t]+", "", file.read(), flags=regex.DOTALL)

				file.seek(0)
				file.write(svg)
				file.truncate()

	def generate_cover_svg(self) -> None:
		"""
		Generate a distributable cover SVG in ./src/epub/images/ based on the cover file in ./images/

		INPUTS
		None

		OUTPUTS
		None.
		"""

		inkscape_path = shutil.which("inkscape")

		if inkscape_path is None:
			raise se.MissingDependencyException("Couldn’t locate Inkscape. Is it installed?")

		source_images_directory = os.path.join(self.directory, "images")
		source_cover_jpg_filename = os.path.join(source_images_directory, "cover.jpg")
		source_cover_svg_filename = os.path.join(source_images_directory, "cover.svg")
		dest_images_directory = os.path.join(self.directory, "src", "epub", "images")
		dest_cover_svg_filename = os.path.join(dest_images_directory, "cover.svg")

		# Create output directory if it doesn't exist
		try:
			os.makedirs(dest_images_directory)
		except OSError as ex:
			if ex.errno != errno.EEXIST:
				raise ex

		# Remove useless metadata from cover source files
		for root, _, filenames in os.walk(source_images_directory):
			for filename in fnmatch.filter(filenames, "cover.source.*"):
				se.images.remove_image_metadata(os.path.join(root, filename))

		if os.path.isfile(source_cover_jpg_filename):
			se.images.remove_image_metadata(source_cover_jpg_filename)

			if os.path.isfile(source_cover_svg_filename):
				# base64 encode cover.jpg
				with open(source_cover_jpg_filename, "rb") as file:
					source_cover_jpg_base64 = base64.b64encode(file.read()).decode()

				# Convert text to paths
				# Inkscape adds a ton of crap to the SVG and we clean that crap a little later
				subprocess.run([inkscape_path, source_cover_svg_filename, "--without-gui", "--export-text-to-path", "--export-plain-svg", dest_cover_svg_filename])

				# Embed cover.jpg
				with open(dest_cover_svg_filename, "r+", encoding="utf-8") as file:
					svg = regex.sub(r"xlink:href=\".*?cover\.jpg", "xlink:href=\"data:image/jpeg;base64," + source_cover_jpg_base64, file.read(), flags=regex.DOTALL)

					file.seek(0)
					file.write(svg)
					file.truncate()

				se.images.format_inkscape_svg(dest_cover_svg_filename)

				# For the cover we want to keep the path.title-box style, and add an additional
				# style to color our new paths white
				with open(dest_cover_svg_filename, "r+", encoding="utf-8") as file:
					svg = regex.sub(r"<style.+?</style>", "<style type=\"text/css\">\n\t\tpath{\n\t\t\tfill: #fff;\n\t\t}\n\n\t\t.title-box{\n\t\t\tfill: #000;\n\t\t\tfill-opacity: .75;\n\t\t}\n\t</style>", file.read(), flags=regex.DOTALL)

					file.seek(0)
					file.write(svg)
					file.truncate()

	def reorder_endnotes(self, target_endnote_number: int, step: int = 1) -> None:
		"""
		Reorder endnotes starting at target_endnote_number.

		INPUTS:
		target_endnote_number: The endnote to start reordering at
		step: 1 to increment or -1 to decrement

		OUTPUTS:
		None.
		"""

		increment = step == 1
		endnote_count = 0
		source_directory = os.path.join(self.directory, "src")

		try:
			endnotes_filename = os.path.join(source_directory, "epub", "text", "endnotes.xhtml")
			with open(endnotes_filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()
				soup = BeautifulSoup(xhtml, "lxml")

				endnote_count = len(soup.select("li[id^=note-]"))

				if increment:
					note_range = range(endnote_count, target_endnote_number - 1, -1)
				else:
					note_range = range(target_endnote_number, endnote_count + 1, 1)

				for endnote_number in note_range:
					xhtml = xhtml.replace("id=\"note-{}\"".format(endnote_number), "id=\"note-{}\"".format(endnote_number + step), 1)
					xhtml = xhtml.replace("#noteref-{}\"".format(endnote_number), "#noteref-{}\"".format(endnote_number + step), 1)

				# There may be some links within the notes that refer to other endnotes.
				# These potentially need incrementing / decrementing too. This code assumes
				# a link that looks something like <a href="#note-1">note 1</a>.
				endnote_links = regex.findall(r"href=\"#note-(\d+)\"(.*?) (\d+)</a>", xhtml)
				for link in endnote_links:
					link_number = int(link[0])
					if (link_number < target_endnote_number and increment) or (link_number > target_endnote_number and not increment):
						continue
					xhtml = xhtml.replace("href=\"#note-{0}\"{1} {0}</a>".format(link[0], link[1]), "href=\"#note-{0}\"{1} {0}</a>".format(link_number + step, link[1]))

				file.seek(0)
				file.write(xhtml)
				file.truncate()

		except Exception:
			raise se.InvalidSeEbookException("Couldn’t open endnotes file: {}".format(endnotes_filename))

		with concurrent.futures.ProcessPoolExecutor() as executor:
			for root, _, filenames in os.walk(source_directory):
				for filename in fnmatch.filter(filenames, "*.xhtml"):
					# Skip endnotes.xhtml since we already processed it
					if filename == "endnotes.xhtml":
						continue

					executor.submit(_process_endnotes_in_file, filename, root, note_range, step)

	def update_revision(self) -> None:
		"""
		Update the revision number and updated date in the metadata and colophon.

		INPUTS
		None

		OUTPUTS
		None.
		"""

		timestamp = datetime.datetime.utcnow()
		iso_timestamp = regex.sub(r"\.[0-9]+$", "", timestamp.isoformat()) + "Z"

		# Construct the friendly timestamp
		friendly_timestamp = "{0:%B %e, %Y, %l:%M <abbr class=\"time eoc\">%p</abbr>}".format(timestamp)
		friendly_timestamp = regex.sub(r"\s+", " ", friendly_timestamp).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

		# Calculate the new revision number
		revision = int(regex.search(r"<meta property=\"se:revision-number\">([0-9]+)</meta>", self._metadata_xhtml).group(1))
		revision = revision + 1

		# If this is an initial release, set the release date in content.opf
		if revision == 1:
			self._metadata_xhtml = regex.sub(r"<dc:date>[^<]+?</dc:date>", "<dc:date>{}</dc:date>".format(iso_timestamp), self._metadata_xhtml)

		# Set modified date and revision number in content.opf
		self._metadata_xhtml = regex.sub(r"<meta property=\"dcterms:modified\">[^<]+?</meta>", "<meta property=\"dcterms:modified\">{}</meta>".format(iso_timestamp), self._metadata_xhtml)
		self._metadata_xhtml = regex.sub(r"<meta property=\"se:revision-number\">[^<]+?</meta>", "<meta property=\"se:revision-number\">{}</meta>".format(revision), self._metadata_xhtml)

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "w", encoding="utf-8") as file:
			file.seek(0)
			file.write(self._metadata_xhtml)
			file.truncate()

		# Update the colophon with release info
		with open(os.path.join(self.directory, "src", "epub", "text", "colophon.xhtml"), "r+", encoding="utf-8") as file:
			xhtml = file.read()

			# Are we moving from the first edition to the nth edition?
			if revision == 1:
				xhtml = regex.sub(r"<span class=\"release-date\">.+?</span>", "<span class=\"release-date\">{}</span>".format(friendly_timestamp), xhtml)
			else:
				ordinal = se.formatting.get_ordinal(revision)
				if "<p>This is the first edition of this ebook.<br/>" in xhtml:
					xhtml = xhtml.replace("This edition was released on<br/>", "The first edition was released on<br/>")
					xhtml = xhtml.replace("<p>This is the first edition of this ebook.<br/>", "<p>This is the <span class=\"revision-number\">{}</span> edition of this ebook.<br/>\n\t\t\tThis edition was released on<br/>\n\t\t\t<span class=\"revision-date\">{}</span><br/>".format(ordinal, friendly_timestamp))
				else:
					xhtml = regex.sub(r"<span class=\"revision-date\">.+?</span>", "<span class=\"revision-date\">{}</span>".format(friendly_timestamp), xhtml)
					xhtml = regex.sub(r"<span class=\"revision-number\">[^<]+?</span>", "<span class=\"revision-number\">{}</span>".format(ordinal), xhtml)

			file.seek(0)
			file.write(xhtml)
			file.truncate()

	def update_flesch_reading_ease(self) -> None:
		"""
		Calculate a new reading ease for this ebook and update the metadata file.
		Ignores SE boilerplate files like the imprint.

		INPUTS
		None

		OUTPUTS
		None.
		"""
		text = ""

		for filename in se.get_target_filenames([self.directory], (".xhtml"), True):
			with open(filename, "r", encoding="utf-8") as file:
				text += " " + file.read()

		self._metadata_xhtml = regex.sub(r"<meta property=\"se:reading-ease\.flesch\">[^<]*</meta>", "<meta property=\"se:reading-ease.flesch\">{}</meta>".format(se.formatting.get_flesch_reading_ease(text)), self._metadata_xhtml)

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "w", encoding="utf-8") as file:
			file.seek(0)
			file.write(self._metadata_xhtml)
			file.truncate()

	def update_word_count(self) -> None:
		"""
		Calculate a new word count for this ebook and update the metadata file.
		Ignores SE boilerplate files like the imprint, as well as any endnotes.

		INPUTS
		None

		OUTPUTS
		None.
		"""
		word_count = 0

		for filename in se.get_target_filenames([self.directory], (".xhtml"), True):
			if filename.endswith("endnotes.xhtml"):
				continue

			with open(filename, "r", encoding="utf-8") as file:
				word_count += se.formatting.get_word_count(file.read())

		self._metadata_xhtml = regex.sub(r"<meta property=\"se:word-count\">[^<]*</meta>", "<meta property=\"se:word-count\">{}</meta>".format(word_count), self._metadata_xhtml)

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
			file.seek(0)
			file.write(self._metadata_xhtml)
			file.truncate()

	def generate_manifest(self) -> str:
		"""
		Return the <manifest> element for this ebook as an XML string.

		INPUTS
		None

		OUTPUTS
		An XML fragment string representing the manifest.
		"""

		manifest = []

		# Add CSS
		for _, _, filenames in os.walk(os.path.join(self.directory, "src", "epub", "css")):
			for filename in filenames:
				manifest.append("<item href=\"css/{}\" id=\"{}\" media-type=\"text/css\"/>".format(filename, filename))

		# Add images
		for _, _, filenames in os.walk(os.path.join(self.directory, "src", "epub", "images")):
			for filename in filenames:
				media_type = "image/jpeg"
				properties = ""

				if filename.endswith(".svg"):
					media_type = "image/svg+xml"

				if filename.endswith(".png"):
					media_type = "image/png"

				if filename == "cover.svg":
					properties = " properties=\"cover-image\""

				manifest.append("<item href=\"images/{}\" id=\"{}\" media-type=\"{}\"{}/>".format(filename, filename, media_type, properties))

		# Add XHTML files
		for root, _, filenames in os.walk(os.path.join(self.directory, "src", "epub", "text")):
			for filename in filenames:
				# Skip dotfiles, because .DS_Store might be binary and then we'd crash when we try to read it below
				if filename.startswith("."):
					continue

				properties = "properties=\""

				with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
					file_contents = file.read()
					if "http://www.w3.org/1998/Math/MathML" in file_contents:
						properties += "mathml "
					if ".svg" in file_contents:
						properties += "svg "

				properties = " " + properties.strip() + "\""

				if properties == " properties=\"\"":
					properties = ""

				manifest.append("<item href=\"text/{}\" id=\"{}\" media-type=\"application/xhtml+xml\"{}/>".format(filename, filename, properties))

		manifest = se.natural_sort(manifest)

		manifest_xhtml = "<manifest>\n\t<item href=\"toc.xhtml\" id=\"toc.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>\n"

		for line in manifest:
			manifest_xhtml = manifest_xhtml + "\t" + line + "\n"

		manifest_xhtml = manifest_xhtml + "</manifest>"

		return manifest_xhtml

	def generate_spine(self) -> str:
		"""
		Return the <spine> element of this ebook as an XML string, with a best guess as to the correct order. Manual review is required.

		INPUTS
		None

		OUTPUTS
		An XML fragment string representing the spine.
		"""

		excluded_files = se.IGNORED_FILENAMES + ["dedication.xhtml", "introduction.xhtml", "foreword.xhtml", "preface.xhtml", "epigraph.xhtml", "endnotes.xhtml"]
		spine = ["<itemref idref=\"titlepage.xhtml\"/>", "<itemref idref=\"imprint.xhtml\"/>"]

		filenames = se.natural_sort(os.listdir(os.path.join(self.directory, "src", "epub", "text")))

		if "dedication.xhtml" in filenames:
			spine.append("<itemref idref=\"dedication.xhtml\"/>")

		if "introduction.xhtml" in filenames:
			spine.append("<itemref idref=\"introduction.xhtml\"/>")

		if "foreword.xhtml" in filenames:
			spine.append("<itemref idref=\"foreword.xhtml\"/>")

		if "preface.xhtml" in filenames:
			spine.append("<itemref idref=\"preface.xhtml\"/>")

		if "epigraph.xhtml" in filenames:
			spine.append("<itemref idref=\"epigraph.xhtml\"/>")

		if "halftitle.xhtml" in filenames:
			spine.append("<itemref idref=\"halftitle.xhtml\"/>")

		for filename in filenames:
			if filename not in excluded_files:
				spine.append("<itemref idref=\"{}\"/>".format(filename))

		if "endnotes.xhtml" in filenames:
			spine.append("<itemref idref=\"endnotes.xhtml\"/>")

		if "loi.xhtml" in filenames:
			spine.append("<itemref idref=\"loi.xhtml\"/>")

		spine.append("<itemref idref=\"colophon.xhtml\"/>")
		spine.append("<itemref idref=\"uncopyright.xhtml\"/>")

		spine_xhtml = "<spine>\n"
		for line in spine:
			spine_xhtml = spine_xhtml + "\t" + line + "\n"

		spine_xhtml = spine_xhtml + "</spine>"

		return spine_xhtml

	def lint(self) -> list:
		"""
		Check this ebook for some common SE style errors.

		INPUTS
		None

		OUTPUTS
		A list of LintMessage objects.
		"""

		messages = []
		license_file_path = resource_filename("se", os.path.join("data", "templates", "LICENSE.md"))
		gitignore_file_path = resource_filename("se", os.path.join("data", "templates", "gitignore"))
		core_css_file_path = resource_filename("se", os.path.join("data", "templates", "core.css"))
		logo_svg_file_path = resource_filename("se", os.path.join("data", "templates", "logo.svg"))
		uncopyright_file_path = resource_filename("se", os.path.join("data", "templates", "uncopyright.xhtml"))
		has_halftitle = False
		has_frontmatter = False
		has_cover_source = False
		cover_svg_title = ""
		titlepage_svg_title = ""
		xhtml_css_classes = {}
		headings = []

		# Get the ebook language, for later use
		language = regex.search(r"<dc:language>([^>]+?)</dc:language>", self._metadata_xhtml).group(1)

		# Check local.css for various items, for later use
		abbr_elements = []
		css = ""
		with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), "r", encoding="utf-8") as file:
			css = file.read()

			local_css_has_subtitle_style = "span[epub|type~=\"subtitle\"]" in css

			abbr_styles = regex.findall(r"abbr\.[a-z]+", css)

			matches = regex.findall(r"^h[0-6]\s*,?{?", css, flags=regex.MULTILINE)
			if matches:
				messages.append(LintMessage("Do not directly select h[0-6] elements, as they are used in template files; use more specific selectors.", se.MESSAGE_TYPE_ERROR, "local.css"))

		# Check for presence of ./dist/ folder
		if os.path.exists(os.path.join(self.directory, "dist")):
			messages.append(LintMessage("Illegal ./dist/ folder. Do not commit compiled versions of the source.", se.MESSAGE_TYPE_ERROR, "./dist/"))

		# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
		if regex.search(r"#description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", self._metadata_xhtml.replace("\"&gt;", "").replace("=\"", "")) is not None:
			messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata long description", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for malformed long description HTML
		long_description = regex.findall(r"<meta id=\"long-description\".+?>(.+?)</meta>", self._metadata_xhtml, flags=regex.DOTALL)
		if long_description:
			long_description = "<?xml version=\"1.0\"?><html xmlns=\"http://www.w3.org/1999/xhtml\">" + html.unescape(long_description[0]) + "</html>"
			try:
				etree.parse(io.StringIO(long_description))
			except lxml.etree.XMLSyntaxError as ex:
				messages.append(LintMessage("Metadata long description is not valid HTML. LXML says: " + str(ex), se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for double spacing
		regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
		matches = regex.findall(regex_string, self._metadata_xhtml)
		if matches:
			messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		if regex.search(r"<dc:description id=\"description\">[^<]+?(['\"]|\-\-)[^<]+?</dc:description>", self._metadata_xhtml) is not None:
			messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata dc:description.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
		matches = regex.findall(r"[a-zA-Z][”][,.]", self._metadata_xhtml)
		if matches:
			messages.append(LintMessage("Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, "content.opf"))

		# Make sure long-description is escaped HTML
		if "<meta id=\"long-description\" property=\"se:long-description\" refines=\"#description\">\n\t\t\t&lt;p&gt;" not in self._metadata_xhtml:
			messages.append(LintMessage("Long description must be escaped HTML.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for HTML entities in long-description, but allow &amp;amp;
		if regex.search(r"&amp;[a-z]+?;", self._metadata_xhtml.replace("&amp;amp;", "")):
			messages.append(LintMessage("HTML entites detected in metadata. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal em-dashes in <dc:subject>
		if regex.search(r"<dc:subject id=\"[^\"]+?\">[^<]+?—[^<]+?</dc:subject>", self._metadata_xhtml) is not None:
			messages.append(LintMessage("Illegal em-dash detected in dc:subject; use --", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for empty production notes
		if "<meta property=\"se:production-notes\">Any special notes about the production of this ebook for future editors/producers? Remove this element if not.</meta>" in self._metadata_xhtml:
			messages.append(LintMessage("Empty production-notes element in metadata.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal VCS URLs
		matches = regex.findall(r"<meta property=\"se:url\.vcs\.github\">([^<]+?)</meta>", self._metadata_xhtml)
		if matches:
			for match in matches:
				if not match.startswith("https://github.com/standardebooks/"):
					messages.append(LintMessage("Illegal se:url.vcs.github. VCS URLs must begin with https://github.com/standardebooks/: {}".format(match), se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for HathiTrust scan URLs instead of actual record URLs
		if "babel.hathitrust.org" in self._metadata_xhtml or "hdl.handle.net" in self._metadata_xhtml:
			messages.append(LintMessage("Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: https://catalog.hathitrust.org/Record/<RECORD-ID>", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal se:subject tags
		matches = regex.findall(r"<meta property=\"se:subject\">([^<]+?)</meta>", self._metadata_xhtml)
		if matches:
			for match in matches:
				if match not in se.SE_GENRES:
					messages.append(LintMessage("Illegal se:subject: {}".format(match), se.MESSAGE_TYPE_ERROR, "content.opf"))
		else:
			messages.append(LintMessage("No se:subject <meta> tag found.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for CDATA tags
		if "<![CDATA[" in self._metadata_xhtml:
			messages.append(LintMessage("<![CDATA[ detected. Run `clean` to canonicalize <![CDATA[ sections.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check that our provided identifier matches the generated identifier
		identifier = regex.sub(r"<.+?>", "", regex.findall(r"<dc:identifier id=\"uid\">.+?</dc:identifier>", self._metadata_xhtml)[0])
		if identifier != self.generated_identifier:
			messages.append(LintMessage("<dc:identifier> does not match expected: {}".format(self.generated_identifier), se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check that the GitHub repo URL is as expected
		if self.generated_github_repo_url not in self._metadata_xhtml:
			messages.append(LintMessage("GitHub repo URL does not match expected: {}".format(self.generated_github_repo_url), se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check if se:name.person.full-name matches their titlepage name
		matches = regex.findall(r"<meta property=\"se:name\.person\.full-name\" refines=\"#([^\"]+?)\">([^<]*?)</meta>", self._metadata_xhtml)
		duplicate_names = []
		for match in matches:
			name_matches = regex.findall(r"<([a-z:]+)[^<]+?id=\"{}\"[^<]*?>([^<]*?)</\1>".format(match[0]), self._metadata_xhtml)
			for name_match in name_matches:
				if name_match[1] == match[1]:
					duplicate_names.append(name_match[1])

		if duplicate_names:
			messages.append(LintMessage("se:name.person.full-name property identical to regular name. If the two are identical the full name <meta> element must be removed.", se.MESSAGE_TYPE_ERROR, "content.opf"))
			for duplicate_name in duplicate_names:
				messages.append(LintMessage(duplicate_name, se.MESSAGE_TYPE_ERROR, "", True))

		# Check for malformed URLs
		for message in self._get_malformed_urls(self._metadata_xhtml):
			message.filename = "content.opf"
			messages.append(message)

		if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", self._metadata_xhtml):
			messages.append(LintMessage("id.loc.gov URL ending with illegal .html", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Does the manifest match the generated manifest?
		for manifest in regex.findall(r"<manifest>.*?</manifest>", self._metadata_xhtml, flags=regex.DOTALL):
			manifest = regex.sub(r"[\n\t]", "", manifest)
			expected_manifest = regex.sub(r"[\n\t]", "", self.generate_manifest())

			if manifest != expected_manifest:
				messages.append(LintMessage("<manifest> does not match expected structure.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Make sure some static files are unchanged
		try:
			if not filecmp.cmp(license_file_path, os.path.join(self.directory, "LICENSE.md")):
				messages.append(LintMessage("LICENSE.md does not match {}".format(license_file_path), se.MESSAGE_TYPE_ERROR, "LICENSE.md"))
		except Exception:
			messages.append(LintMessage("Missing ./LICENSE.md", se.MESSAGE_TYPE_ERROR, "LICENSE.md"))

		if not filecmp.cmp(core_css_file_path, os.path.join(self.directory, "src", "epub", "css", "core.css")):
			messages.append(LintMessage("core.css does not match {}".format(core_css_file_path), se.MESSAGE_TYPE_ERROR, "core.css"))

		if not filecmp.cmp(logo_svg_file_path, os.path.join(self.directory, "src", "epub", "images", "logo.svg")):
			messages.append(LintMessage("logo.svg does not match {}".format(logo_svg_file_path), se.MESSAGE_TYPE_ERROR, "logo.svg"))

		if not filecmp.cmp(uncopyright_file_path, os.path.join(self.directory, "src", "epub", "text", "uncopyright.xhtml")):
			messages.append(LintMessage("uncopyright.xhtml does not match {}".format(uncopyright_file_path), se.MESSAGE_TYPE_ERROR, "uncopyright.xhtml"))

		# Check for unused selectors
		unused_selectors = self._get_unused_selectors()
		if unused_selectors:
			messages.append(LintMessage("Unused CSS selectors:", se.MESSAGE_TYPE_ERROR, "local.css"))
			for selector in unused_selectors:
				messages.append(LintMessage(selector, se.MESSAGE_TYPE_ERROR, "", True))

		# Now iterate over individual files for some checks
		for root, _, filenames in os.walk(self.directory):
			for filename in sorted(filenames, key=se.natural_sort_key):
				if ".git/" in os.path.join(root, filename):
					continue

				if filename.startswith("cover.source."):
					has_cover_source = True

				if filename != "LICENSE.md" and regex.findall(r"[A-Z]", filename):
					messages.append(LintMessage("Illegal uppercase letter in filename", se.MESSAGE_TYPE_ERROR, filename))

				if "-0" in filename:
					messages.append(LintMessage("Illegal leading 0 in filename", se.MESSAGE_TYPE_ERROR, filename))

				if filename.endswith(tuple(se.BINARY_EXTENSIONS)) or filename.endswith("core.css"):
					continue

				if filename.startswith(".") or filename.startswith("README"):
					if filename == ".gitignore":
						# .gitignore is optional, because our standard gitignore ignores itself.
						# So if it's present, it must match our template.
						if not filecmp.cmp(gitignore_file_path, os.path.join(self.directory, ".gitignore")):
							messages.append(LintMessage(".gitignore does not match {}".format(gitignore_file_path), se.MESSAGE_TYPE_ERROR, ".gitignore"))
							continue
					else:
						messages.append(LintMessage("Illegal {} file detected in {}".format(filename, root), se.MESSAGE_TYPE_ERROR))
						continue

				with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
					try:
						file_contents = file.read()
					except UnicodeDecodeError:
						# This is more to help developers find weird files that might choke 'lint', hopefully unnecessary for end users
						messages.append(LintMessage("Problem decoding file as utf-8", se.MESSAGE_TYPE_ERROR, filename))
						continue

					if "http://standardebooks.org" in file_contents:
						messages.append(LintMessage("Non-HTTPS Standard Ebooks URL detected.", se.MESSAGE_TYPE_ERROR, filename))

					if "UTF-8" in file_contents:
						messages.append(LintMessage("String \"UTF-8\" must always be lowercase.", se.MESSAGE_TYPE_ERROR, filename))

					if filename == "halftitle.xhtml":
						has_halftitle = True

					if filename.endswith(".svg"):
						# Check for fill: #000 which should simply be removed
						matches = regex.findall(r"fill=\"\s*#000", file_contents) + regex.findall(r"style=\"[^\"]*?fill:\s*#000", file_contents)
						if matches:
							messages.append(LintMessage("Found illegal style=\"fill: #000\" or fill=\"#000\".", se.MESSAGE_TYPE_ERROR, filename))

						if os.sep + "src" + os.sep not in root:
							# Check that cover and titlepage images are in all caps
							if filename == "cover.svg":
								matches = regex.findall(r"<text[^>]+?>.*[a-z].*</text>", file_contents)
								if matches:
									messages.append(LintMessage("Lowercase letters in cover. Cover text must be all uppercase.", se.MESSAGE_TYPE_ERROR, filename))

								# Save for later comparison with titlepage
								matches = regex.findall(r"<title>(.*?)</title>", file_contents)
								for match in matches:
									cover_svg_title = match.replace("The cover for ", "")

							if filename == "titlepage.svg":
								matches = regex.findall(r"<text[^>]+?>(.*[a-z].*)</text>", html.unescape(file_contents))
								for match in matches:
									if match != "translated by" and match != "illustrated by" and match != "and":
										messages.append(LintMessage("Lowercase letters in titlepage. Titlepage text must be all uppercase except \"translated by\" and \"illustrated by\".", se.MESSAGE_TYPE_ERROR, filename))

								# For later comparison with cover
								matches = regex.findall(r"<title>(.*?)</title>", file_contents)
								for match in matches:
									titlepage_svg_title = match.replace("The titlepage for ", "")

					if filename.endswith(".css"):
						# Check CSS style

						# First remove @supports selectors and normalize indentation within them
						matches = regex.findall(r"^@supports\(.+?\){.+?}\s*}", file_contents, flags=regex.MULTILINE | regex.DOTALL)
						for match in matches:
							processed_match = regex.sub(r"^@supports\(.+?\){\s*(.+?)\s*}\s*}", "\\1", match.replace("\n\t", "\n") + "\n}", flags=regex.MULTILINE | regex.DOTALL)
							file_contents = file_contents.replace(match, processed_match)

						# Remove comments that are on their own line
						file_contents = regex.sub(r"^/\*.+?\*/\n", "", file_contents, flags=regex.MULTILINE | regex.DOTALL)

						# Check for unneeded white-space nowrap in abbr selectors
						matches = regex.findall(r"abbr.+?{[^}]*?white-space:\s*nowrap;[^}]*?}", css)
						if matches:
							messages.append(LintMessage("abbr selector does not need white-space: nowrap; as it inherits it from core.css.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# No empty CSS selectors
						matches = regex.findall(r"^.+\{\s*\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("Empty selector.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# No space before CSS opening braces
						matches = regex.findall(r".+\s\{", file_contents)
						if matches:
							messages.append(LintMessage("CSS opening braces must not be preceded by space.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# CSS closing braces on their own line
						matches = regex.findall(r"^\s*[^\s+]\s*.+\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("CSS closing braces must be on their own line.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# White space before CSS closing braces
						matches = regex.findall(r"^\s+\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("No white space before CSS closing braces.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Properties not indented with tabs
						matches = regex.findall(r"^[^\t@/].+:[^\{,]+?;$", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("CSS properties must be indented with exactly one tab.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Don't specify border color
						matches = regex.findall(r"(?:border|color).+?(?:#[a-f0-9]{0,6}|black|white|red)", file_contents, flags=regex.IGNORECASE)
						if matches:
							messages.append(LintMessage("Don't specify border colors, so that reading systems can adjust for night mode.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Blank space between selectors
						matches = regex.findall(r"\}\n[^\s]+", file_contents)
						if matches:
							messages.append(LintMessage("CSS selectors must have exactly one blank line between them.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Blank space between properties and values
						matches = regex.findall(r"\s+[a-z\-]+:[^ ]+?;", file_contents)
						if matches:
							messages.append(LintMessage("Exactly one space required between CSS properties and their values.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						matches = regex.findall(r"\}\n\s{2,}[^\s]+", file_contents)
						if matches:
							messages.append(LintMessage("CSS selectors must have exactly one blank line between them.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Properties indented with multiple tabs
						matches = regex.findall(r"^\t{2,}.+:[^\{,]+?;$", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("CSS properties must be indented with exactly one tab.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

					if filename.endswith(".xhtml"):
						for message in self._get_malformed_urls(file_contents):
							message.filename = filename
							messages.append(message)

						# Check if this is a frontmatter file
						if filename != "titlepage.xhtml" and filename != "imprint.xhtml" and filename != "toc.xhtml":
							matches = regex.findall(r"epub:type=\"[^\"]*?frontmatter[^\"]*?\"", file_contents)
							if matches:
								has_frontmatter = True

						# Add new CSS classes to global list
						if filename not in se.IGNORED_FILENAMES:
							matches = regex.findall(r"(?:class=\")[^\"]+?(?:\")", file_contents)
							for match in matches:
								for css_class in match.replace("class=", "").replace("\"", "").split():
									if css_class in xhtml_css_classes:
										xhtml_css_classes[css_class] += 1
									else:
										xhtml_css_classes[css_class] = 1

									#xhtml_css_classes = xhtml_css_classes + match.replace("class=", "").replace("\"", "").split()

						# Read file contents into a DOM for querying
						dom = BeautifulSoup(file_contents, "lxml")

						# Store all headings to check for ToC references later
						if filename != "toc.xhtml":
							matches = dom.select("h1,h2,h3,h4,h5,h6")
							for match in matches:

								# Remove any links to the endnotes
								endnote_ref = match.find("a", attrs={"epub:type": regex.compile("^.*noteref.*$")})
								if endnote_ref:
									endnote_ref.extract()

								# Decide whether to remove subheadings based on the following logic:
								# If the closest parent <section> is a part or division, then keep subtitle
								# Else, if the closest parent <section> is a halftitlepage, then discard subtitle
								# Else, if the first child of the heading is not z3998:roman, then also discard subtitle
								# Else, keep the subtitle.
								heading_subtitle = match.find(attrs={"epub:type": regex.compile("^.*subtitle.*$")})

								if heading_subtitle:
									parent_section = match.find_parents("section")

									# Sometimes we might not have a parent <section>, like in Keats' Poetry
									if not parent_section:
										parent_section = match.find_parents("body")

									closest_section_epub_type = parent_section[0].get("epub:type") or ""
									heading_first_child_epub_type = match.find("span", recursive=False).get("epub:type") or ""

									if regex.findall(r"^.*(part|division).*$", closest_section_epub_type):
										remove_subtitle = False
									elif regex.findall(r"^.*halftitlepage.*$", closest_section_epub_type):
										remove_subtitle = True
									elif not regex.findall(r"^.*z3998:roman.*$", heading_first_child_epub_type):
										remove_subtitle = True
									else:
										remove_subtitle = False

									if remove_subtitle:
										heading_subtitle.extract()

								normalized_text = " ".join(match.get_text().split())
								headings = headings + [(normalized_text, filename)]

						# Check for direct z3998:roman spans that should have their semantic pulled into the parent element
						matches = regex.findall(r"<([a-z0-9]+)[^>]*?>\s*(<span epub:type=\"z3998:roman\">[^<]+?</span>)\s*</\1>", file_contents, flags=regex.DOTALL)
						if matches:
							messages.append(LintMessage("If <span> exists only for the z3998:roman semantic, then z3998:roman should be pulled into parent tag instead.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match[1], se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for "Hathi Trust" instead of "HathiTrust"
						if "Hathi Trust" in file_contents:
							messages.append(LintMessage("\"Hathi Trust\" should be \"HathiTrust\"", se.MESSAGE_TYPE_ERROR, filename))

						# Check for uppercase letters in IDs or classes
						matches = dom.select("[id],[class]")
						for match in matches:
							if match.has_attr("id"):
								normalized_id = unicodedata.normalize("NFKD", match["id"])
								uppercase_matches = regex.findall(r"[A-Z]", normalized_id)
								for _ in uppercase_matches:
									messages.append(LintMessage("Uppercase ID attribute: {}. Attribute values must be all lowercase.".format(match["id"]), se.MESSAGE_TYPE_ERROR, filename))

								number_matches = regex.findall(r"^[0-9]", normalized_id)
								for _ in number_matches:
									messages.append(LintMessage("ID starting with a number is illegal XHTML: {}".format(match["id"]), se.MESSAGE_TYPE_ERROR, filename))

							if match.has_attr("class"):
								for css_class in match["class"]:
									uppercase_matches = regex.findall(r"[A-Z]", unicodedata.normalize("NFKD", css_class))
									for _ in uppercase_matches:
										messages.append(LintMessage("Uppercase class attribute: {}. Attribute values must be all lowercase.".format(css_class), se.MESSAGE_TYPE_ERROR, filename))

						matches = [x for x in dom.select("section") if not x.has_attr("id")]
						if matches:
							messages.append(LintMessage("<section> element without id attribute.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for numeric entities
						matches = regex.findall(r"&#[0-9]+?;", file_contents)
						if matches:
							messages.append(LintMessage("Illegal numeric entity (like &#913;) in file.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for double greater-than at the end of a tag
						matches = regex.findall(r"(>>|>&gt;)", file_contents)
						if matches:
							messages.append(LintMessage("Tags should end with a single >.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for nbsp before times
						matches = regex.findall(r"[0-9]+[^{}]<abbr class=\"time".format(se.NO_BREAK_SPACE), file_contents)
						if matches:
							messages.append(LintMessage("Required nbsp not found before <abbr class=\"time\">", se.MESSAGE_TYPE_WARNING, filename))

						# Check for low-hanging misquoted fruit
						matches = regex.findall(r"[A-Za-z]+[“‘]", file_contents)
						if matches:
							messages.append(LintMessage("Possible mis-curled quotation mark.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check that times have colons and not periods
						matches = regex.findall(r"[0-9]\.[0-9]+\s<abbr class=\"time", file_contents) + regex.findall(r"at [0-9]\.[0-9]+", file_contents)
						if matches:
							messages.append(LintMessage("Times must be separated by colons (:) not periods (.)", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for leading 0 in IDs
						matches = regex.findall(r"id=\"[^\"]+?\-0[0-9]+[^\"]*?\"", file_contents)
						if matches:
							messages.append(LintMessage("Illegal leading 0 in ID attribute", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for money not separated by commas
						matches = regex.findall(r"[£\$][0-9]{4,}", file_contents)
						if matches:
							messages.append(LintMessage("Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for trailing commas inside <i> tags at the close of dialog
						if ",</i>”" in file_contents:
							messages.append(LintMessage("Comma inside <i> tag before closing dialog. (Search for ,</i>”)", se.MESSAGE_TYPE_WARNING, filename))

						# Check for period following Roman numeral, which is an old-timey style we must fix
						# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
						matches = regex.findall(r"(?<!<p[^>]*?>)<span epub:type=\"z3998:roman\">[^<]+?</span>\.\s+[a-z]", file_contents)
						if matches:
							messages.append(LintMessage("Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for two em dashes in a row
						matches = regex.findall(r"—{}*—+".format(se.WORD_JOINER), file_contents)
						if matches:
							messages.append(LintMessage("Two or more em-dashes in a row detected. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for <abbr class="name"> that does not contain spaces
						matches = regex.findall(r"<abbr class=\"name\">[^<]*?[A-Z]\.[A-Z]\.[^<]*?</abbr>", file_contents)
						if matches:
							messages.append(LintMessage("Initials in <abbr class=\"name\"> not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for empty <h2> missing epub:type="title" attribute
						if "<h2>" in file_contents:
							messages.append(LintMessage("<h2> tag without epub:type=\"title\" attribute.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for a common typo
						if "z3998:nonfiction" in file_contents:
							messages.append(LintMessage("Typo: z3998:nonfiction should be z3998:non-fiction", se.MESSAGE_TYPE_ERROR, filename))

						# Check for empty <p> tags
						matches = regex.findall(r"<p>\s*</p>", file_contents)
						if "<p/>" in file_contents or matches:
							messages.append(LintMessage("Empty <p> tag. Use <hr/> for scene breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for single words that are in italics, but that have closing punctuation outside italics
						# Outer wrapping match is so that .findall returns the entire match and not the subgroup
						# The first regex also matches the first few characters before the first double quote; we use those for more sophisticated
						# checks below, to give fewer false positives like `with its downy red hairs and its “<i xml:lang="fr">doigts de faune</i>.”`
						matches = regex.findall(r"((?:.{1,2}\s)?“<(i|em)[^>]*?>[^<]+?</\2>[\!\?\.])", file_contents) + regex.findall(r"([\.\!\?] <(i|em)[^>]*?>[^<]+?</\2>[\!\?\.])", file_contents)

						# But, if we've matched a name of something, don't include that as an error. For example, `He said, “<i epub:type="se:name.publication.book">The Decameron</i>.”`
						# We also exclude the match from the list if:
						# 1. The double quote is directly preceded by a lowercase letter and a space: `with its downy red hairs and its “<i xml:lang="fr">doigts de faune</i>.”`
						# 2. The double quote is directly preceded by a lowercase letter, a comma, and a space, and the first letter within the double quote is lowercase: In the original, “<i xml:lang="es">que era un Conde de Irlos</i>.”
						matches = [x for x in matches if "epub:type=\"se:name." not in x[0] and "epub:type=\"z3998:taxonomy" not in x[0] and not regex.match(r"^[a-z’]+\s“", x[0]) and not regex.match(r"^[a-z’]+,\s“[a-z]", se.formatting.remove_tags(x[0]))]
						if matches:
							messages.append(LintMessage("When a complete clause is italicized, ending punctuation EXCEPT commas must be within containing italics.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match[0], se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for foreign phrases with italics going *outside* quotes
						matches = regex.findall(r"<i[^>]*?>“.+?\b", file_contents) + regex.findall(r"”</i>", file_contents)
						if matches:
							messages.append(LintMessage("When italicizing language in dialog, italics go INSIDE quotation marks.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for style attributes
						matches = regex.findall(r"<.+?style=\"", file_contents)
						if matches:
							messages.append(LintMessage("Illegal style attribute. Do not use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for uppercase HTML tags
						if regex.findall(r"<[A-Z]+", file_contents):
							messages.append(LintMessage("One or more uppercase HTML tags.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for nbsp within <abbr class="name">, which is redundant
						matches = regex.findall(r"<abbr[^>]+?class=\"name\"[^>]*?>[^<]*?{}[^<]*?</abbr>".format(se.NO_BREAK_SPACE), file_contents)
						if matches:
							messages.append(LintMessage("No-break space detected in <abbr class=\"name\">. This is redundant.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for Roman numerals in <title> tag
						if regex.findall(r"<title>[Cc]hapter [XxIiVv]+", file_contents):
							messages.append(LintMessage("No Roman numerals allowed in <title> tag; use decimal numbers.", se.MESSAGE_TYPE_ERROR, filename))

						# If the chapter has a number and no subtitle, check the <title> tag
						matches = regex.findall(r"<h([0-6]) epub:type=\"title z3998:roman\">([^<]+)</h\1>", file_contents, flags=regex.DOTALL)

						# But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
						if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
							try:
								chapter_number = roman.fromRoman(matches[0][1].upper())

								regex_string = r"<title>(Chapter|Section|Part) {}".format(chapter_number)
								if not regex.findall(regex_string, file_contents):
									messages.append(LintMessage("<title> tag doesn't match expected value; should be \"Chapter {}\". (Beware hidden Unicode characters!)".format(chapter_number), se.MESSAGE_TYPE_ERROR, filename))
							except Exception:
								messages.append(LintMessage("<h#> tag is marked with z3998:roman, but is not a Roman numeral", se.MESSAGE_TYPE_ERROR, filename))

						# If the chapter has a number and subtitle, check the <title> tag
						matches = regex.findall(r"<h([0-6]) epub:type=\"title\">\s*<span epub:type=\"z3998:roman\">([^<]+)</span>\s*<span epub:type=\"subtitle\">(.+?)</span>\s*</h\1>", file_contents, flags=regex.DOTALL)

						# But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
						if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
							chapter_number = roman.fromRoman(matches[0][1].upper())

							# First, remove endnotes in the subtitle, then remove all other tags (but not tag contents)
							chapter_title = regex.sub(r"<a[^<]+?epub:type=\"noteref\"[^<]*?>[^<]+?</a>", "", matches[0][2]).strip()
							chapter_title = regex.sub(r"<[^<]+?>", "", chapter_title)

							regex_string = r"<title>(Chapter|Section|Part) {}: {}".format(chapter_number, regex.escape(chapter_title))
							if not regex.findall(regex_string, file_contents):
								messages.append(LintMessage("<title> tag doesn't match expected value; should be \"Chapter {}: {}\". (Beware hidden Unicode characters!)".format(chapter_number, chapter_title), se.MESSAGE_TYPE_ERROR, filename))

						# Check for missing subtitle styling
						if "epub:type=\"subtitle\"" in file_contents and not local_css_has_subtitle_style:
							messages.append(LintMessage("Subtitles detected, but no subtitle style detected in local.css.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for whitespace before noteref
						matches = regex.findall(r"\s+<a href=\"endnotes\.xhtml#note-[0-9]+?\" id=\"noteref-[0-9]+?\" epub:type=\"noteref\">[0-9]+?</a>", file_contents)
						if matches:
							messages.append(LintMessage("Illegal white space before noteref.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for <li> elements that don't have a direct block child
						if filename != "toc.xhtml":
							matches = regex.findall(r"<li(?:\s[^>]*?>|>)\s*[^\s<]", file_contents)
							if matches:
								messages.append(LintMessage("<li> without direct block-level child.", se.MESSAGE_TYPE_WARNING, filename))
								for match in matches:
									messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for IDs on <h#> tags
						matches = regex.findall(r"<h[0-6][^>]*?id=[^>]*?>", file_contents, flags=regex.DOTALL)
						if matches:
							messages.append(LintMessage("<h#> tag with id attribute. <h#> tags should be wrapped in <section> tags, which should hold the id attribute.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check to see if <h#> tags are correctly titlecased
						matches = regex.finditer(r"<h([0-6])([^>]*?)>(.*?)</h\1>", file_contents, flags=regex.DOTALL)
						for match in matches:
							if "z3998:roman" not in match.group(2):
								title = match.group(3).strip()

								# Remove leading roman numerals first
								title = regex.sub(r"^<span epub:type=\"[^\"]*?z3998:roman[^\"]*?\">(.*?)</span>", "", title, flags=regex.DOTALL)

								# Remove leading leftover spacing and punctuation
								title = regex.sub(r"^[\s\.\,\!\?\:\;]*", "", title)

								# Remove endnotes
								title = regex.sub(r"<a[^>]*?epub:type=\"noteref\"[^>]*?>[0-9]+</a>", "", title)

								# Normalize whitespace
								title = regex.sub(r"\s+", " ", title, flags=regex.DOTALL).strip()

								# Remove nested <span>s in subtitles, which might trip up the next regex block
								title = regex.sub(r"(<span epub:type=\"subtitle\">[^<]*?)<span[^>]*?>([^<]*?</span>)", r"\1\2", title, flags=regex.DOTALL)
								title = regex.sub(r"(<span epub:type=\"subtitle\">[^<]*?)</span>([^<]*?</span>)", r"\1\2", title, flags=regex.DOTALL)

								# Do we have a subtitle? If so the first letter of that must be capitalized, so we pull that out
								subtitle_matches = regex.findall(r"(.*?)<span epub:type=\"subtitle\">(.*?)</span>(.*?)", title, flags=regex.DOTALL)
								if subtitle_matches:
									for title_header, subtitle, title_footer in subtitle_matches:
										title_header = se.formatting.titlecase(se.formatting.remove_tags(title_header).strip())
										subtitle = se.formatting.titlecase(se.formatting.remove_tags(subtitle).strip())
										title_footer = se.formatting.titlecase(se.formatting.remove_tags(title_footer).strip())

										titlecased_title = title_header + " " + subtitle + " " + title_footer
										titlecased_title = titlecased_title.strip()

										title = se.formatting.remove_tags(title).strip()
										if title != titlecased_title:
											messages.append(LintMessage("Title \"{}\" not correctly titlecased. Expected: {}".format(title, titlecased_title), se.MESSAGE_TYPE_WARNING, filename))

								# No subtitle? Much more straightforward
								else:
									titlecased_title = se.formatting.remove_tags(se.formatting.titlecase(title))
									title = se.formatting.remove_tags(title)
									if title != titlecased_title:
										messages.append(LintMessage("Title \"{}\" not correctly titlecased. Expected: {}".format(title, titlecased_title), se.MESSAGE_TYPE_WARNING, filename))

						# Check for <figure> tags without id attributes
						matches = regex.findall(r"<img[^>]*?id=\"[^>]+?>", file_contents)
						if matches:
							messages.append(LintMessage("<img> tag with ID attribute. ID attributes go on parent <figure> tags.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for closing dialog without comma
						matches = regex.findall(r"[a-z]+?” [a-zA-Z]+? said", file_contents)
						if matches:
							messages.append(LintMessage("Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for non-typogrified img alt attributes
						matches = regex.findall(r"alt=\"[^\"]*?('|--|&quot;)[^\"]*?\"", file_contents)
						if matches:
							messages.append(LintMessage("Non-typogrified ', \" (as &quot;), or -- in image alt attribute.", se.MESSAGE_TYPE_ERROR, filename))

						# Check alt attributes not ending in punctuation
						if filename not in se.IGNORED_FILENAMES:
							matches = regex.findall(r"alt=\"[^\"]*?[a-zA-Z]\"", file_contents)
							if matches:
								messages.append(LintMessage("Alt attribute doesn't appear to end with punctuation. Alt attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename))

						# Check alt attributes match image titles
						images = dom.select("img[src$=svg]")
						for image in images:
							alt_text = image["alt"]
							title_text = ""
							image_ref = image["src"].split("/").pop()
							with open(os.path.join(self.directory, "src", "epub", "images", image_ref), "r", encoding="utf-8") as image_source:
								try:
									title_text = BeautifulSoup(image_source, "lxml").title.get_text()
								except Exception:
									messages.append(LintMessage("{} missing <title> element.".format(image_ref), se.MESSAGE_TYPE_ERROR, image_ref))
							if title_text != "" and alt_text != "" and title_text != alt_text:
								messages.append(LintMessage("The <title> of {} doesn’t match the alt text in {}".format(image_ref, filename), se.MESSAGE_TYPE_ERROR, filename))

						# Check for punctuation after endnotes
						regex_string = r"<a[^>]*?epub:type=\"noteref\"[^>]*?>[0-9]+</a>[^\s<–\]\)—{}]".format(se.WORD_JOINER)
						matches = regex.findall(regex_string, file_contents)
						if matches:
							messages.append(LintMessage("Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for nbsp in measurements, for example: 90 mm
						matches = regex.findall(r"[0-9]+[\- ][mck][mgl]\b", file_contents)
						if matches:
							messages.append(LintMessage("Measurements must be separated by a no-break space, not a dash or regular space.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for line breaks after <br/> tags
						matches = regex.findall(r"<br\s*?/>[^\n]", file_contents)
						if matches:
							messages.append(LintMessage("<br/> tags must be followed by a newline, and subsequent content must be indented to the same level.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for <pre> tags
						if "<pre" in file_contents:
							messages.append(LintMessage("Illegal <pre> tag.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for double spacing
						regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
						matches = regex.findall(regex_string, file_contents)
						if matches:
							messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)", se.MESSAGE_TYPE_ERROR, filename))

						# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
						matches = regex.findall(r"[a-zA-Z][”][,.]", file_contents)
						if matches:
							messages.append(LintMessage("Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename))

						# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
						matches = regex.findall(r"\bse:[a-z]+:(?:[a-z]+:?)*", file_contents)
						if matches:
							messages.append(LintMessage("Illegal colon (:) detected in SE identifier. SE identifiers are separated by dots (.) not colons (:). Identifier: {}".format(matches), se.MESSAGE_TYPE_ERROR, filename))

						# Check for leftover asterisms
						matches = regex.findall(r"\*\s*(\*\s*)+", file_contents)
						if matches:
							messages.append(LintMessage("Illegal asterism (***) detected. Section/scene breaks must be defined by an <hr/> tag.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for space before endnote backlinks
						if filename == "endnotes.xhtml":
							# Do we have to replace Ibid.?
							matches = regex.findall(r"\bibid\b", file_contents, flags=regex.IGNORECASE)
							if matches:
								messages.append(LintMessage("Illegal \"Ibid\" in endnotes. \"Ibid\" means \"The previous reference\" which is meaningless with popup endnotes, and must be replaced by the actual thing \"Ibid\" refers to.", se.MESSAGE_TYPE_ERROR, filename))

							endnote_referrers = dom.select("li[id^=note-] a")
							bad_referrers = []

							for referrer in endnote_referrers:
								# We check against the attr value here because I couldn't figure out how to select an XML-namespaced attribute using BS4
								if "epub:type" in referrer.attrs and referrer.attrs["epub:type"] == "se:referrer":
									is_first_sib = True
									for sib in referrer.previous_siblings:
										if is_first_sib:
											is_first_sib = False
											if isinstance(sib, NavigableString):
												if sib == "\n": # Referrer preceded by newline. Check if all previous sibs are tags.
													continue
												elif sib == " " or str(sib) == se.NO_BREAK_SPACE or regex.search(r"[^\s] $", str(sib)): # Referrer preceded by a single space; we're OK
													break
												else: # Referrer preceded by a string that is not a newline and does not end with a single space
													bad_referrers.append(referrer)
													break

										else:
											# We got here because the first sib was a newline, or not a string. So, check all previous sibs.
											if isinstance(sib, NavigableString) and sib != "\n":
												bad_referrers.append(referrer)
												break

							if bad_referrers:
								messages.append(LintMessage("Endnote referrer link not preceded by exactly one space, or a newline if all previous siblings are elements.", se.MESSAGE_TYPE_WARNING, filename))
								for referrer in bad_referrers:
									messages.append(LintMessage(str(referrer), se.MESSAGE_TYPE_WARNING, filename, True))

						# If we're in the imprint, are the sources represented correctly?
						# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
						if filename == "imprint.xhtml":
							matches = regex.findall(r"<dc:source>([^<]+?)</dc:source>", self._metadata_xhtml)
							if len(matches) <= 2:
								for link in matches:
									if "gutenberg.org" in link and "<a href=\"{}\">Project Gutenberg</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: <a href=\"{}\">Project Gutenberg</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

									if "hathitrust.org" in link and "the <a href=\"{}\">HathiTrust Digital Library</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: the <a href=\"{}\">HathiTrust Digital Library</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

									if "archive.org" in link and "the <a href=\"{}\">Internet Archive</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: the <a href=\"{}\">Internet Archive</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

									if "books.google.com" in link and "<a href=\"{}\">Google Books</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: <a href=\"{}\">Google Books</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

						# Collect abbr elements for later check
						result = regex.findall("<abbr[^<]+?>", file_contents)
						result = [item.replace("eoc", "").replace(" \"", "").strip() for item in result]
						abbr_elements = list(set(result + abbr_elements))

						# Check if language tags in individual files match the language in content.opf
						if filename not in se.IGNORED_FILENAMES:
							file_language = regex.search(r"<html[^<]+xml\:lang=\"([^\"]+)\"", file_contents).group(1)
							if language != file_language:
								messages.append(LintMessage("File language is {}, but content.opf language is {}".format(file_language, language), se.MESSAGE_TYPE_ERROR, filename))

						# Check LoI descriptions to see if they match associated figcaptions
						if filename == "loi.xhtml":
							illustrations = dom.select("li > a")
							for illustration in illustrations:
								figure_ref = illustration["href"].split("#")[1]
								chapter_ref = regex.findall(r"(.*?)#.*", illustration["href"])[0]
								figcaption_text = ""
								loi_text = illustration.get_text()

								with open(os.path.join(self.directory, "src", "epub", "text", chapter_ref), "r", encoding="utf-8") as chapter:
									figure = BeautifulSoup(chapter, "lxml").select("#"+figure_ref)[0]
									if figure.figcaption:
										figcaption_text = figure.figcaption.get_text()
								if figcaption_text != "" and loi_text != "" and figcaption_text != loi_text:
									messages.append(LintMessage("The <figcaption> tag of {} doesn’t match the text in its LoI entry".format(figure_ref), se.MESSAGE_TYPE_WARNING, chapter_ref))

					# Check for missing MARC relators
					if filename == "introduction.xhtml" and ">aui<" not in self._metadata_xhtml and ">win<" not in self._metadata_xhtml:
						messages.append(LintMessage("introduction.xhtml found, but no MARC relator 'aui' (Author of introduction, but not the chief author) or 'win' (Writer of introduction)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "preface.xhtml" and ">wpr<" not in self._metadata_xhtml:
						messages.append(LintMessage("preface.xhtml found, but no MARC relator 'wpr' (Writer of preface)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "afterword.xhtml" and ">aft<" not in self._metadata_xhtml:
						messages.append(LintMessage("afterword.xhtml found, but no MARC relator 'aft' (Author of colophon, afterword, etc.)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "endnotes.xhtml" and ">ann<" not in self._metadata_xhtml:
						messages.append(LintMessage("endnotes.xhtml found, but no MARC relator 'ann' (Annotator)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "loi.xhtml" and ">ill<" not in self._metadata_xhtml:
						messages.append(LintMessage("loi.xhtml found, but no MARC relator 'ill' (Illustrator)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "colophon.xhtml" and "<a class=\"raw-url\" href=\"{}\">{}</a>".format(self.generated_identifier.replace("url:", ""), self.generated_identifier.replace("url:https://", "")) not in file_contents:
						messages.append(LintMessage("Unexpected SE identifier in colophon. Expected: {}".format(self.generated_identifier), se.MESSAGE_TYPE_ERROR, filename))

					# Check for wrong semantics in frontmatter/backmatter
					if filename in se.FRONTMATTER_FILENAMES and "frontmatter" not in file_contents:
						messages.append(LintMessage("No frontmatter semantic inflection for what looks like a frontmatter file", se.MESSAGE_TYPE_WARNING, filename))

					if filename in se.BACKMATTER_FILENAMES and "backmatter" not in file_contents:
						messages.append(LintMessage("No backmatter semantic inflection for what looks like a backmatter file", se.MESSAGE_TYPE_WARNING, filename))

		if cover_svg_title != titlepage_svg_title:
			messages.append(LintMessage("cover.svg and titlepage.svg <title> tags don't match", se.MESSAGE_TYPE_ERROR))

		if has_frontmatter and not has_halftitle:
			messages.append(LintMessage("Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		if not has_cover_source:
			messages.append(LintMessage("./images/cover.source.jpg not found", se.MESSAGE_TYPE_ERROR, "cover.source.jpg"))

		single_use_css_classes = []

		for css_class in xhtml_css_classes:
			if css_class not in se.IGNORED_CLASSES:
				if "." + css_class not in css:
					messages.append(LintMessage("class “{}” found in xhtml, but no style in local.css".format(css_class), se.MESSAGE_TYPE_ERROR, "local.css"))

			if xhtml_css_classes[css_class] == 1 and css_class not in se.IGNORED_CLASSES and not regex.match(r"^i[0-9]$", css_class):
				# Don't count ignored classes OR i[0-9] which are used for poetry styling
				single_use_css_classes.append(css_class)

		if single_use_css_classes:
			messages.append(LintMessage("CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks.", se.MESSAGE_TYPE_WARNING, "local.css"))
			for css_class in single_use_css_classes:
				messages.append(LintMessage(css_class, se.MESSAGE_TYPE_WARNING, "local.css", True))

		headings = list(set(headings))
		with open(os.path.join(self.directory, "src", "epub", "toc.xhtml"), "r", encoding="utf-8") as toc:
			toc = BeautifulSoup(toc.read(), "lxml")
			landmarks = toc.find("nav", attrs={"epub:type": "landmarks"})
			toc = toc.find("nav", attrs={"epub:type": "toc"})

			# Depth first search using recursiveChildGenerator to get the headings in order
			toc_entries = []
			for child in toc.recursiveChildGenerator():
				if getattr(child, "name") == "a":
					toc_entries.append(child)

			# Match ToC headings against text headings
			# Unlike main headings, ToC entries have a ‘:’ before the subheading so we need to strip these for comparison
			toc_headings = []
			for index, entry in enumerate(toc_entries):
				entry_text = " ".join(entry.get_text().replace(":", "").split())
				entry_file = regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", entry.get("href"))
				toc_headings.append((entry_text, entry_file))
			for heading in headings:
				# Occasionally we find a heading with a colon, but as we’ve stripped our
				# ToC-only colons above we also need to do that here for the comparison.
				heading_without_colons = (heading[0].replace(":", ""), heading[1])
				if heading_without_colons not in toc_headings:
					messages.append(LintMessage("Heading ‘{}’ found, but not present for that file in the ToC".format(heading[0]), se.MESSAGE_TYPE_ERROR, heading[1]))

			# Check our ordered ToC entries against the spine
			# To cover all possibilities, we combine the toc and the landmarks to get the full set of entries
			with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r", encoding="utf-8") as content_opf:
				toc_files = []
				for index, entry in enumerate(landmarks.find_all("a", attrs={"epub:type": regex.compile("^.*(frontmatter|bodymatter).*$")})):
					entry_file = regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", entry.get("href"))
					toc_files.append(entry_file)
				for index, entry in enumerate(toc_entries):
					entry_file = regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", entry.get("href"))
					toc_files.append(entry_file)
				unique_toc_files = []
				[unique_toc_files.append(i) for i in toc_files if not unique_toc_files.count(i)]
				toc_files = unique_toc_files
				spine_entries = BeautifulSoup(content_opf.read(), "lxml").find("spine").find_all("itemref")
				for index, entry in enumerate(spine_entries):
					if toc_files[index] != entry.attrs["idref"]:
						messages.append(LintMessage("The spine order does not match the order of the ToC and landmarks", se.MESSAGE_TYPE_ERROR, "content.opf"))
						break

		for element in abbr_elements:
			try:
				css_class = regex.search(r"class=\"([^\"]+?)\"", element).group(1)
			except Exception:
				continue
			if css_class and (css_class == "temperature" or css_class == "era" or css_class == "acronym") and "abbr." + css_class not in abbr_styles:
				messages.append(LintMessage("abbr.{} element found, but no required style in local.css (See typgoraphy manual for style)".format(css_class), se.MESSAGE_TYPE_ERROR, "local.css"))

		return messages
