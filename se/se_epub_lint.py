#!/usr/bin/env python3
"""
Contains the LintMessage class and the Lint function, which is broken out of
the SeEpub class for readability and maintainability.

Strictly speaking, the lint() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

import filecmp
import glob
import html
import io
import os
import unicodedata
from pathlib import Path
from typing import Dict, List
import importlib_resources
import lxml.cssselect
import lxml.etree as etree
import regex
import roman
from bs4 import BeautifulSoup, NavigableString
import se
import se.easy_xml
import se.formatting
import se.images


COLOPHON_VARIABLES = ["TITLE", "YEAR", "AUTHOR_WIKI_URL", "AUTHOR", "PRODUCER_URL", "PRODUCER", "PG_YEAR", "TRANSCRIBER_1", "TRANSCRIBER_2", "PG_URL", "IA_URL", "PAINTING", "ARTIST_WIKI_URL", "ARTIST"]
EPUB_SEMANTIC_VOCABULARY = ["cover", "frontmatter", "bodymatter", "backmatter", "volume", "part", "chapter", "division", "foreword", "preface", "prologue", "introduction", "preamble", "conclusion", "epilogue", "afterword", "epigraph", "toc", "landmarks", "loa", "loi", "lot", "lov", "appendix", "colophon", "index", "index-headnotes", "index-legend", "index-group", "index-entry-list", "index-entry", "index-term", "index-editor-note", "index-locator", "index-locator-list", "index-locator-range", "index-xref-preferred", "index-xref-related", "index-term-category", "index-term-categories", "glossary", "glossterm", "glossdef", "bibliography", "biblioentry", "titlepage", "halftitlepage", "copyright-page", "acknowledgments", "imprint", "imprimatur", "contributors", "other-credits", "errata", "dedication", "revision-history", "notice", "tip", "halftitle", "fulltitle", "covertitle", "title", "subtitle", "bridgehead", "learning-objective", "learning-resource", "assessment", "qna", "panel", "panel-group", "balloon", "text-area", "sound-area", "footnote", "endnote", "footnotes", "endnotes", "noteref", "keyword", "topic-sentence", "concluding-sentence", "pagebreak", "page-list", "table", "table-row", "table-cell", "list", "list-item", "figure", "aside"]

class LintMessage:
	"""
	An object representing an output message for the lint function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	def __init__(self, text: str, message_type=se.MESSAGE_TYPE_WARNING, filename: str = "", submessages: List[str] = None):
		self.text = text.strip()
		self.filename = filename
		self.message_type = message_type
		self.submessages = submessages

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
	if "http://gutenberg.org" in xhtml or "https://gutenberg.org" in xhtml:
		messages.append(LintMessage("gutenberg.org URL missing leading www.", se.MESSAGE_TYPE_ERROR))

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

def _get_unused_selectors(self) -> List[str]:
	"""
	Helper function used in self.lint(); merge directly into lint()?
	Get a list of CSS selectors that do not actually select HTML in the epub.

	INPUTS
	None

	OUTPUTS
	A list of strings representing CSS selectors that do not actually select HTML in the epub.
	"""

	try:
		with open(self.path / "src" / "epub" / "css" / "local.css", encoding="utf-8") as file:
			css = file.read()
	except Exception:
		raise FileNotFoundError("Couldn’t open {}".format(self.path / "src" / "epub" / "css" / "local.css"))

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
	selectors = {line for line in css.splitlines() if line != ""}
	unused_selectors = set(selectors)

	# Get a list of .xhtml files to search
	filenames = glob.glob(str(self.path / "src" / "epub" / "text" / "*.xhtml"))

	# Now iterate over each CSS selector and see if it's used in any of the files we found
	for selector in selectors:
		try:
			sel = lxml.cssselect.CSSSelector(selector, translator="html", namespaces=se.XHTML_NAMESPACES)
		except lxml.cssselect.ExpressionError:
			# This gets thrown if we use pseudo-elements, which lxml doesn't support
			unused_selectors.remove(selector)
			continue
		except lxml.cssselect.SelectorSyntaxError as ex:
			raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: {selector}\n{ex}")

		for filename in filenames:
			if not filename.endswith("titlepage.xhtml") and not filename.endswith("imprint.xhtml") and not filename.endswith("uncopyright.xhtml"):
				# We have to remove the default namespace declaration from our document, otherwise
				# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
				with open(filename, "r", encoding="utf-8") as file:
					xhtml = file.read().replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")

				try:
					tree = etree.fromstring(str.encode(xhtml))
				except etree.XMLSyntaxError as ex:
					raise se.InvalidXhtmlException("Couldn’t parse XHTML in file: {}, error: {}".format(filename, str(ex)))
				except Exception:
					raise se.InvalidXhtmlException(f"Couldn’t parse XHTML in file: {filename}")

				if tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
					unused_selectors.remove(selector)
					break

	return list(unused_selectors)

def lint(self, metadata_xhtml) -> list:
	"""
	Check this ebook for some common SE style errors.

	INPUTS
	None

	OUTPUTS
	A list of LintMessage objects.
	"""

	messages = []
	has_halftitle = False
	has_frontmatter = False
	has_cover_source = False
	cover_svg_title = ""
	titlepage_svg_title = ""
	xhtml_css_classes: Dict[str, int] = {}
	headings: List[tuple] = []

	# Get the ebook language, for later use
	language = regex.search(r"<dc:language>([^>]+?)</dc:language>", metadata_xhtml).group(1)

	# Check local.css for various items, for later use
	abbr_elements: List[str] = []
	css = ""
	with open(self.path / "src" / "epub" / "css" / "local.css", "r", encoding="utf-8") as file:
		css = file.read()

		local_css_has_subtitle_style = "span[epub|type~=\"subtitle\"]" in css

		abbr_styles = regex.findall(r"abbr\.[a-z]+", css)

		matches = regex.findall(r"^h[0-6]\s*,?{?", css, flags=regex.MULTILINE)
		if matches:
			messages.append(LintMessage("Do not directly select h[0-6] elements, as they are used in template files; use more specific selectors.", se.MESSAGE_TYPE_ERROR, "local.css"))

	# Check for presence of ./dist/ folder
	if (self.path / "dist").exists():
		messages.append(LintMessage("Illegal ./dist/ folder. Do not commit compiled versions of the source.", se.MESSAGE_TYPE_ERROR, "./dist/"))

	# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
	if regex.search(r"#description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", metadata_xhtml.replace("\"&gt;", "").replace("=\"", "")) is not None:
		messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata long description", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check if there are non-typogrified quotes or em-dashes in the title.
	# The open-ended start and end of the regex also catches title-sort
	if regex.search(r"title\">[^<]+?(['\"]|\-\-)[^<]+?<", metadata_xhtml) is not None:
		messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata title", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for malformed long description HTML
	long_description = regex.findall(r"<meta id=\"long-description\".+?>(.+?)</meta>", metadata_xhtml, flags=regex.DOTALL)
	if long_description:
		long_description = "<?xml version=\"1.0\"?><html xmlns=\"http://www.w3.org/1999/xhtml\">" + html.unescape(long_description[0]) + "</html>"
		try:
			etree.parse(io.StringIO(long_description))
		except lxml.etree.XMLSyntaxError as ex:
			messages.append(LintMessage("Metadata long description is not valid HTML. LXML says: " + str(ex), se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for double spacing
	regex_string = fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}"
	matches = regex.findall(regex_string, metadata_xhtml)
	if matches:
		messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	if regex.search(r"<dc:description id=\"description\">[^<]+?(['\"]|\-\-)[^<]+?</dc:description>", metadata_xhtml) is not None:
		messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata dc:description.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
	matches = regex.findall(r"[a-zA-Z][”][,.]", metadata_xhtml)
	if matches:
		messages.append(LintMessage("Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, "content.opf"))

	# Make sure long-description is escaped HTML
	if "<meta id=\"long-description\" property=\"se:long-description\" refines=\"#description\">\n\t\t\t&lt;p&gt;" not in metadata_xhtml:
		messages.append(LintMessage("Long description must be escaped HTML.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for HTML entities in long-description, but allow &amp;amp;
	if regex.search(r"&amp;[a-z]+?;", metadata_xhtml.replace("&amp;amp;", "")):
		messages.append(LintMessage("HTML entites detected in metadata. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal em-dashes in <dc:subject>
	if regex.search(r"<dc:subject id=\"[^\"]+?\">[^<]+?—[^<]+?</dc:subject>", metadata_xhtml) is not None:
		messages.append(LintMessage("Illegal em-dash detected in dc:subject; use --", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for empty production notes
	if "<meta property=\"se:production-notes\">Any special notes about the production of this ebook for future editors/producers? Remove this element if not.</meta>" in metadata_xhtml:
		messages.append(LintMessage("Empty production-notes element in metadata.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal VCS URLs
	matches = regex.findall(r"<meta property=\"se:url\.vcs\.github\">([^<]+?)</meta>", metadata_xhtml)
	if matches:
		for match in matches:
			if not match.startswith("https://github.com/standardebooks/"):
				messages.append(LintMessage(f"Illegal se:url.vcs.github. VCS URLs must begin with https://github.com/standardebooks/: {match}", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for HathiTrust scan URLs instead of actual record URLs
	if "babel.hathitrust.org" in metadata_xhtml or "hdl.handle.net" in metadata_xhtml:
		messages.append(LintMessage("Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: https://catalog.hathitrust.org/Record/<RECORD-ID>", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal se:subject tags
	matches = regex.findall(r"<meta property=\"se:subject\">([^<]+?)</meta>", metadata_xhtml)
	if matches:
		for match in matches:
			if match not in se.SE_GENRES:
				messages.append(LintMessage(f"Illegal se:subject: {match}", se.MESSAGE_TYPE_ERROR, "content.opf"))
	else:
		messages.append(LintMessage("No se:subject <meta> element found.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for CDATA tags
	if "<![CDATA[" in metadata_xhtml:
		messages.append(LintMessage("<![CDATA[ detected. Run `clean` to canonicalize <![CDATA[ sections.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check that our provided identifier matches the generated identifier
	identifier = regex.sub(r"<.+?>", "", regex.findall(r"<dc:identifier id=\"uid\">.+?</dc:identifier>", metadata_xhtml)[0])
	if identifier != self.generated_identifier:
		messages.append(LintMessage(f"<dc:identifier> does not match expected: {self.generated_identifier}", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check that the GitHub repo URL is as expected
	if ("<meta property=\"se:url.vcs.github\">" + self.generated_github_repo_url + "</meta>") not in metadata_xhtml:
		messages.append(LintMessage(f"GitHub repo URL does not match expected: {self.generated_github_repo_url}", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check if se:name.person.full-name matches their titlepage name
	matches = regex.findall(r"<meta property=\"se:name\.person\.full-name\" refines=\"#([^\"]+?)\">([^<]*?)</meta>", metadata_xhtml)
	duplicate_names = []
	for match in matches:
		name_matches = regex.findall(fr"<([a-z:]+)[^<]+?id=\"{match[0]}\"[^<]*?>([^<]*?)</\1>", metadata_xhtml)
		for name_match in name_matches:
			if name_match[1] == match[1]:
				duplicate_names.append(name_match[1])

	if duplicate_names:
		messages.append(LintMessage("se:name.person.full-name property identical to regular name. If the two are identical the full name <meta> element must be removed.", se.MESSAGE_TYPE_ERROR, "content.opf", duplicate_names))

	# Check for malformed URLs
	for message in _get_malformed_urls(metadata_xhtml):
		message.filename = "content.opf"
		messages.append(message)

	if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", metadata_xhtml):
		messages.append(LintMessage("id.loc.gov URL ending with illegal .html", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Does the manifest match the generated manifest?
	for manifest in regex.findall(r"<manifest>.*?</manifest>", metadata_xhtml, flags=regex.DOTALL):
		manifest = regex.sub(r"[\n\t]", "", manifest)
		expected_manifest = regex.sub(r"[\n\t]", "", self.generate_manifest())

		if manifest != expected_manifest:
			messages.append(LintMessage("<manifest> does not match expected structure.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Make sure some static files are unchanged
	try:
		with importlib_resources.path("se.data.templates", "LICENSE.md") as license_file_path:
			if not filecmp.cmp(license_file_path, self.path / "LICENSE.md"):
				messages.append(LintMessage(f"LICENSE.md does not match {license_file_path}", se.MESSAGE_TYPE_ERROR, "LICENSE.md"))
	except Exception:
		messages.append(LintMessage("Missing ./LICENSE.md", se.MESSAGE_TYPE_ERROR, "LICENSE.md"))

	with importlib_resources.path("se.data.templates", "core.css") as core_css_file_path:
		if not filecmp.cmp(core_css_file_path, self.path / "src" / "epub" / "css" / "core.css"):
			messages.append(LintMessage(f"core.css does not match {core_css_file_path}", se.MESSAGE_TYPE_ERROR, "core.css"))

	with importlib_resources.path("se.data.templates", "logo.svg") as logo_svg_file_path:
		if not filecmp.cmp(logo_svg_file_path, self.path / "src" / "epub" / "images" / "logo.svg"):
			messages.append(LintMessage(f"logo.svg does not match {logo_svg_file_path}", se.MESSAGE_TYPE_ERROR, "logo.svg"))

	with importlib_resources.path("se.data.templates", "uncopyright.xhtml") as uncopyright_file_path:
		if not filecmp.cmp(uncopyright_file_path, self.path / "src" / "epub" / "text" / "uncopyright.xhtml"):
			messages.append(LintMessage(f"uncopyright.xhtml does not match {uncopyright_file_path}", se.MESSAGE_TYPE_ERROR, "uncopyright.xhtml"))

	# Check for unused selectors
	unused_selectors = _get_unused_selectors(self)
	if unused_selectors:
		messages.append(LintMessage("Unused CSS selectors:", se.MESSAGE_TYPE_ERROR, "local.css", unused_selectors))

	# Now iterate over individual files for some checks
	for root, _, filenames in os.walk(self.path):
		for filename in sorted(filenames, key=se.natural_sort_key):
			if ".git" in str(Path(root) / filename):
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
					with importlib_resources.path("se.data.templates", "gitignore") as gitignore_file_path:
						if not filecmp.cmp(gitignore_file_path, str(self.path / ".gitignore")):
							messages.append(LintMessage(f".gitignore does not match {gitignore_file_path}", se.MESSAGE_TYPE_ERROR, ".gitignore"))
							continue
				else:
					messages.append(LintMessage(f"Illegal {filename} file detected in {root}", se.MESSAGE_TYPE_ERROR))
					continue

			with open(Path(root) / filename, "r", encoding="utf-8") as file:
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
					if "<title>Half Title</title>" not in file_contents:
						messages.append(LintMessage("Half title <title> elements must contain exactly: \"Half Title\".", se.MESSAGE_TYPE_ERROR, filename))

				if filename == "colophon.xhtml":
					if "<a href=\"{}\">{}</a>".format(self.generated_identifier.replace("url:", ""), self.generated_identifier.replace("url:https://", "")) not in file_contents:
						messages.append(LintMessage(f"Unexpected SE identifier in colophon. Expected: {self.generated_identifier}", se.MESSAGE_TYPE_ERROR, filename))

					if ">trl<" in metadata_xhtml and "translated from" not in file_contents:
						messages.append(LintMessage("Translator detected in metadata, but no “translated from LANG” block in colophon", se.MESSAGE_TYPE_ERROR, filename))

					# Check if we forgot to fill any variable slots
					for variable in COLOPHON_VARIABLES:
						if variable in file_contents:
							messages.append(LintMessage(f"Missing data in colophon: {variable}", se.MESSAGE_TYPE_ERROR, filename))

					# Are the sources represented correctly?
					# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
					matches = regex.findall(r"<dc:source>([^<]+?)</dc:source>", metadata_xhtml)
					if len(matches) <= 2:
						for link in matches:
							if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
								messages.append(LintMessage(f"Source not represented in colophon.xhtml. Expected: <a href=\"{link}\">Project Gutenberg</a>", se.MESSAGE_TYPE_WARNING, filename))

							if "hathitrust.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
								messages.append(LintMessage(f"Source not represented in colophon.xhtml. Expected: the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>", se.MESSAGE_TYPE_WARNING, filename))

							if "archive.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">Internet Archive</a>" not in file_contents:
								messages.append(LintMessage(f"Source not represented in colophon.xhtml. Expected: the<br/> <a href=\"{link}\">Internet Archive</a>", se.MESSAGE_TYPE_WARNING, filename))

							if "books.google.com" in link and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
								messages.append(LintMessage(f"Source not represented in colophon.xhtml. Expected: <a href=\"{link}\">Google Books</a>", se.MESSAGE_TYPE_WARNING, filename))

				if filename == "titlepage.xhtml":
					if "<title>Titlepage</title>" not in file_contents:
						messages.append(LintMessage("Titlepage <title> elements must contain exactly: \"Titlepage\".", se.MESSAGE_TYPE_ERROR, filename))

				if filename.endswith(".svg"):
					# Check for fill: #000 which should simply be removed
					matches = regex.findall(r"fill=\"\s*#000", file_contents) + regex.findall(r"style=\"[^\"]*?fill:\s*#000", file_contents)
					if matches:
						messages.append(LintMessage("Illegal style=\"fill: #000\" or fill=\"#000\".", se.MESSAGE_TYPE_ERROR, filename))

					# Check for illegal height or width on root <svg> element
					if filename != "logo.svg": # Do as I say, not as I do...
						matches = regex.findall(r"<svg[^>]*?(height|width)=[^>]*?>", file_contents)
						if matches:
							messages.append(LintMessage("Illegal height or width on root <svg> element. Size SVGs using the viewbox attribute only.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for illegal transform attribute
					matches = regex.findall(r"<[a-z]+[^>]*?transform=[^>]*?>", file_contents)
					if matches:
						messages.append(LintMessage("Illegal transform attribute. SVGs should be optimized to remove use of transform. Try using Inkscape to save as an \"optimized SVG\".", se.MESSAGE_TYPE_ERROR, filename))

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
								if match not in ("translated by", "illustrated by", "and"):
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
					matches = regex.findall(r"abbr[^{]*?{[^}]*?white-space:\s*nowrap;[^}]*?}", css, regex.DOTALL)
					if matches:
						messages.append(LintMessage("abbr selector does not need white-space: nowrap; as it inherits it from core.css.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Don't specify border color
					matches = regex.findall(r"(?:border|color).+?(?:#[a-f0-9]{0,6}|black|white|red)", file_contents, flags=regex.IGNORECASE)
					if matches:
						messages.append(LintMessage("Don’t specify border colors, so that reading systems can adjust for night mode.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# If we select on the xml namespace, make sure we define the namespace in the CSS, otherwise the selector won't work
					matches = regex.findall(r"\[\s*xml\s*\|", file_contents)
					if matches and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in file_contents:
						messages.append(LintMessage("[xml|attr] selector in CSS, but no XML namespace declared (@namespace xml \"http://www.w3.org/XML/1998/namespace\";).", se.MESSAGE_TYPE_ERROR, filename))


				if filename.endswith(".xhtml"):
					for message in _get_malformed_urls(file_contents):
						message.filename = filename
						messages.append(message)

					# Check if this is a frontmatter file
					if filename not in ("titlepage.xhtml", "imprint.xhtml", "toc.xhtml"):
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
						for match in dom.select("h1,h2,h3,h4,h5,h6"):

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
								# If an <h#> tag has a subtitle, the non-subtitle text must also be wrapped in a <span>.
								# This invocation of match.find() returns all text nodes. We don't want any text nodes, so if it returns anything then we know we're
								# missing a <span> somewhere.
								if match.find(text=True, recursive=False).strip():
									messages.append(LintMessage(f"<{match.name}> element has subtitle <span>, but first line is not wrapped in a <span>. See semantics manual for structure of headers with subtitles.", se.MESSAGE_TYPE_ERROR, filename))

								# OK, move on with processing headers.
								parent_section = match.find_parents("section")

								# Sometimes we might not have a parent <section>, like in Keats' Poetry
								if not parent_section:
									parent_section = match.find_parents("body")

								closest_section_epub_type = parent_section[0].get("epub:type") or ""
								heading_first_child_epub_type = match.find("span", recursive=False).get("epub:type") or ""

								if regex.findall(r"^.*(part|division|volume).*$", closest_section_epub_type) and not regex.findall(r"^.*se:short-story.*$", closest_section_epub_type):
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
						messages.append(LintMessage("If <span> exists only for the z3998:roman semantic, then z3998:roman should be pulled into parent element instead.", se.MESSAGE_TYPE_WARNING, filename, [match[1] for match in matches]))

					# Check for "Hathi Trust" instead of "HathiTrust"
					if "Hathi Trust" in file_contents:
						messages.append(LintMessage("`Hathi Trust` should be `HathiTrust`", se.MESSAGE_TYPE_ERROR, filename))

					# Check for uppercase letters in IDs or classes
					matches = dom.select("[id],[class]")
					for match in matches:
						if match.has_attr("id"):
							normalized_id = unicodedata.normalize("NFKD", match["id"])
							uppercase_matches = regex.findall(r"[A-Z]+", normalized_id)
							if uppercase_matches:
								messages.append(LintMessage("Uppercase ID attribute. Attribute values must be all lowercase.", se.MESSAGE_TYPE_ERROR, filename, uppercase_matches))

							number_matches = regex.findall(r"^[0-9]+.+", normalized_id)
							if number_matches:
								messages.append(LintMessage("ID starting with a number is illegal XHTML.", se.MESSAGE_TYPE_ERROR, filename, number_matches))

						if match.has_attr("class"):
							for css_class in match["class"]:
								uppercase_matches = regex.findall(r"[A-Z]+", unicodedata.normalize("NFKD", css_class))
								if uppercase_matches:
									messages.append(LintMessage("Uppercase class attribute. Attribute values must be all lowercase.", se.MESSAGE_TYPE_ERROR, filename, uppercase_matches))

					matches = [x for x in dom.select("section") if not x.has_attr("id")]
					if matches:
						messages.append(LintMessage("<section> element without id attribute.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for empty title tags
					if "<title/>" in file_contents or "<title></title>" in file_contents:
						messages.append(LintMessage("Empty <title> element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for numeric entities
					matches = regex.findall(r"&#[0-9]+?;", file_contents)
					if matches:
						messages.append(LintMessage("Illegal numeric entity (like &#913;) in file.", se.MESSAGE_TYPE_ERROR, filename))

					# Check nested <blockquote> elements
					matches = regex.findall(r"<blockquote[^>]*?>\s*<blockquote", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("Nested <blockquote> element.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for <hr> tags before the end of a section, which is a common PG artifact
					matches = regex.findall(r"<hr[^>]*?/?>\s*</section>", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("Illegal <hr/> before the end of a section.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for double greater-than at the end of a tag
					matches = regex.findall(r"(>>|>&gt;)", file_contents)
					if matches:
						messages.append(LintMessage("Elements should end with a single >.", se.MESSAGE_TYPE_WARNING, filename))

					# Ignore the title page here, because we often have publishers with ampersands as
					# translators, but in alt tags. Like "George Allen & Unwin".
					if filename != "titlepage.xhtml":
						# Before we process this, we remove the eoc class from <abbr class="name"> because negative lookbehind
						# must be fixed-width. I.e. we can't do `class="name( eoc)?"`
						temp_file_contents = file_contents.replace("\"name eoc\"", "\"name\"")

						# Check for nbsp before ampersand (&amp)
						matches = regex.findall(fr"(?<!\<abbr class=\"name\")>[^>]*?[^{se.NO_BREAK_SPACE}]\&amp;", temp_file_contents)
						if matches:
							messages.append(LintMessage("Required nbsp not found before &amp;", se.MESSAGE_TYPE_WARNING, filename))

						# Check for nbsp after ampersand (&amp)
						matches = regex.findall(fr"(?<!\<abbr class=\"name\")>[^>]*?\&amp;[^{se.NO_BREAK_SPACE}]", temp_file_contents)
						if matches:
							messages.append(LintMessage("Required nbsp not found after &amp;", se.MESSAGE_TYPE_WARNING, filename))

					# Check for nbsp before times
					matches = regex.findall(fr"[0-9]+[^{se.NO_BREAK_SPACE}]<abbr class=\"time", file_contents)
					if matches:
						messages.append(LintMessage("Required nbsp not found before <abbr class=\"time\">", se.MESSAGE_TYPE_WARNING, filename))

					# Check for low-hanging misquoted fruit
					matches = regex.findall(r"[A-Za-z]+[“‘]", file_contents)
					if matches:
						messages.append(LintMessage("Possible mis-curled quotation mark.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check that times have colons and not periods
					matches = regex.findall(r"[0-9]\.[0-9]+\s<abbr class=\"time", file_contents) + regex.findall(r"at [0-9]\.[0-9]+", file_contents)
					if matches:
						messages.append(LintMessage("Times must be separated by colons (:) not periods (.)", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for leading 0 in IDs (note: not the same as checking for IDs that start with an integer)
					matches = regex.findall(r"id=\"[^\"]+?\-0[0-9]+[^\"]*?\"", file_contents)
					if matches:
						messages.append(LintMessage("Illegal leading 0 in ID attribute", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for stage direction that ends in ?! but also has a trailing period
					matches = regex.findall(r"<i epub:type=\"z3998:stage-direction\">(?:(?!<i).)*?\.</i>[,:;!?]", file_contents)
					if matches:
						messages.append(LintMessage("Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for ending punctuation inside italics that have semantics.
					# Ignore the colophon because paintings might have punctuation in their names
					if filename != "colophon.xhtml":
						matches = regex.findall(r"(<([ib]) epub:type=\"[^\"]*?se:name\.[^\"]*?\">[^<]+?[\.,\!\?]</\2>)", file_contents)
						filtered_matches = []
						for match in matches:
							if "z3998:stage-direction" not in match[0]:
								filtered_matches.append(match[0])

						# ...and also check for ending punctuation inside em tags, if it looks like a *part* of a clause
						# instead of a whole clause. If the <em> is preceded by an em dash or quotes then it's
						# presumed to be a whole clause.
						matches = regex.findall(r"(?:[^—“‘])<em>(?:\w+?\s*){1,2}?[\.,\!\?]<\/em>", file_contents)
						for match in matches:
							if match[4].islower():
								filtered_matches.append(match)

						if filtered_matches:
							messages.append(LintMessage("Ending punctuation inside italics.", se.MESSAGE_TYPE_WARNING, filename, filtered_matches))

					# Check for money not separated by commas
					matches = regex.findall(r"[£\$][0-9]{4,}", file_contents)
					if matches:
						messages.append(LintMessage("Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for deprecated MathML elements
					matches = regex.findall(r"<(?:m:)?mfenced[^>]*?>.+?</(?:m:)?mfenced>", file_contents)
					if matches:
						messages.append(LintMessage("<m:mfenced> is deprecated in the MathML spec. Use <m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for period following Roman numeral, which is an old-timey style we must fix
					# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
					matches = regex.findall(r"(?<!<p[^>]*?>)<span epub:type=\"z3998:roman\">[^<]+?</span>\.\s+[a-z]", file_contents)
					if matches:
						messages.append(LintMessage("Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for two em dashes in a row
					matches = regex.findall(fr"—{se.WORD_JOINER}*—+", file_contents)
					if matches:
						messages.append(LintMessage("Two or more em-dashes in a row detected. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <abbr class="name"> that does not contain spaces
					matches = regex.findall(r"<abbr class=\"name\">[^<]*?[A-Z]\.[A-Z]\.[^<]*?</abbr>", file_contents)
					if matches:
						messages.append(LintMessage("Initials in <abbr class=\"name\"> not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for empty <h2> missing epub:type="title" attribute
					if "<h2>" in file_contents:
						messages.append(LintMessage("<h2> element without `epub:type=\"title\"` attribute.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for a common typo
					if "z3998:nonfiction" in file_contents:
						messages.append(LintMessage("z3998:nonfiction should be z3998:non-fiction", se.MESSAGE_TYPE_ERROR, filename))

					# Check for empty <p> tags
					matches = regex.findall(r"<p[^>]*?>\s*</p>", file_contents)
					if "<p/>" in file_contents or matches:
						messages.append(LintMessage("Empty <p> element. Use <hr/> for thematic breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <p> tags that end with <br/>
					matches = regex.findall(r"(\s*<br/?>\s*)+</p>", file_contents)
					if matches:
						messages.append(LintMessage("<br/> element found before closing </p> tag.", se.MESSAGE_TYPE_ERROR, filename))

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
						messages.append(LintMessage("When a complete clause is italicized, ending punctuation except commas must be within containing italics.", se.MESSAGE_TYPE_WARNING, filename, [match[0] for match in matches]))

					# Run some checks on <i> elements
					comma_matches = []
					italicizing_matches = []
					elements = dom.select("i")
					for elem in elements:
						next_sib = elem.nextSibling

						# Check for trailing commas inside <i> tags at the close of dialog
						# More sophisticated version of: \b[^\s]+?,</i>”
						if isinstance(next_sib, NavigableString) and next_sib.startswith("”") and elem.text.endswith(","):
							comma_matches.append(str(elem) + "”")

						# Check for foreign phrases with italics going *outside* quotes
						for attr in elem.attrs:
							if attr == "xml:lang" and (elem.text.startswith("“") or elem.text.endswith("”")):
								italicizing_matches.append(str(elem))

					if comma_matches:
						messages.append(LintMessage("Comma inside <i> element before closing dialog.", se.MESSAGE_TYPE_WARNING, filename, comma_matches))

					if italicizing_matches:
						messages.append(LintMessage("When italicizing language in dialog, italics go inside quotation marks.", se.MESSAGE_TYPE_WARNING, filename, italicizing_matches))

					# Check for style attributes
					matches = regex.findall(r"<.+?style=\"", file_contents)
					if matches:
						messages.append(LintMessage("Illegal style attribute. Do not use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for uppercase HTML tags
					if regex.findall(r"<[A-Z]+", file_contents):
						messages.append(LintMessage("One or more uppercase HTML tags.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for nbsp within <abbr class="name">, which is redundant
					matches = regex.findall(fr"<abbr[^>]+?class=\"name\"[^>]*?>[^<]*?{se.NO_BREAK_SPACE}[^<]*?</abbr>", file_contents)
					if matches:
						messages.append(LintMessage("No-break space detected in <abbr class=\"name\">. This is redundant.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for Roman numerals in <title> tag
					if regex.findall(r"<title>[Cc]hapter [XxIiVv]+", file_contents):
						messages.append(LintMessage("No Roman numerals allowed in <title> element; use decimal numbers.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for HTML tags in <title> tags
					matches = regex.findall(r"<title>.*?[<].*?</title>", file_contents)
					if matches:
						messages.append(LintMessage("Element in <title> element", se.MESSAGE_TYPE_ERROR, filename, matches))

					# If the chapter has a number and no subtitle, check the <title> tag...
					matches = regex.findall(r"<h([0-6]) epub:type=\"title z3998:roman\">([^<]+)</h\1>", file_contents, flags=regex.DOTALL)

					# ...But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
					if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
						try:
							chapter_number = roman.fromRoman(matches[0][1].upper())

							regex_string = fr"<title>(Chapter|Section|Part) {chapter_number}"
							if not regex.findall(regex_string, file_contents):
								messages.append(LintMessage(f"<title> element doesn’t match expected value; should be `Chapter {chapter_number}`. (Beware hidden Unicode characters!)", se.MESSAGE_TYPE_ERROR, filename))
						except Exception:
							messages.append(LintMessage("<h#> element is marked with z3998:roman, but is not a Roman numeral", se.MESSAGE_TYPE_ERROR, filename))

					# If the chapter has a number and subtitle, check the <title> tag...
					matches = regex.findall(r"<h([0-6]) epub:type=\"title\">\s*<span epub:type=\"z3998:roman\">([^<]+)</span>\s*<span epub:type=\"subtitle\">(.+?)</span>\s*</h\1>", file_contents, flags=regex.DOTALL)

					# ...But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
					if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
						chapter_number = roman.fromRoman(matches[0][1].upper())

						# First, remove endnotes in the subtitle, then remove all other tags (but not tag contents)
						chapter_title = regex.sub(r"<a[^<]+?epub:type=\"noteref\"[^<]*?>[^<]+?</a>", "", matches[0][2]).strip()
						chapter_title = regex.sub(r"<[^<]+?>", "", chapter_title)

						regex_string = r"<title>(Chapter|Section|Part) {}: {}".format(chapter_number, regex.escape(chapter_title))
						if not regex.findall(regex_string, file_contents):
							messages.append(LintMessage(f"<title> element doesn’t match expected value; should be `Chapter {chapter_number}: {chapter_title}`. (Beware hidden Unicode characters!)", se.MESSAGE_TYPE_ERROR, filename))

					# Check for missing subtitle styling
					if "epub:type=\"subtitle\"" in file_contents and not local_css_has_subtitle_style:
						messages.append(LintMessage("Subtitles detected, but no subtitle style detected in local.css.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for whitespace before noteref
					matches = regex.findall(r"\s+<a href=\"endnotes\.xhtml#note-[0-9]+?\" id=\"noteref-[0-9]+?\" epub:type=\"noteref\">[0-9]+?</a>", file_contents)
					if matches:
						messages.append(LintMessage("Illegal white space before noteref.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for <li> elements that don't have a direct block child
					if filename != "toc.xhtml":
						matches = regex.findall(r"<li(?:\s[^>]*?>|>)\s*[^\s<]", file_contents)
						if matches:
							messages.append(LintMessage("<li> without direct block-level child.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for IDs on <h#> tags
					matches = regex.findall(r"<h[0-6][^>]*?id=[^>]*?>", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("<h#> element with id attribute. <h#> elements should be wrapped in <section> elements, which should hold the id attribute.", se.MESSAGE_TYPE_WARNING, filename, matches))

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
										messages.append(LintMessage(f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`", se.MESSAGE_TYPE_WARNING, filename))

							# No subtitle? Much more straightforward
							else:
								titlecased_title = se.formatting.remove_tags(se.formatting.titlecase(title))
								title = se.formatting.remove_tags(title)
								if title != titlecased_title:
									messages.append(LintMessage(f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`", se.MESSAGE_TYPE_WARNING, filename))

					# Check for <figure> tags without id attributes
					matches = regex.findall(r"<img[^>]*?id=\"[^>]+?>", file_contents)
					if matches:
						messages.append(LintMessage("<img> element with ID attribute. ID attributes go on parent <figure> elements.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for closing dialog without comma
					matches = regex.findall(r"[a-z]+?” [a-zA-Z]+? said", file_contents)
					if matches:
						messages.append(LintMessage("Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for non-typogrified img alt attributes
					matches = regex.findall(r"alt=\"[^\"]*?('|--|&quot;)[^\"]*?\"", file_contents)
					if matches:
						messages.append(LintMessage("Non-typogrified ', \" (as &quot;), or -- in image alt attribute.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check alt attributes not ending in punctuation
					if filename not in se.IGNORED_FILENAMES:
						matches = regex.findall(r"alt=\"[^\"]*?[a-zA-Z]\"", file_contents)
						if matches:
							messages.append(LintMessage("Alt attribute doesn’t appear to end with punctuation. Alt attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check alt attributes match image titles
					images = dom.select("img[src$=svg]")
					for image in images:
						alt_text = image["alt"]
						title_text = ""
						image_ref = image["src"].split("/").pop()
						try:
							with open(self.path / "src" / "epub" / "images" / image_ref, "r", encoding="utf-8") as image_source:
								try:
									title_text = BeautifulSoup(image_source, "lxml").title.get_text()
								except Exception:
									messages.append(LintMessage(f"{image_ref} missing <title> element.", se.MESSAGE_TYPE_ERROR, image_ref))
							if title_text != "" and alt_text != "" and title_text != alt_text:
								messages.append(LintMessage(f"The <title> of {image_ref} doesn’t match the alt text in {filename}", se.MESSAGE_TYPE_ERROR, filename))
						except FileNotFoundError:
							messages.append(LintMessage(f"The image {image_ref} doesn’t exist", se.MESSAGE_TYPE_ERROR, filename))

					# Check for punctuation after endnotes
					regex_string = fr"<a[^>]*?epub:type=\"noteref\"[^>]*?>[0-9]+</a>[^\s<–\]\)—{se.WORD_JOINER}]"
					matches = regex.findall(regex_string, file_contents)
					if matches:
						messages.append(LintMessage("Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for nbsp in measurements, for example: 90 mm
					matches = regex.findall(r"[0-9]+[\- ][mck][mgl]\b", file_contents)
					if matches:
						messages.append(LintMessage("Measurements must be separated by a no-break space, not a dash or regular space.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for line breaks after <br/> tags
					matches = regex.findall(r"<br\s*?/>[^\n]", file_contents)
					if matches:
						messages.append(LintMessage("<br/> element must be followed by a newline, and subsequent content must be indented to the same level.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <pre> tags
					if "<pre" in file_contents:
						messages.append(LintMessage("Illegal <pre> element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
					matches = regex.findall(r"\b.+?”[,\.]", file_contents)
					if matches:
						messages.append(LintMessage("Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for double spacing
					regex_string = fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}"
					matches = regex.findall(regex_string, file_contents)
					if matches:
						messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)", se.MESSAGE_TYPE_ERROR, filename))

					# Run some checks on epub:type values
					incorrect_attrs = []
					epub_type_attrs = regex.findall("epub:type=\"([^\"]+?)\"", file_contents)
					for attrs in epub_type_attrs:
						for attr in regex.split(r"\s", attrs):
							# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
							matches = regex.findall(r"^se:[a-z]+:(?:[a-z]+:?)*", attr)
							if matches:
								messages.append(LintMessage(f"Illegal colon (:) detected in SE identifier. SE identifiers are separated by dots (.) not colons (:). E.g., `se:name.vessel.ship`", se.MESSAGE_TYPE_ERROR, filename, matches))

							# Did someone use periods instead of colons for the SE namespace? e.g. se.name.vessel.ship
							matches = regex.findall(r"^se\.[a-z]+(?:\.[a-z]+)*", attr)
							if matches:
								messages.append(LintMessage(f"SE namespace must be followed by a colon (:), not a dot (.). E.g., `se:name.vessel`", se.MESSAGE_TYPE_ERROR, filename, matches))

							# Did we draw from the z3998 vocabulary when the item exists in the epub vocabulary?
							if attr.startswith("z3998:"):
								bare_attr = attr.replace("z3998:", "")
								if bare_attr in EPUB_SEMANTIC_VOCABULARY:
									incorrect_attrs.append((attr, bare_attr))

					# Convert this into a unique set so we don't spam the console with repetitive messages
					unique_incorrect_attrs = set(incorrect_attrs)
					for (attr, bare_attr) in unique_incorrect_attrs:
						messages.append(LintMessage(f"`{attr}` semantic used, but `{bare_attr}` is in the EPUB semantic inflection vocabulary.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for leftover asterisms
					matches = regex.findall(r"<[a-z]+[^>]*?>\s*\*\s*(\*\s*)+", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("Illegal asterism (***) detected. Section/scene breaks must be defined by an <hr/> element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for space before endnote backlinks
					if filename == "endnotes.xhtml":
						# Do we have to replace Ibid.?
						matches = regex.findall(r"\bibid\b", file_contents, flags=regex.IGNORECASE)
						if matches:
							messages.append(LintMessage("Illegal `Ibid` in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing `Ibid` refers to.", se.MESSAGE_TYPE_ERROR, filename))

						endnote_referrers = dom.select("li[id^=note-] a")
						bad_referrers = []

						for referrer in endnote_referrers:
							# We check against the attr value here because I couldn't figure out how to select an XML-namespaced attribute using BS4
							if "epub:type" in referrer.attrs and referrer.attrs["epub:type"] == "backlink":
								is_first_sib = True
								for sib in referrer.previous_siblings:
									if is_first_sib:
										is_first_sib = False
										if isinstance(sib, NavigableString):
											if sib == "\n": # Referrer preceded by newline. Check if all previous sibs are tags.
												continue
											if sib == " " or str(sib) == se.NO_BREAK_SPACE or regex.search(r"[^\s] $", str(sib)): # Referrer preceded by a single space; we're OK
												break
											# Referrer preceded by a string that is not a newline and does not end with a single space
											bad_referrers.append(referrer)
											break
									else:
										# We got here because the first sib was a newline, or not a string. So, check all previous sibs.
										if isinstance(sib, NavigableString) and sib != "\n":
											bad_referrers.append(referrer)
											break

						if bad_referrers:
							messages.append(LintMessage("Endnote referrer link not preceded by exactly one space, or a newline if all previous siblings are elements.", se.MESSAGE_TYPE_WARNING, filename, [str(referrer) for referrer in bad_referrers]))

					# If we're in the imprint, are the sources represented correctly?
					# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
					if filename == "imprint.xhtml":
						matches = regex.findall(r"<dc:source>([^<]+?)</dc:source>", metadata_xhtml)
						if len(matches) <= 2:
							for link in matches:
								if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
									messages.append(LintMessage(f"Source not represented in imprint.xhtml. Expected: <a href=\"{link}\">Project Gutenberg</a>", se.MESSAGE_TYPE_WARNING, filename))

								if "hathitrust.org" in link and f"the <a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
									messages.append(LintMessage(f"Source not represented in imprint.xhtml. Expected: the <a href=\"{link}\">HathiTrust Digital Library</a>", se.MESSAGE_TYPE_WARNING, filename))

								if "archive.org" in link and f"the <a href=\"{link}\">Internet Archive</a>" not in file_contents:
									messages.append(LintMessage(f"Source not represented in imprint.xhtml. Expected: the <a href=\"{link}\">Internet Archive</a>", se.MESSAGE_TYPE_WARNING, filename))

								if "books.google.com" in link and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
									messages.append(LintMessage(f"Source not represented in imprint.xhtml. Expected: <a href=\"{link}\">Google Books</a>", se.MESSAGE_TYPE_WARNING, filename))

					# Collect abbr elements for later check
					result = regex.findall("<abbr[^<]+?>", file_contents)
					result = [item.replace("eoc", "").replace(" \"", "").strip() for item in result]
					abbr_elements = list(set(result + abbr_elements))

					# Check if language tags in individual files match the language in content.opf
					if filename not in se.IGNORED_FILENAMES:
						file_language = regex.search(r"<html[^<]+xml\:lang=\"([^\"]+)\"", file_contents).group(1)
						if language != file_language:
							messages.append(LintMessage(f"File language is {file_language}, but content.opf language is {language}", se.MESSAGE_TYPE_ERROR, filename))

					# Check LoI descriptions to see if they match associated figcaptions
					if filename == "loi.xhtml":
						illustrations = dom.select("li > a")
						for illustration in illustrations:
							figure_ref = illustration["href"].split("#")[1]
							chapter_ref = regex.findall(r"(.*?)#.*", illustration["href"])[0]
							figcaption_text = ""
							loi_text = illustration.get_text()

							with open(self.path / "src" / "epub" / "text" / chapter_ref, "r", encoding="utf-8") as chapter:
								try:
									figure = BeautifulSoup(chapter, "lxml").select("#" + figure_ref)[0]
								except Exception:
									messages.append(LintMessage(f"#{figure_ref} not found in file {chapter_ref}", se.MESSAGE_TYPE_ERROR, 'loi.xhtml'))
									continue

								if figure.img:
									figure_img_alt = figure.img.get('alt')

								if figure.figcaption:
									figcaption_text = figure.figcaption.get_text()
							if (figcaption_text != "" and loi_text != "" and figcaption_text != loi_text) and (figure_img_alt != "" and loi_text != "" and figure_img_alt != loi_text):
								messages.append(LintMessage(f"The <figcaption> element of {figure_ref} doesn’t match the text in its LoI entry", se.MESSAGE_TYPE_WARNING, chapter_ref))

				# Check for missing MARC relators
				if filename == "introduction.xhtml" and ">aui<" not in metadata_xhtml and ">win<" not in metadata_xhtml:
					messages.append(LintMessage("introduction.xhtml found, but no MARC relator `aui` (Author of introduction, but not the chief author) or `win` (Writer of introduction)", se.MESSAGE_TYPE_WARNING, filename))

				if filename == "preface.xhtml" and ">wpr<" not in metadata_xhtml:
					messages.append(LintMessage("preface.xhtml found, but no MARC relator `wpr` (Writer of preface)", se.MESSAGE_TYPE_WARNING, filename))

				if filename == "afterword.xhtml" and ">aft<" not in metadata_xhtml:
					messages.append(LintMessage("afterword.xhtml found, but no MARC relator `aft` (Author of colophon, afterword, etc.)", se.MESSAGE_TYPE_WARNING, filename))

				if filename == "endnotes.xhtml" and ">ann<" not in metadata_xhtml:
					messages.append(LintMessage("endnotes.xhtml found, but no MARC relator `ann` (Annotator)", se.MESSAGE_TYPE_WARNING, filename))

				if filename == "loi.xhtml" and ">ill<" not in metadata_xhtml:
					messages.append(LintMessage("loi.xhtml found, but no MARC relator `ill` (Illustrator)", se.MESSAGE_TYPE_WARNING, filename))

				# Check for wrong semantics in frontmatter/backmatter
				if filename in se.FRONTMATTER_FILENAMES and "frontmatter" not in file_contents:
					messages.append(LintMessage("No frontmatter semantic inflection for what looks like a frontmatter file", se.MESSAGE_TYPE_WARNING, filename))

				if filename in se.BACKMATTER_FILENAMES and "backmatter" not in file_contents:
					messages.append(LintMessage("No backmatter semantic inflection for what looks like a backmatter file", se.MESSAGE_TYPE_WARNING, filename))

	if cover_svg_title != titlepage_svg_title:
		messages.append(LintMessage("cover.svg and titlepage.svg <title> elements don’t match", se.MESSAGE_TYPE_ERROR))

	if has_frontmatter and not has_halftitle:
		messages.append(LintMessage("Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	if not has_cover_source:
		messages.append(LintMessage("./images/cover.source.jpg not found", se.MESSAGE_TYPE_ERROR, "cover.source.jpg"))

	single_use_css_classes = []

	for css_class in xhtml_css_classes:
		if css_class not in se.IGNORED_CLASSES:
			if "." + css_class not in css:
				messages.append(LintMessage(f"class `{css_class}` found in xhtml, but no style in local.css", se.MESSAGE_TYPE_ERROR, "local.css"))

		if xhtml_css_classes[css_class] == 1 and css_class not in se.IGNORED_CLASSES and not regex.match(r"^i[0-9]$", css_class):
			# Don't count ignored classes OR i[0-9] which are used for poetry styling
			single_use_css_classes.append(css_class)

	if single_use_css_classes:
		messages.append(LintMessage("CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks.", se.MESSAGE_TYPE_WARNING, "local.css", single_use_css_classes))

	headings = list(set(headings))
	with open(self.path / "src" / "epub" / "toc.xhtml", "r", encoding="utf-8") as file:
		toc = BeautifulSoup(file.read(), "lxml")
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
				messages.append(LintMessage(f"Heading `{heading[0]}` found, but not present for that file in the ToC.", se.MESSAGE_TYPE_ERROR, heading[1]))

		# Check our ordered ToC entries against the spine
		# To cover all possibilities, we combine the toc and the landmarks to get the full set of entries
		with open(self.path / "src" / "epub" / "content.opf", "r", encoding="utf-8") as content_opf:
			toc_files = []
			for index, entry in enumerate(landmarks.find_all("a", attrs={"epub:type": regex.compile("^.*(frontmatter|bodymatter).*$")})):
				entry_file = regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", entry.get("href"))
				toc_files.append(entry_file)
			for index, entry in enumerate(toc_entries):
				entry_file = regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", entry.get("href"))
				toc_files.append(entry_file)
			unique_toc_files: List[str] = []
			for toc_file in toc_files:
				if toc_file not in unique_toc_files:
					unique_toc_files.append(toc_file)
			toc_files = unique_toc_files
			spine_entries = BeautifulSoup(content_opf.read(), "lxml").find("spine").find_all("itemref")
			if len(toc_files) != len(spine_entries):
				messages.append(LintMessage("The number of elements in the spine ({}) does not match the number of elements in the ToC and landmarks ({}).".format(len(toc_files), len(spine_entries)), se.MESSAGE_TYPE_ERROR, "content.opf"))
			for index, entry in enumerate(spine_entries):
				if toc_files[index] != entry.attrs["idref"]:
					messages.append(LintMessage(f"The spine order does not match the order of the ToC and landmarks. Expected {entry.attrs['idref']}, found {toc_files[index]}.", se.MESSAGE_TYPE_ERROR, "content.opf"))
					break

	for element in abbr_elements:
		try:
			css_class = regex.search(r"class=\"([^\"]+?)\"", element).group(1)
		except Exception:
			continue
		if css_class and css_class in ("temperature", "era", "acronym") and "abbr." + css_class not in abbr_styles:
			messages.append(LintMessage(f"abbr.{css_class} element found, but no required style in local.css (See typgoraphy manual for style)", se.MESSAGE_TYPE_ERROR, "local.css"))

	return messages
