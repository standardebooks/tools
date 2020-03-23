#!/usr/bin/env python3
"""
Contains the LintMessage class and the Lint function, which is broken out of
the SeEpub class for readability and maintainability.

Strictly speaking, the lint() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

import filecmp
from fnmatch import translate
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
from natsort import natsorted
import se
import se.easy_xml
import se.formatting
import se.images


COLOPHON_VARIABLES = ["TITLE", "YEAR", "AUTHOR_WIKI_URL", "AUTHOR", "PRODUCER_URL", "PRODUCER", "PG_YEAR", "TRANSCRIBER_1", "TRANSCRIBER_2", "PG_URL", "IA_URL", "PAINTING", "ARTIST_WIKI_URL", "ARTIST"]
EPUB_SEMANTIC_VOCABULARY = ["cover", "frontmatter", "bodymatter", "backmatter", "volume", "part", "chapter", "division", "foreword", "preface", "prologue", "introduction", "preamble", "conclusion", "epilogue", "afterword", "epigraph", "toc", "landmarks", "loa", "loi", "lot", "lov", "appendix", "colophon", "index", "index-headnotes", "index-legend", "index-group", "index-entry-list", "index-entry", "index-term", "index-editor-note", "index-locator", "index-locator-list", "index-locator-range", "index-xref-preferred", "index-xref-related", "index-term-category", "index-term-categories", "glossary", "glossterm", "glossdef", "bibliography", "biblioentry", "titlepage", "halftitlepage", "copyright-page", "acknowledgments", "imprint", "imprimatur", "contributors", "other-credits", "errata", "dedication", "revision-history", "notice", "tip", "halftitle", "fulltitle", "covertitle", "title", "subtitle", "bridgehead", "learning-objective", "learning-resource", "assessment", "qna", "panel", "panel-group", "balloon", "text-area", "sound-area", "footnote", "endnote", "footnotes", "endnotes", "noteref", "keyword", "topic-sentence", "concluding-sentence", "pagebreak", "page-list", "table", "table-row", "table-cell", "list", "list-item", "figure", "aside"]

"""
LIST OF ALL SE LINT MESSAGES

CSS
"c-001", "Do not directly select `<h#>` elements, as they are used in template files; use more specific selectors."
"c-002", "Unused CSS selectors."
"c-003", "`[xml|attr]` selector in CSS, but no XML namespace declared (`@namespace xml \"http://www.w3.org/XML/1998/namespace\";`)."
"c-004", "Do not specify border colors, so that reading systems can adjust for night mode."
"c-005", "`abbr` selector does not need `white-space: nowrap;` as it inherits it from `core.css`."
"c-006", "Subtitles found, but no subtitle style found in `local.css`."
"c-007", f"`<abbr class=\"{css_class}\">` element found, but no required style in `local.css`. See the typography manual for required styls."
"c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks."

FILESYSTEM
"f-001", "Illegal file or directory."
"f-002", "Missing expected file or directory."
"f-003", f"File does not match `{license_file_path}`."
"f-004", f"File does not match `{core_css_file_path}`."
"f-005", f"File does not match `{logo_svg_file_path}`."
"f-006", f"File does not match `{uncopyright_file_path}`."
"f-007", f"File does not match `{gitignore_file_path}`."
"f-008", "Illegal uppercase letter in filename."
"f-009", "Illegal leading `0` in filename."
"f-010", "Problem decoding file as utf-8."
"f-011", "JPEG files must end in `.jpg`."
"f-012", "TIFF files must end in `.tif`."

METADATA
"m-001", "gutenberg.org URL missing leading `www.`."
"m-002", "archive.org URL should not have leading `www.`."
"m-003", "Non-https URL."
"m-004", "Non-canonical Google Books URL. Google Books URLs must look exactly like `https://books.google.com/books?id=<BOOK-ID>`."
"m-005", "Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like `https://catalog.hathitrust.org/Record/<BOOK-ID>`."
"m-006", "Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like `https://www.gutenberg.org/ebooks/<BOOK-ID>`."
"m-007", "Non-canonical archive.org URL. Internet Archive URLs must look exactly like `https://archive.org/details/<BOOK-ID>`."
"m-008", "id.loc.gov URL ending with illegal `.html`."
"m-009", f"GitHub repo URL does not match expected: `{self.generated_github_repo_url}`."
"m-010", "Illegal `se:url.vcs.github`. VCS URLs must begin with `https://github.com/standardebooks/`."
"m-011", "Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: `https://catalog.hathitrust.org/Record/<RECORD-ID>`."
"m-012", "Non-typogrified `\"`, `'`, or `--` in `<dc:title>` element."
"m-013", "Non-typogrified `\"`, `'`, or `--` in `<dc:description>` element."
"m-014", "Non-typogrified `\"`, `'`, or `--` in  long description."
"m-015", "Metadata long description is not valid HTML. LXML says: "
"m-016", "Long description must be escaped HTML."
"m-017", "`<![CDATA[` found. Run `se clean` to canonicalize `<![CDATA[` sections."
"m-018", "HTML entities found. Use Unicode equivalents instead."
"m-019", "Illegal em-dash in `dc:subject`; use `--`."
"m-020", "Illegal value for `<meta property="se:subject">` element."
"m-021", "No `<meta property=\"se:subject\">` element found."
"m-022", "Empty `<meta property=\"se:production-notes\">` element."
"m-023", f"`<dc:identifier>` does not match expected: `{self.generated_identifier}`."
"m-024", "`se:name.person.full-name` property identical to regular name. If the two are identical the full name `<meta>` element must be removed."
"m-025", "Translator found in metadata, but no `translated from LANG` block in colophon."
"m-026", f"Project Gutenberg source not present. Expected: `<a href=\"{link}\">Project Gutenberg</a>`."
"m-027", f"HathiTrust source not present. Expected: the `<a href=\"{link}\">HathiTrust Digital Library</a>`."
"m-028", f"Internet Archive source not present. Expected: the `<a href=\"{link}\">Internet Archive</a>`."
"m-029", f"Google Books source not present. Expected: `<a href=\"{link}\">Google Books</a>`."
"m-030", "`introduction.xhtml` found, but no MARC relator `aui` (Author of introduction, but not the chief author) or `win` (Writer of introduction)."
"m-031", "`preface.xhtml` found, but no MARC relator `wpr` (Writer of preface)."
"m-032", "`afterword.xhtml` found, but no MARC relator `aft` (Author of colophon, afterword, etc.)."
"m-033", "`endnotes.xhtml` found, but no MARC relator `ann` (Annotator)."
"m-034", "`loi.xhtml` found, but no MARC relator `ill` (Illustrator)."
"m-035", f"Unexpected SE identifier in colophon. Expected: `{self.generated_identifier}`."
"m-036", "Missing data in colophon."
"m-037", f"Source not represented in colophon.xhtml. Expected: `<a href=\"{link}\">Project Gutenberg</a>`."
"m-038", f"Source not represented in colophon.xhtml. Expected: `the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>`."
"m-039", f"Source not represented in colophon.xhtml. Expected: `the<br/> <a href=\"{link}\">Internet Archive</a>`."
"m-040", f"Source not represented in colophon.xhtml. Expected: `<a href=\"{link}\">Google Books</a>`."
"m-041", "`Hathi Trust` should be `HathiTrust`."
"m-042", "`<manifest>` does not match expected structure."
"m-043", f"The number of elements in the spine ({len(toc_files)}) does not match the number of elements in the ToC and landmarks ({len(spine_entries)})."
"m-044", f"The spine order does not match the order of the ToC and landmarks. Expected `{entry.attrs['idref']}`, found `{toc_files[index]}`."
"m-045", f"Heading `{heading[0]}` found, but not present for that file in the ToC."
"m-046", "Missing or empty `<reason>` element."
"m-047", "Ignoring `*` is too general. Target specific files if possible."
"m-048", "Unused se-lint-ignore.xml rule."
"m-049", "No se-lint-ignore.xml rules. Delete the file if there are no rules."

SEMANTICS & CONTENT
"s-001", "Illegal numeric entity (like `&#913;`)."
"s-002", "Lowercase letters in cover. Cover text must be all uppercase."
"s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except `translated by` and `illustrated by`."
"s-004", "Empty `<title>` element."
"s-005", "Nested `<blockquote>` element."
"s-006", "Poetry or verse included without `<span>` element."
"s-007", "`<li>` element without direct block-level child."
"s-008", "`<br/>` element found before closing `</p>` tag."
"s-009", "`<h2>` element without `epub:type=\"title\"` attribute."
"s-010", "Empty `<p>` element. Use `<hr/>` for thematic breaks if appropriate."
"s-011", "`<section>` element without `id` attribute."
"s-012", "Illegal `<hr/>` before the end of a section."
"s-013", "Illegal `<pre>` element."
"s-014", "`<br/>` after block-level element."
"s-015", f"`<{match.name}>` element has subtitle `<span>`, but first line is not wrapped in a `<span>`. See semantics manual for structure of headers with subtitles."
"s-016", "`<br/>` element must be followed by a newline, and subsequent content must be indented to the same level."
"s-017", F"`<m:mfenced>` is deprecated in the MathML spec. Use `<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>`."
"s-018", "`<img>` element with `id` attribute. `id` attributes go on parent `<figure>` elements."
"s-019", "`<h#>` element with `id` attribute. `<h#>` elements should be wrapped in `<section>` elements, which should hold the `id` attribute."
"s-020", "Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present."
"s-021", f"Unexpected value for `<title>` element. Expected: `{title}`. (Beware hidden Unicode characters!)"
"s-022", f"The `<title>` element of `{image_ref}` does not match the alt text in `{filename}`."
"s-023", f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`."
"s-023", f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`."
"s-024", "Half title `<title>` elements must contain exactly: \"Half Title\"."
"s-025", "Titlepage `<title>` elements must contain exactly: `Titlepage`."
"s-026", "Illegal Roman numeral in `<title>` element; use Arabic numbers."
"s-027", f"{image_ref} missing `<title>` element."
"s-028", "`cover.svg` and `titlepage.svg` `<title>` elements do not match."
"s-029", "If a `<span>` exists only for the `z3998:roman` semantic, then `z3998:roman` should be pulled into parent element instead."
"s-030", "`z3998:nonfiction` should be `z3998:non-fiction`."
"s-031", "Illegal colon (`:`) in SE identifier. SE identifiers are separated by dots, not colons. E.g., `se:name.vessel.ship`."
"s-032", "SE namespace must be followed by a colon (`:`), not a dot. E.g., `se:name.vessel`."
"s-033", f"File language is `{file_language}`, but `content.opf` language is `{language}`."
"s-034", f"`{attr}` semantic used, but `{bare_attr}` is in the EPUB semantic inflection vocabulary."
"s-035", "`<h#>` element has the `z3998:roman` semantic, but is not a Roman numeral."
"s-036", "No `frontmatter` semantic inflection for what looks like a frontmatter file."
"s-037", "No `backmatter` semantic inflection for what looks like a backmatter file."
"s-038", "Illegal asterism (`***`). Section/scene breaks must be defined by an `<hr/>` element."
"s-039", "Illegal `Ibid` in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing `Ibid` refers to."
"s-040", f"`#{figure_ref}` not found in file `{chapter_ref}`."
"s-041", f"The `<figcaption>` element of `#{figure_ref}` does not match the text in its LoI entry."
"s-042", "`<table>` element without `<tbody>` child."
"s-043", "Poem included without styling in `local.css`."
"s-044", "Verse included without styling in `local.css`."
"s-045", "Song included without styling in `local.css`."
"s-046", "`noteref` as a direct child of poetry or verse. `noteref`s should be in their parent `<span>`."

TYPOGRAPHY
"t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)"
"t-002", "Comma or period outside of double quote. Generally punctuation should go within single and double quotes."
"t-002", "Comma or period outside of double quote. Generally punctuation should go within single and double quotes."
"t-003", "`“` missing matching `”`."
"t-004", "`‘` missing matching `’`."
"t-005", "Dialog without ending comma."
"t-007", "Required no-break space not found before `&amp;`."
"t-008", "Required no-break space not found after `&amp;`."
"t-009", "Required no-break space not found before `<abbr class=\"time\">`."
"t-010", "Times must be separated by colons (`:`) not periods (`.`)."
"t-011", "Missing punctuation before closing quotes."
"t-012", "Illegal white space before noteref."
"t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period."
"t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash."
"t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals."
"t-016", "Initials in `<abbr class=\"name\">` not separated by spaces."
"t-017", "Ending punctuation inside italics."
"t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction."
"t-019", "When a complete clause is italicized, ending punctuation except commas must be within containing italics."
"t-020", "Endnote links must be outside of punctuation, including quotation marks."
"t-021", "Measurements must be separated by a no-break space, not a dash or regular space."
"t-022", "No-break space found in `<abbr class=\"name\">`. This is redundant."
"t-023", "Comma inside `<i>` element before closing dialog."
"t-024", "When italicizing language in dialog, italics go inside quotation marks."
"t-025", "Non-typogrified `'`, `\"` (as `&quot;`), or `--` in image `alt` attribute."
"t-026", "`alt` attribute does not appear to end with punctuation. `alt` attributes must be composed of complete sentences ending in appropriate punctuation."
"t-027", "Endnote referrer link not preceded by exactly one space, or a newline if all previous siblings are elements."
"t-028", "Possible mis-curled quotation mark."

XHTML
"x-001", "String `UTF-8` must always be lowercase."
"x-002", "Uppercase in attribute value. Attribute values must be all lowercase."
"x-003", "Illegal `transform` attribute. SVGs should be optimized to remove use of `transform`. Try using Inkscape to save as an “optimized SVG”."
"x-004", "Illegal `style=\"fill: #000\"` or `fill=\"#000\"`."
"x-005", "Illegal height or width on root `<svg>` element. Size SVGs using the `viewBox` attribute only."
"x-006", f"`{match}` found instead of `viewBox`. `viewBox` must be correctly capitalized."
"x-007", "`id` attributes starting with a number are illegal XHTML."
"x-008", "Elements should end with a single `>`."
"x-009", "Illegal leading 0 in `id` attribute."
"x-010", "Illegal element in `<title>` element."
"x-011", "Uppercased HTML tag."
"x-012", "Illegal `style` attribute. Do not use inline styles, any element can be targeted with a clever enough selector."
"x-013", "CSS class found in XHTML, but not in `local.css`."
"""

class LintMessage:
	"""
	An object representing an output message for the lint function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	def __init__(self, code: str, text: str, message_type=se.MESSAGE_TYPE_WARNING, filename: str = "", submessages: List[str] = None):
		self.code = code
		self.text = text.strip()
		self.filename = filename
		self.message_type = message_type
		self.submessages = submessages

def _get_malformed_urls(xhtml: str, filename: str) -> list:
	"""
	Helper function used in self.lint()
	Get a list of URLs in the epub that do not match SE standards.

	INPUTS
	xhtml: A string of XHTML to check

	OUTPUTS
	A list of LintMessages representing any malformed URLs in the XHTML string
	"""

	messages = []

	# Check for non-https URLs
	matches = regex.findall(r"(?<!www\.)gutenberg\.org[^\"<\s]*", xhtml)
	if matches:
		messages.append(LintMessage("m-001", "gutenberg.org URL missing leading `www.`.", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"www\.archive\.org[^\"<\s]*", xhtml)
	if matches:
		messages.append(LintMessage("m-002", "archive.org URL should not have leading `www.`.", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"http://(?:gutenberg\.org|archive\.org|pgdp\.net|catalog\.hathitrust\.org|en\.wikipedia\.org)[^\"<\s]*", xhtml)
	if matches:
		messages.append(LintMessage("m-003", "Non-https URL.", se.MESSAGE_TYPE_ERROR, filename, matches))

	# Check for malformed canonical URLs
	if regex.search(r"books\.google\.com/books\?id=.+?[&#]", xhtml):
		messages.append(LintMessage("m-004", "Non-canonical Google Books URL. Google Books URLs must look exactly like `https://books.google.com/books?id=<BOOK-ID>`.", se.MESSAGE_TYPE_ERROR, filename))

	if "babel.hathitrust.org" in xhtml:
		messages.append(LintMessage("m-005", "Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like `https://catalog.hathitrust.org/Record/<BOOK-ID>`.", se.MESSAGE_TYPE_ERROR, filename))

	if ".gutenberg.org/files/" in xhtml:
		messages.append(LintMessage("m-006", "Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like `https://www.gutenberg.org/ebooks/<BOOK-ID>`.", se.MESSAGE_TYPE_ERROR, filename))

	if "archive.org/stream" in xhtml:
		messages.append(LintMessage("m-007", "Non-canonical archive.org URL. Internet Archive URLs must look exactly like `https://archive.org/details/<BOOK-ID>`.", se.MESSAGE_TYPE_ERROR, filename))

	return messages

def lint(self, metadata_xhtml: str, skip_lint_ignore: bool) -> list:
	"""
	Check this ebook for some common SE style errors.

	INPUTS
	None

	OUTPUTS
	A list of LintMessage objects.
	"""

	messages: List[LintMessage] = []
	has_halftitle = False
	has_frontmatter = False
	has_cover_source = False
	cover_svg_title = ""
	titlepage_svg_title = ""
	xhtml_css_classes: Dict[str, int] = {}
	headings: List[tuple] = []
	double_spaced_files: List[str] = []
	unused_selectors: List[str] = []

	# This is a dict with where keys are the path and values are a list of code dicts.
	# Each code dict has a key "code" which is the actual code, and a key "used" which is a
	# bool indicating whether or not the code has actually been caught in the linting run.
	ignored_codes: Dict[str, List[Dict]] = {}

	# First, check if we have an se-lint-ignore.xml file in the ebook root. If so, parse it.
	# This is an example se-lint-ignore.xml file. File paths support shell-style globbing. <reason> is required.
	# <?xml version="1.0" encoding="utf-8"?>
	# <se-lint-ignore>
	# 	<file path="chapter-6.xhtml">
	# 		<ignore>
	# 			<code>t-007</code>
	# 			<reason>The ampersand is part of prose in a letter written in the character's distinct style.</reason>
	# 		</ignore>
	# 		<ignore>
	# 			<code>t-008</code>
	# 			<reason>The ampersand is part of prose in a letter written in the character's distinct style.</reason>
	# 		</ignore>
	# 	</file>
	# 	<file path="preface-*.xhtml">
	# 		<ignore>
	# 			<code>t-011</code>
	# 			<reason>The quotes are in headlines that lack punctuation on purpose.</reason>
	# 		</ignore>
	# 	</file>
	# </se-lint-ignore>
	if not skip_lint_ignore:
		try:
			with open(self.path / "se-lint-ignore.xml", "r", encoding="utf-8") as file:
				lint_config = se.easy_xml.EasyXmlTree(file.read())

			elements = lint_config.xpath("//se-lint-ignore/file")

			if not elements:
				messages.append(LintMessage("m-049", "No se-lint-ignore.xml rules. Delete the file if there are no rules.", se.MESSAGE_TYPE_ERROR, "se-lint-ignore.xml"))

			has_illegal_path = False

			for element in elements:
				path = element.attribute("path").strip()

				if path == "*":
					has_illegal_path = True # Set a bool so that we set a lint error later, to prevent adding it multiple times

				if path not in ignored_codes:
					ignored_codes[path] = []

				for ignore in element.lxml_element:
					if ignore.tag == "ignore":
						has_reason = False
						for child in ignore:
							if child.tag == "code":
								ignored_codes[path].append({"code": child.text.strip(), "used": False})

							if child.tag == "reason" and child.text.strip() != "":
								has_reason = True

						if not has_reason:
							messages.append(LintMessage("m-046", "Missing or empty `<reason>` element.", se.MESSAGE_TYPE_ERROR, "se-lint-ignore.xml"))

			if has_illegal_path:
				messages.append(LintMessage("m-047", "Ignoring `*` is too general. Target specific files if possible.", se.MESSAGE_TYPE_WARNING, "se-lint-ignore.xml"))

		except FileNotFoundError as ex:
			pass
		except se.InvalidXhtmlException as ex:
			raise ex
		except Exception as ex:
			raise se.InvalidXhtmlException("Couldn’t parse `se-lint-ignore.xml` file.")

	# Done parsing ignore list

	# Get the ebook language, for later use
	language = regex.search(r"<dc:language>([^>]+?)</dc:language>", metadata_xhtml).group(1)

	# Check local.css for various items, for later use
	abbr_elements: List[str] = []
	try:
		with open(self.path / "src" / "epub" / "css" / "local.css", "r", encoding="utf-8") as file:
			self.local_css = file.read()

			local_css_has_subtitle_style = "span[epub|type~=\"subtitle\"]" in self.local_css

			local_css_has_poem_style = "z3998:poem" in self.local_css
			local_css_has_verse_style = "z3998:verse" in self.local_css
			local_css_has_song_style = "z3998:song" in self.local_css

			abbr_styles = regex.findall(r"abbr\.[a-z]+", self.local_css)

			matches = regex.findall(r"^h[0-6]\s*,?{?", self.local_css, flags=regex.MULTILINE)
			if matches:
				messages.append(LintMessage("c-001", "Do not directly select `<h#>` elements, as they are used in template files; use more specific selectors.", se.MESSAGE_TYPE_ERROR, "local.css"))
	except Exception:
		raise se.InvalidSeEbookException(f"Couldn’t open `{self.path / 'src' / 'epub' / 'css' / 'local.css'}`.")

	root_files = os.listdir(self.path)
	expected_root_files = [".git", "images", "src", "LICENSE.md"]
	illegal_files = [x for x in root_files if x not in expected_root_files and x != ".gitignore" and x != "se-lint-ignore.xml"] # .gitignore and se-lint-ignore.xml are optional
	missing_files = [x for x in expected_root_files if x not in root_files and x != "LICENSE.md"] # We add more to this later on. LICENSE.md gets checked later on, so we don't want to add it twice

	for illegal_file in illegal_files:
		messages.append(LintMessage("f-001", "Illegal file or directory.", se.MESSAGE_TYPE_ERROR, illegal_file))

	# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
	if regex.search(r"#description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", metadata_xhtml.replace("\"&gt;", "").replace("=\"", "")) is not None:
		messages.append(LintMessage("m-014", "Non-typogrified `\"`, `'`, or `--` in long description.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check if there are non-typogrified quotes or em-dashes in the title.
	# The open-ended start and end of the regex also catches title-sort
	if regex.search(r"title\">[^<]+?(['\"]|\-\-)[^<]+?<", metadata_xhtml) is not None:
		messages.append(LintMessage("m-012", "Non-typogrified `\"`, `'`, or `--` in `<dc:title>` element.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	if regex.search(r"<dc:description id=\"description\">[^<]+?(['\"]|\-\-)[^<]+?</dc:description>", metadata_xhtml) is not None:
		messages.append(LintMessage("m-013", "Non-typogrified `\"`, `'`, or `--` in `<dc:description>` element.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for malformed long description HTML
	long_description = regex.findall(r"<meta id=\"long-description\".+?>(.+?)</meta>", metadata_xhtml, flags=regex.DOTALL)
	if long_description:
		long_description = f"<?xml version=\"1.0\"?><html xmlns=\"http://www.w3.org/1999/xhtml\">{html.unescape(long_description[0])}</html>"
		try:
			etree.parse(io.StringIO(long_description))
		except lxml.etree.XMLSyntaxError as ex:
			messages.append(LintMessage("m-015", f"Metadata long description is not valid HTML. LXML says: {ex}", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for double spacing
	regex_string = fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}"
	matches = regex.findall(regex_string, metadata_xhtml)
	if matches:
		double_spaced_files.append("content.opf")

	# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
	matches = regex.findall(r"[a-zA-Z][”][,\.]", metadata_xhtml)
	if matches:
		messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, "content.opf"))

	# Make sure long-description is escaped HTML
	if "<meta id=\"long-description\" property=\"se:long-description\" refines=\"#description\">\n\t\t\t&lt;p&gt;" not in metadata_xhtml:
		messages.append(LintMessage("m-016", "Long description must be escaped HTML.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for HTML entities in long-description, but allow &amp;amp;
	if regex.search(r"&amp;[a-z]+?;", metadata_xhtml.replace("&amp;amp;", "")):
		messages.append(LintMessage("m-018", "HTML entities found. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal em-dashes in <dc:subject>
	if regex.search(r"<dc:subject id=\"[^\"]+?\">[^<]+?—[^<]+?</dc:subject>", metadata_xhtml) is not None:
		messages.append(LintMessage("m-019", "Illegal em-dash in `dc:subject`; use `--`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for empty production notes
	if "<meta property=\"se:production-notes\">Any special notes about the production of this ebook for future editors/producers? Remove this element if not.</meta>" in metadata_xhtml:
		messages.append(LintMessage("m-022", "Empty `<meta property=\"se:production-notes\">` element.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal VCS URLs
	matches = regex.findall(r"<meta property=\"se:url\.vcs\.github\">([^<]+?)</meta>", metadata_xhtml)
	if matches:
		for match in matches:
			if not match.startswith("https://github.com/standardebooks/"):
				messages.append(LintMessage("m-010", "Illegal `se:url.vcs.github`. VCS URLs must begin with `https://github.com/standardebooks/`.", se.MESSAGE_TYPE_ERROR, "content.opf", list(match)))

	# Check for HathiTrust scan URLs instead of actual record URLs
	if "babel.hathitrust.org" in metadata_xhtml or "hdl.handle.net" in metadata_xhtml:
		messages.append(LintMessage("m-011", "Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: `https://catalog.hathitrust.org/Record/<RECORD-ID>`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal se:subject tags
	illegal_subjects = []
	matches = regex.findall(r"<meta property=\"se:subject\">([^<]+?)</meta>", metadata_xhtml)
	if matches:
		for match in matches:
			if match not in se.SE_GENRES:
				illegal_subjects.append(match)

		if illegal_subjects:
			messages.append(LintMessage("m-020", "Illegal value for `<meta property=\"se:subject\">` element.", se.MESSAGE_TYPE_ERROR, "content.opf", illegal_subjects))
	else:
		messages.append(LintMessage("m-021", "No `<meta property=\"se:subject\">` element found.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for CDATA tags
	if "<![CDATA[" in metadata_xhtml:
		messages.append(LintMessage("m-017", "`<![CDATA[` found. Run `se clean` to canonicalize `<![CDATA[` sections.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check that our provided identifier matches the generated identifier
	identifier = regex.sub(r"<.+?>", "", regex.findall(r"<dc:identifier id=\"uid\">.+?</dc:identifier>", metadata_xhtml)[0])
	if identifier != self.generated_identifier:
		messages.append(LintMessage("m-023", f"`<dc:identifier>` does not match expected: `{self.generated_identifier}`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check that the GitHub repo URL is as expected
	if f"<meta property=\"se:url.vcs.github\">{self.generated_github_repo_url}</meta>" not in metadata_xhtml:
		messages.append(LintMessage("m-009", f"GitHub repo URL does not match expected: `{self.generated_github_repo_url}`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check if se:name.person.full-name matches their titlepage name
	matches = regex.findall(r"<meta property=\"se:name\.person\.full-name\" refines=\"#([^\"]+?)\">([^<]*?)</meta>", metadata_xhtml)
	duplicate_names = []
	for match in matches:
		name_matches = regex.findall(fr"<([a-z:]+)[^<]+?id=\"{match[0]}\"[^<]*?>([^<]*?)</\1>", metadata_xhtml)
		for name_match in name_matches:
			if name_match[1] == match[1]:
				duplicate_names.append(name_match[1])

	if duplicate_names:
		messages.append(LintMessage("m-024", "`se:name.person.full-name` property identical to regular name. If the two are identical the full name `<meta>` element must be removed.", se.MESSAGE_TYPE_ERROR, "content.opf", duplicate_names))

	# Check for malformed URLs
	messages = messages + _get_malformed_urls(metadata_xhtml, "content.opf")

	if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", metadata_xhtml):
		messages.append(LintMessage("m-008", "id.loc.gov URL ending with illegal `.html`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Does the manifest match the generated manifest?
	for manifest in regex.findall(r"<manifest>.*?</manifest>", metadata_xhtml, flags=regex.DOTALL):
		manifest = regex.sub(r"[\n\t]", "", manifest)
		expected_manifest = regex.sub(r"[\n\t]", "", self.generate_manifest())

		if manifest != expected_manifest:
			messages.append(LintMessage("m-042", "`<manifest>` element does not match expected structure.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Make sure some static files are unchanged
	try:
		with importlib_resources.path("se.data.templates", "LICENSE.md") as license_file_path:
			if not filecmp.cmp(license_file_path, self.path / "LICENSE.md"):
				messages.append(LintMessage("f-003", f"File does not match `{license_file_path}`.", se.MESSAGE_TYPE_ERROR, "LICENSE.md"))
	except Exception:
		missing_files.append("LICENSE.md")

	try:
		with importlib_resources.path("se.data.templates", "core.css") as core_css_file_path:
			if not filecmp.cmp(core_css_file_path, self.path / "src" / "epub" / "css" / "core.css"):
				messages.append(LintMessage("f-004", f"File does not match `{core_css_file_path}`.", se.MESSAGE_TYPE_ERROR, "core.css"))
	except Exception:
		missing_files.append(str(Path("src/epub/css/core.css")))

	try:
		with importlib_resources.path("se.data.templates", "logo.svg") as logo_svg_file_path:
			if not filecmp.cmp(logo_svg_file_path, self.path / "src" / "epub" / "images" / "logo.svg"):
				messages.append(LintMessage("f-005", f"File does not match `{logo_svg_file_path}`.", se.MESSAGE_TYPE_ERROR, "logo.svg"))
	except Exception:
		missing_files.append(str(Path("src/epub/images/logo.svg")))

	try:
		with importlib_resources.path("se.data.templates", "uncopyright.xhtml") as uncopyright_file_path:
			if not filecmp.cmp(uncopyright_file_path, self.path / "src" / "epub" / "text" / "uncopyright.xhtml"):
				messages.append(LintMessage("f-006", f"File does not match `{uncopyright_file_path}`.", se.MESSAGE_TYPE_ERROR, "uncopyright.xhtml"))
	except Exception:
		missing_files.append(str(Path("src/epub/text/uncopyright.xhtml")))

	# Construct a set of CSS selectors in local.css
	# We'll check against this set in each file to see if any of them are unused.

	# Remove @supports directives, as the parser can't handle them
	unused_selector_css = regex.sub(r"^@supports\(.+?\){(.+?)}\s*}", "\\1}", self.local_css, flags=regex.MULTILINE | regex.DOTALL)

	# Remove actual content of css selectors
	unused_selector_css = regex.sub(r"{[^}]+}", "", unused_selector_css)

	# Remove trailing commas
	unused_selector_css = regex.sub(r",", "", unused_selector_css)

	# Remove pseudo-elements like ::before; we are interested in the *selectors* of pseudo elements, not the
	# elements themselves
	unused_selector_css = regex.sub(r"::[a-z\-]+", "", unused_selector_css)

	# Remove comments
	unused_selector_css = regex.sub(r"/\*.+?\*/", "", unused_selector_css, flags=regex.DOTALL)

	# Remove @ defines
	unused_selector_css = regex.sub(r"^@.+", "", unused_selector_css, flags=regex.MULTILINE)

	# Construct a set of selectors
	local_css_selectors = list({line.strip() for line in unused_selector_css.splitlines() if line != ""})
	unused_selectors = local_css_selectors.copy()
	# Done creating our list of selectors.

	# Now iterate over individual files for some checks
	for root, _, filenames in os.walk(self.path):
		for filename in natsorted(filenames):
			if ".git" in str(Path(root) / filename):
				continue

			if ".jpeg" in filename:
				messages.append(LintMessage("f-011", "JPEG files must end in `.jpg`.", se.MESSAGE_TYPE_ERROR, filename))

			if ".tiff" in filename:
				messages.append(LintMessage("f-012", "TIFF files must end in `.tif`.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.startswith("cover.source."):
				has_cover_source = True

			if filename != "LICENSE.md" and regex.findall(r"[A-Z]", filename):
				messages.append(LintMessage("f-008", "Illegal uppercase letter in filename.", se.MESSAGE_TYPE_ERROR, filename))

			if "-0" in filename:
				messages.append(LintMessage("f-009", "Illegal leading `0` in filename.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.endswith(tuple(se.BINARY_EXTENSIONS)) or filename.endswith("core.css"):
				continue

			if filename == ".gitignore":
				# .gitignore is optional, because our standard gitignore ignores itself.
				# So if it's present, it must match our template.
				with importlib_resources.path("se.data.templates", "gitignore") as gitignore_file_path:
					if not filecmp.cmp(gitignore_file_path, str(self.path / ".gitignore")):
						messages.append(LintMessage("f-007", f"File does not match `{gitignore_file_path}`.", se.MESSAGE_TYPE_ERROR, ".gitignore"))
						continue

			with open(Path(root) / filename, "r", encoding="utf-8") as file:
				try:
					file_contents = file.read()
				except UnicodeDecodeError:
					# This is more to help developers find weird files that might choke 'lint', hopefully unnecessary for end users
					messages.append(LintMessage("f-010", "Problem decoding file as utf-8.", se.MESSAGE_TYPE_ERROR, filename))
					continue

				matches = regex.findall(r"http://standardebooks\.org[^\"<\s]*", file_contents)
				if matches:
					messages.append(LintMessage("m-003", "Non-HTTPS URL.", se.MESSAGE_TYPE_ERROR, filename, matches))

				if "UTF-8" in file_contents:
					messages.append(LintMessage("x-001", "String `UTF-8` must always be lowercase.", se.MESSAGE_TYPE_ERROR, filename))

				if filename == "halftitle.xhtml":
					has_halftitle = True
					if "<title>Half Title</title>" not in file_contents:
						messages.append(LintMessage("s-024", "Half title `<title>` elements must contain exactly: \"Half Title\".", se.MESSAGE_TYPE_ERROR, filename))

				if filename == "colophon.xhtml":
					if f"<a href=\"{self.generated_identifier.replace('url:', '')}\">{self.generated_identifier.replace('url:https://', '')}</a>" not in file_contents:
						messages.append(LintMessage("m-035", f"Unexpected SE identifier in colophon. Expected: `{self.generated_identifier}`.", se.MESSAGE_TYPE_ERROR, filename))

					if ">trl<" in metadata_xhtml and "translated from" not in file_contents:
						messages.append(LintMessage("m-025", "Translator found in metadata, but no `translated from LANG` block in colophon.", se.MESSAGE_TYPE_ERROR, filename))

					# Check if we forgot to fill any variable slots
					missing_colophon_vars = [x for x in COLOPHON_VARIABLES if regex.search(fr"\b{x}\b", file_contents)]
					if missing_colophon_vars:
						messages.append(LintMessage("m-036", "Missing data in colophon.", se.MESSAGE_TYPE_ERROR, filename, missing_colophon_vars))

					# Are the sources represented correctly?
					# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
					matches = regex.findall(r"<dc:source>([^<]+?)</dc:source>", metadata_xhtml)
					if len(matches) <= 2:
						for link in matches:
							if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
								messages.append(LintMessage("m-037", f"Source not represented in colophon.xhtml. Expected: `<a href=\"{link}\">Project Gutenberg</a>`.", se.MESSAGE_TYPE_WARNING, filename))

							if "hathitrust.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
								messages.append(LintMessage("m-038", f"Source not represented in colophon.xhtml. Expected: `the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>`.", se.MESSAGE_TYPE_WARNING, filename))

							if "archive.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">Internet Archive</a>" not in file_contents:
								messages.append(LintMessage("m-039", f"Source not represented in colophon.xhtml. Expected: `the<br/> <a href=\"{link}\">Internet Archive</a>`.", se.MESSAGE_TYPE_WARNING, filename))

							if "books.google.com" in link and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
								messages.append(LintMessage("m-040", f"Source not represented in colophon.xhtml. Expected: `<a href=\"{link}\">Google Books</a>`.", se.MESSAGE_TYPE_WARNING, filename))

				if filename == "titlepage.xhtml":
					if "<title>Titlepage</title>" not in file_contents:
						messages.append(LintMessage("s-025", "Titlepage `<title>` elements must contain exactly: `Titlepage`.", se.MESSAGE_TYPE_ERROR, filename))

				if filename.endswith(".svg"):
					# Check for fill: #000 which should simply be removed
					matches = regex.findall(r"fill=\"\s*#000", file_contents) + regex.findall(r"style=\"[^\"]*?fill:\s*#000", file_contents)
					if matches:
						messages.append(LintMessage("x-004", "Illegal `style=\"fill: #000\"` or `fill=\"#000\"`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for illegal height or width on root <svg> element
					if filename != "logo.svg": # Do as I say, not as I do...
						matches = regex.findall(r"<svg[^>]*?(height|width)=[^>]*?>", file_contents)
						if matches:
							messages.append(LintMessage("x-005", "Illegal height or width on root `<svg>` element. Size SVGs using the `viewBox` attribute only.", se.MESSAGE_TYPE_ERROR, filename))

					matches = regex.findall(r"viewbox", file_contents, flags=regex.IGNORECASE)
					for match in matches:
						if match != "viewBox":
							messages.append(LintMessage("x-006", f"`{match}` found instead of `viewBox`. `viewBox` must be correctly capitalized.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for illegal transform attribute
					matches = regex.findall(r"<[a-z]+[^>]*?transform=[^>]*?>", file_contents)
					if matches:
						messages.append(LintMessage("x-003", "Illegal `transform` attribute. SVGs should be optimized to remove use of `transform`. Try using Inkscape to save as an “optimized SVG”.", se.MESSAGE_TYPE_ERROR, filename))

					if f"{os.sep}src{os.sep}" not in root:
						# Check that cover and titlepage images are in all caps
						if filename == "cover.svg":
							matches = regex.findall(r"<text[^>]+?>.*[a-z].*</text>", file_contents)
							if matches:
								messages.append(LintMessage("s-002", "Lowercase letters in cover. Cover text must be all uppercase.", se.MESSAGE_TYPE_ERROR, filename))

							# Save for later comparison with titlepage
							matches = regex.findall(r"<title>(.*?)</title>", file_contents)
							for match in matches:
								cover_svg_title = match.replace("The cover for ", "")

						if filename == "titlepage.svg":
							matches = regex.findall(r"<text[^>]+?>(.*[a-z].*)</text>", html.unescape(file_contents))
							for match in matches:
								if match not in ("translated by", "illustrated by", "and"):
									messages.append(LintMessage("s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except `translated by` and `illustrated by`.", se.MESSAGE_TYPE_ERROR, filename))

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
					matches = regex.findall(r"abbr[^{]*?{[^}]*?white-space:\s*nowrap;[^}]*?}", self.local_css, regex.DOTALL)
					if matches:
						messages.append(LintMessage("c-005", "`abbr` selector does not need `white-space: nowrap;` as it inherits it from `core.css`.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Don't specify border color
					matches = regex.findall(r"(?:border|color).+?(?:#[a-f0-9]{0,6}|black|white|red)", file_contents, flags=regex.IGNORECASE)
					if matches:
						messages.append(LintMessage("c-004", "Do not specify border colors, so that reading systems can adjust for night mode.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# If we select on the xml namespace, make sure we define the namespace in the CSS, otherwise the selector won't work
					matches = regex.findall(r"\[\s*xml\s*\|", file_contents)
					if matches and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in file_contents:
						messages.append(LintMessage("c-003", "`[xml|attr]` selector in CSS, but no XML namespace declared (`@namespace xml \"http://www.w3.org/XML/1998/namespace\";`).", se.MESSAGE_TYPE_ERROR, filename))

				if filename.endswith(".xhtml"):
					# Read file contents into a DOM for querying
					dom_soup = BeautifulSoup(file_contents, "lxml")

					# We also create an EasyXmlTree object, because Beautiful Soup can't select on XML namespaces
					# like [epub|type~="x"]
					dom_lxml = se.easy_xml.EasyXmlTree(file_contents)

					messages = messages + _get_malformed_urls(file_contents, filename)

					# Check for unused selectors
					if not filename.endswith("titlepage.xhtml") and not filename.endswith("imprint.xhtml") and not filename.endswith("uncopyright.xhtml"):
						for selector in local_css_selectors:
							try:
								sel = lxml.cssselect.CSSSelector(selector, translator="html", namespaces=se.XHTML_NAMESPACES)
							except lxml.cssselect.ExpressionError as ex:
								# This gets thrown on some selectors not yet implemented by lxml, like *:first-of-type
								unused_selectors.remove(selector)
								continue
							except Exception as ex:
								raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: `{selector}`\n`lxml` says: {ex}")

							try:
								# We have to remove the default namespace declaration from our document, otherwise
								# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
								tree = etree.fromstring(str.encode(file_contents.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")))
							except etree.XMLSyntaxError as ex:
								raise se.InvalidXhtmlException(f"Couldn’t parse XHTML in `{filename}`\n`lxml` says: {str(ex)}")
							except Exception:
								raise se.InvalidXhtmlException(f"Couldn’t parse XHTML in `{filename}`")

							if tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
								unused_selectors.remove(selector)

					# Update our list of local.css selectors to check in the next file
					local_css_selectors = list(unused_selectors)

					# Done checking for unused selectors.

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

					# Store all headings to check for ToC references later
					if filename != "toc.xhtml":
						for match in dom_soup.select("h1,h2,h3,h4,h5,h6"):

							# Remove any links to the endnotes
							endnote_ref = match.find("a", attrs={"epub:type": regex.compile("^.*noteref.*$")})
							if endnote_ref:
								endnote_ref.extract()

							# Decide whether to remove subheadings based on the following logic:
							# If the closest parent <section> or <article> is a part, division, or volume, then keep subtitle
							# Else, if the closest parent <section> or <article> is a halftitlepage, then discard subtitle
							# Else, if the first child of the heading is not z3998:roman, then also discard subtitle
							# Else, keep the subtitle.
							heading_subtitle = match.find(attrs={"epub:type": regex.compile("^.*subtitle.*$")})

							if heading_subtitle:
								# If an <h#> tag has a subtitle, the non-subtitle text must also be wrapped in a <span>.
								# This invocation of match.find() returns all text nodes. We don't want any text nodes, so if it returns anything then we know we're
								# missing a <span> somewhere.
								if match.find(text=True, recursive=False).strip():
									messages.append(LintMessage("s-015", f"`<{match.name}>` element has subtitle `<span>`, but first line is not wrapped in a `<span>`. See semantics manual for structure of headers with subtitles.", se.MESSAGE_TYPE_ERROR, filename))

								# OK, move on with processing headers.
								parent_section = match.find_parents(["section", "article"])

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
						messages.append(LintMessage("s-029", "If a `<span>` exists only for the `z3998:roman` semantic, then `z3998:roman` should be pulled into parent element instead.", se.MESSAGE_TYPE_WARNING, filename, [match[1] for match in matches]))

					# Check for "Hathi Trust" instead of "HathiTrust"
					if "Hathi Trust" in file_contents:
						messages.append(LintMessage("m-041", "`Hathi Trust` should be `HathiTrust`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for uppercase letters in IDs or classes
					uppercase_attr_values = []
					matches = dom_soup.select("[id],[class]")
					for match in matches:
						if match.has_attr("id"):
							normalized_id = unicodedata.normalize("NFKD", match["id"])
							for uppercase_match in regex.findall(r"[A-Z]+", normalized_id):
								uppercase_attr_values.append(f"id=\"{uppercase_match}\"")

							number_matches = regex.findall(r"^[0-9]+.+", normalized_id)
							if number_matches:
								messages.append(LintMessage("x-007", "`id` attributes starting with a number are illegal XHTML.", se.MESSAGE_TYPE_ERROR, filename, number_matches))

						if match.has_attr("class"):
							for css_class in match["class"]:
								for uppercase_match in regex.findall(r"[A-Z]+", unicodedata.normalize("NFKD", css_class)):
									uppercase_attr_values.append(f"class=\"{uppercase_match}\"")

					if uppercase_attr_values:
						messages.append(LintMessage("x-002", "Uppercase in attribute value. Attribute values must be all lowercase.", se.MESSAGE_TYPE_ERROR, filename, uppercase_attr_values))

					matches = [x for x in dom_soup.select("section") if not x.has_attr("id")]
					if matches:
						messages.append(LintMessage("s-011", "`<section>` element without `id` attribute.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for empty title tags
					if "<title/>" in file_contents or "<title></title>" in file_contents:
						messages.append(LintMessage("s-004", "Empty `<title>` element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for numeric entities
					matches = regex.findall(r"&#[0-9]+?;", file_contents)
					if matches:
						messages.append(LintMessage("s-001", "Illegal numeric entity (like `&#913;`).", se.MESSAGE_TYPE_ERROR, filename))

					# Check nested <blockquote> elements
					matches = regex.findall(r"<blockquote[^>]*?>\s*<blockquote", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("s-005", "Nested `<blockquote>` element.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for <hr> tags before the end of a section, which is a common PG artifact
					matches = regex.findall(r"<hr[^>]*?/?>\s*</section>", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("s-012", "Illegal `<hr/>` before the end of a section.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for double greater-than at the end of a tag
					matches = regex.findall(r"(>>|>&gt;)", file_contents)
					if matches:
						messages.append(LintMessage("x-008", "Elements should end with a single `>`.", se.MESSAGE_TYPE_WARNING, filename))

					# Ignore the title page here, because we often have publishers with ampersands as
					# translators, but in alt tags. Like "George Allen & Unwin".
					if filename != "titlepage.xhtml":
						# Before we process this, we remove the eoc class from <abbr class="name"> because negative lookbehind
						# must be fixed-width. I.e. we can't do `class="name( eoc)?"`
						temp_file_contents = file_contents.replace("\"name eoc\"", "\"name\"")

						# Check for nbsp before ampersand (&amp)
						matches = regex.findall(fr"(?<!\<abbr class=\"name\")>[^>]*?[^{se.NO_BREAK_SPACE}]\&amp;", temp_file_contents)
						if matches:
							messages.append(LintMessage("t-007", "Required no-break space not found before `&amp;`.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for nbsp after ampersand (&amp)
						matches = regex.findall(fr"(?<!\<abbr class=\"name\")>[^>]*?\&amp;[^{se.NO_BREAK_SPACE}]", temp_file_contents)
						if matches:
							messages.append(LintMessage("t-008", "Required no-break space not found after `&amp;`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for nbsp before times
					matches = regex.findall(fr"[0-9]+[^{se.NO_BREAK_SPACE}]<abbr class=\"time", file_contents)
					if matches:
						messages.append(LintMessage("t-009", "Required no-break space not found before `<abbr class=\"time\">`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for low-hanging misquoted fruit
					matches = regex.findall(r"[A-Za-z]+[“‘]", file_contents)
					if matches:
						messages.append(LintMessage("t-028", "Possible mis-curled quotation mark.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check that times have colons and not periods
					matches = regex.findall(r"[0-9]\.[0-9]+\s<abbr class=\"time", file_contents) + regex.findall(r"at [0-9]\.[0-9]+", file_contents)
					if matches:
						messages.append(LintMessage("t-010", "Times must be separated by colons (`:`) not periods (`.`).", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for leading 0 in IDs (note: not the same as checking for IDs that start with an integer)
					matches = regex.findall(r"id=\"[^\"]+?\-0[0-9]+[^\"]*?\"", file_contents)
					if matches:
						messages.append(LintMessage("x-009", "Illegal leading 0 in `id` attribute.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for stage direction that ends in ?! but also has a trailing period
					matches = regex.findall(r"<i epub:type=\"z3998:stage-direction\">(?:(?!<i).)*?\.</i>[,:;!?]", file_contents)
					if matches:
						messages.append(LintMessage("t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction.", se.MESSAGE_TYPE_WARNING, filename, matches))

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
							messages.append(LintMessage("t-017", "Ending punctuation inside italics.", se.MESSAGE_TYPE_WARNING, filename, filtered_matches))

					# Check for <table> tags without a <tbody> child
					tables = dom_soup.select("table")
					for table in tables:
						has_tbody = False
						for element in table.contents:
							if element.name == "tbody":
								has_tbody = True
						if not has_tbody:
							messages.append(LintMessage("s-042", "`<table>` element without `<tbody>` child.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for money not separated by commas
					matches = regex.findall(r"[£\$][0-9]{4,}", file_contents)
					if matches:
						messages.append(LintMessage("t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for deprecated MathML elements
					matches = regex.findall(r"<(?:m:)?mfenced[^>]*?>.+?</(?:m:)?mfenced>", file_contents)
					if matches:
						messages.append(LintMessage("s-017", F"`<m:mfenced>` is deprecated in the MathML spec. Use `<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>`.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for period following Roman numeral, which is an old-timey style we must fix
					# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
					matches = regex.findall(r"(?<!<p[^>]*?>)<span epub:type=\"z3998:roman\">[^<]+?</span>\.\s+[a-z]", file_contents)
					if matches:
						messages.append(LintMessage("t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for two em dashes in a row
					matches = regex.findall(fr"—{se.WORD_JOINER}*—+", file_contents)
					if matches:
						messages.append(LintMessage("t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <abbr class="name"> that does not contain spaces
					matches = regex.findall(r"<abbr class=\"name\">[^<]*?[A-Z]\.[A-Z]\.[^<]*?</abbr>", file_contents)
					if matches:
						messages.append(LintMessage("t-016", "Initials in `<abbr class=\"name\">` not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for empty <h2> missing epub:type="title" attribute
					if "<h2>" in file_contents:
						messages.append(LintMessage("s-009", "`<h2>` element without `epub:type=\"title\"` attribute.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for a common typo
					if "z3998:nonfiction" in file_contents:
						messages.append(LintMessage("s-030", "`z3998:nonfiction` should be `z3998:non-fiction`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for empty <p> tags
					matches = regex.findall(r"<p[^>]*?>\s*</p>", file_contents)
					if "<p/>" in file_contents or matches:
						messages.append(LintMessage("s-010", "Empty `<p>` element. Use `<hr/>` for thematic breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <p> tags that end with <br/>
					matches = regex.findall(r"(\s*<br/?>\s*)+</p>", file_contents)
					if matches:
						messages.append(LintMessage("s-008", "`<br/>` element found before closing `</p>` tag.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for single words that are in italics, but that have closing punctuation outside italics
					# Outer wrapping match is so that .findall returns the entire match and not the subgroup
					# The first regex also matches the first few characters before the first double quote; we use those for more sophisticated
					# checks below, to give fewer false positives like `with its downy red hairs and its “<i xml:lang="fr">doigts de faune</i>.”`
					matches = regex.findall(r"((?:.{1,2}\s)?“<(i|em)[^>]*?>[^<]+?</\2>[\!\?\.])", file_contents) + regex.findall(r"([\.\!\?] <(i|em)[^>]*?>[^<]+?</\2>[\!\?\.])", file_contents)

					# But, if we've matched a name of something, don't include that as an error. For example, `He said, “<i epub:type="se:name.publication.book">The Decameron</i>.”`
					# We also exclude the match from the list if:
					# 1. The double quote is directly preceded by a lowercase letter and a space: `with its downy red hairs and its “<i xml:lang="fr">doigts de faune</i>.”`
					# 2. The double quote is directly preceded by a lowercase letter, a comma, and a space, and the first letter within the double quote is lowercase: In the original, “<i xml:lang="es">que era un Conde de Irlos</i>.”
					# 3. The text is a single letter that is not "I" or "a" (because then it is likely a mathematical variable)
					matches = [x for x in matches if "epub:type=\"se:name." not in x[0] and "epub:type=\"z3998:taxonomy" not in x[0] and not regex.match(r"^[a-z’]+\s“", x[0]) and not regex.match(r"^[a-z’]+,\s“[a-z]", se.formatting.remove_tags(x[0])) and not regex.match(r"^.*?<.+?>[^Ia]<.+?>", x[0])]
					if matches:
						messages.append(LintMessage("t-019", "When a complete clause is italicized, ending punctuation except commas must be within containing italics.", se.MESSAGE_TYPE_WARNING, filename, [match[0] for match in matches]))

					# Run some checks on <i> elements
					comma_matches = []
					italicizing_matches = []
					elements = dom_soup.select("i")
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
						messages.append(LintMessage("t-023", "Comma inside `<i>` element before closing dialog.", se.MESSAGE_TYPE_WARNING, filename, comma_matches))

					if italicizing_matches:
						messages.append(LintMessage("t-024", "When italicizing language in dialog, italics go inside quotation marks.", se.MESSAGE_TYPE_WARNING, filename, italicizing_matches))

					# Check for style attributes
					matches = regex.findall(r"<.+?style=\"", file_contents)
					if matches:
						messages.append(LintMessage("x-012", "Illegal `style` attribute. Do not use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for uppercase HTML tags
					matches = regex.findall(r"<[a-zA-Z]*[A-Z]+[a-zA-Z]*", file_contents)
					for match in matches:
						messages.append(LintMessage("x-011", "Uppercased HTML tag.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for nbsp within <abbr class="name">, which is redundant
					matches = regex.findall(fr"<abbr[^>]+?class=\"name\"[^>]*?>[^<]*?{se.NO_BREAK_SPACE}[^<]*?</abbr>", file_contents)
					if matches:
						messages.append(LintMessage("t-022", "No-break space found in `<abbr class=\"name\">`. This is redundant.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for Roman numerals in <title> tag
					if regex.findall(r"<title>[Cc]hapter [XxIiVv]+", file_contents):
						messages.append(LintMessage("s-026", "Illegal Roman numeral in `<title>` element; use Arabic numbers.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for HTML tags in <title> tags
					matches = regex.findall(r"<title>.*?[<].*?</title>", file_contents)
					if matches:
						messages.append(LintMessage("x-010", "Illegal element in `<title>` element.", se.MESSAGE_TYPE_ERROR, filename, matches))

					unexpected_titles = []
					# If the chapter has a number and no subtitle, check the <title> tag...
					matches = regex.findall(r"<h([0-6]) epub:type=\"title z3998:roman\">([^<]+)</h\1>", file_contents, flags=regex.DOTALL)

					# ...But only make the correction if there's one <h#> tag. If there's more than one, then the xhtml file probably requires an overarching title
					if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
						try:
							chapter_number = roman.fromRoman(matches[0][1].upper())

							if not regex.findall(fr"<title>(Chapter|Section|Part) {chapter_number}", file_contents):
								unexpected_titles.append((f"Chapter {chapter_number}", filename))
						except Exception:
							messages.append(LintMessage("s-035", "`<h#>` element has the `z3998:roman` semantic, but is not a Roman numeral.", se.MESSAGE_TYPE_ERROR, filename))

					# If the chapter has a number and subtitle, check the <title> tag...
					matches = regex.findall(r"<h([0-6]) epub:type=\"title\">\s*<span epub:type=\"z3998:roman\">([^<]+)</span>\s*<span epub:type=\"subtitle\">(.+?)</span>\s*</h\1>", file_contents, flags=regex.DOTALL)

					# ...But only make the correction if there's one <h#> tag. If there's more than one, then the xhtml file probably requires an overarching title
					if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
						chapter_number = roman.fromRoman(matches[0][1].upper())

						# First, remove endnotes in the subtitle, then remove all other tags (but not tag contents)
						chapter_title = regex.sub(r"<a[^<]+?epub:type=\"noteref\"[^<]*?>[^<]+?</a>", "", matches[0][2]).strip()
						chapter_title = regex.sub(r"<[^<]+?>", "", chapter_title)

						if not regex.findall(fr"<title>(Chapter|Section|Part) {chapter_number}: {regex.escape(chapter_title)}</title>", file_contents):
							unexpected_titles.append((f"Chapter {chapter_number}: {chapter_title}", filename))

					# Now, we try to select the first <h#> element in a <section> or <article>.
					# If it doesn't have children and its content is a text string, check to see
					# if the <title> tag matches. This catches for example <h2 epub:type="title">Introduction</h2>
					# However, skip this step if the file contains 3+ <article> tags at the top level. That makes it likely
					# that the book is a collection (like a poetry collection) and so the <title> tag can't be inferred.
					if len(dom_soup.select("body > article")) <= 3:
						elements = dom_soup.select("body section:first-of-type h1,h2,h3,h4,h5,h6") + dom_soup.select("body article:first-of-type h1,h2,h3,h4,h5,h6")
						if elements:
							# Make sure we don't process headers that contain <span> elements, we took care of those above.
							if elements[0].get("epub:type") == "title" and (len(elements[0].contents) == 1 or (len(elements[0].contents) > 1 and not str(elements[0].contents[1]).startswith("<span"))) and isinstance(elements[0].contents[0], NavigableString):
								# We want to remove all HTML tags, in case there are things like <abbr>Mr.</abbr> in there.
								title = regex.sub(r"<[^>]+?>", "", str(elements[0]).strip())
								if f"<title>{title}</title>" not in file_contents:
									unexpected_titles.append((title, filename))

					for title, title_filename in unexpected_titles:
						messages.append(LintMessage("s-021", f"Unexpected value for `<title>` element. Expected: `{title}`. (Beware hidden Unicode characters!)", se.MESSAGE_TYPE_ERROR, title_filename))

					# Check for missing subtitle styling
					if "epub:type=\"subtitle\"" in file_contents and not local_css_has_subtitle_style:
						messages.append(LintMessage("c-006", "Subtitles found, but no subtitle style found in `local.css`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for whitespace before noteref
					matches = regex.findall(r"\s+<a href=\"endnotes\.xhtml#note-[0-9]+?\" id=\"noteref-[0-9]+?\" epub:type=\"noteref\">[0-9]+?</a>", file_contents)
					if matches:
						messages.append(LintMessage("t-012", "Illegal white space before noteref.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for <li> elements that don't have a direct block child
					if filename != "toc.xhtml":
						matches = regex.findall(r"<li(?:\s[^>]*?>|>)\s*[^\s<]", file_contents)
						if matches:
							messages.append(LintMessage("s-007", "`<li>` element without direct block-level child.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for ldquo not correctly closed
					# Ignore closing paragraphs, line breaks, and closing cells in case ldquo means "ditto mark"
					matches = regex.findall(r"“[^‘”]+?“", file_contents)
					matches = [x for x in matches if "</p" not in x and "<br/>" not in x and "</td>" not in x]
					if matches:
						messages.append(LintMessage("t-003", "`“` missing matching `”`.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for lsquo not correctly closed
					matches = regex.findall(r"‘[^“’]+?‘", file_contents)
					matches = [x for x in matches if "</p" not in x and "<br/>" not in x]
					if matches:
						messages.append(LintMessage("t-004", "`‘` missing matching `’`.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for IDs on <h#> tags
					matches = regex.findall(r"<h[0-6][^>]*?id=[^>]*?>", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("s-019", "`<h#>` element with `id` attribute. `<h#>` elements should be wrapped in `<section>` elements, which should hold the `id` attribute.", se.MESSAGE_TYPE_WARNING, filename, matches))

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

									titlecased_title = f"{title_header} {subtitle} {title_footer}"
									titlecased_title = titlecased_title.strip()

									title = se.formatting.remove_tags(title).strip()
									if title != titlecased_title:
										messages.append(LintMessage("s-023", f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`.", se.MESSAGE_TYPE_WARNING, filename))

							# No subtitle? Much more straightforward
							else:
								titlecased_title = se.formatting.remove_tags(se.formatting.titlecase(title))
								title = se.formatting.remove_tags(title)
								if title != titlecased_title:
									messages.append(LintMessage("s-023", f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for <figure> tags without id attributes
					matches = regex.findall(r"<img[^>]*?id=\"[^>]+?>", file_contents)
					if matches:
						messages.append(LintMessage("s-018", "`<img>` element with `id` attribute. `id` attributes go on parent `<figure>` elements.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for closing dialog without comma
					matches = regex.findall(r"[a-z]+?” [a-zA-Z]+? said", file_contents)
					if matches:
						messages.append(LintMessage("t-005", "Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for non-typogrified img alt attributes
					matches = regex.findall(r"alt=\"[^\"]*?('|--|&quot;)[^\"]*?\"", file_contents)
					if matches:
						messages.append(LintMessage("t-025", "Non-typogrified `'`, `\"` (as `&quot;`), or `--` in image `alt` attribute.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check alt attributes not ending in punctuation
					if filename not in se.IGNORED_FILENAMES:
						matches = regex.findall(r"alt=\"[^\"]*?[a-zA-Z]\"", file_contents)
						if matches:
							messages.append(LintMessage("t-026", "`alt` attribute does not appear to end with punctuation. `alt` attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check alt attributes match image titles
					images = dom_soup.select("img[src$=svg]")
					for image in images:
						alt_text = image["alt"]
						title_text = ""
						image_ref = image["src"].split("/").pop()
						try:
							with open(self.path / "src" / "epub" / "images" / image_ref, "r", encoding="utf-8") as image_source:
								try:
									title_text = BeautifulSoup(image_source, "lxml").title.get_text()
								except Exception:
									messages.append(LintMessage("s-027", f"{image_ref} missing `<title>` element.", se.MESSAGE_TYPE_ERROR, image_ref))
							if title_text != "" and alt_text != "" and title_text != alt_text:
								messages.append(LintMessage("s-022", f"The `<title>` element of `{image_ref}` does not match the alt text in `{filename}`.", se.MESSAGE_TYPE_ERROR, filename))
						except FileNotFoundError:
							missing_files.append(str(Path(f"src/epub/images/{image_ref}")))

					# Check for punctuation after endnotes
					regex_string = fr"<a[^>]*?epub:type=\"noteref\"[^>]*?>[0-9]+</a>[^\s<–\]\)—{se.WORD_JOINER}]"
					matches = regex.findall(regex_string, file_contents)
					if matches:
						messages.append(LintMessage("t-020", "Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for nbsp in measurements, for example: 90 mm
					matches = regex.findall(r"[0-9]+[\- ][mck][mgl]\b", file_contents)
					if matches:
						messages.append(LintMessage("t-021", "Measurements must be separated by a no-break space, not a dash or regular space.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for line breaks after <br/> tags
					matches = regex.findall(r"<br\s*?/>[^\n]", file_contents)
					if matches:
						messages.append(LintMessage("s-016", "`<br/>` element must be followed by a newline, and subsequent content must be indented to the same level.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <pre> tags
					if "<pre" in file_contents:
						messages.append(LintMessage("s-013", "Illegal `<pre>` element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <pre> tags
					matches = regex.findall(r"</(?:p|blockquote|table|ol|ul|section|article)>\s*<br/>", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("s-014", "`<br/>` after block-level element.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
					matches = regex.findall(r"\b.+?”[,\.](?! …)", file_contents)
					if matches:
						messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for double spacing
					regex_string = fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}"
					matches = regex.findall(regex_string, file_contents)
					if matches:
						double_spaced_files.append(str(Path(filename)))

					# Run some checks on epub:type values
					incorrect_attrs = []
					epub_type_attrs = regex.findall("epub:type=\"([^\"]+?)\"", file_contents)
					for attrs in epub_type_attrs:
						for attr in regex.split(r"\s", attrs):
							# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
							matches = regex.findall(r"^se:[a-z]+:(?:[a-z]+:?)*", attr)
							if matches:
								messages.append(LintMessage("s-031", "Illegal colon (`:`) in SE identifier. SE identifiers are separated by dots, not colons. E.g., `se:name.vessel.ship`.", se.MESSAGE_TYPE_ERROR, filename, matches))

							# Did someone use periods instead of colons for the SE namespace? e.g. se.name.vessel.ship
							matches = regex.findall(r"^se\.[a-z]+(?:\.[a-z]+)*", attr)
							if matches:
								messages.append(LintMessage("s-032", "SE namespace must be followed by a colon (`:`), not a dot. E.g., `se:name.vessel`.", se.MESSAGE_TYPE_ERROR, filename, matches))

							# Did we draw from the z3998 vocabulary when the item exists in the epub vocabulary?
							if attr.startswith("z3998:"):
								bare_attr = attr.replace("z3998:", "")
								if bare_attr in EPUB_SEMANTIC_VOCABULARY:
									incorrect_attrs.append((attr, bare_attr))

					# Convert this into a unique set so we don't spam the console with repetitive messages
					unique_incorrect_attrs = set(incorrect_attrs)
					for (attr, bare_attr) in unique_incorrect_attrs:
						messages.append(LintMessage("s-034", f"`{attr}` semantic used, but `{bare_attr}` is in the EPUB semantic inflection vocabulary.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for leftover asterisms
					matches = regex.findall(r"<[a-z]+[^>]*?>\s*\*\s*(\*\s*)+", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("s-038", "Illegal asterism (`***`). Section/scene breaks must be defined by an `<hr/>` element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for missing punctuation before closing quotes
					matches = regex.findall(r"[a-z]+[”’]</p>(?!\s*</header>)", file_contents, flags=regex.IGNORECASE)
					if matches:
						messages.append(LintMessage("t-011", "Missing punctuation before closing quotes.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check to see if we've marked something as poetry or verse, but didn't include a first <span>
					matches = regex.findall(r"<blockquote [^>]*?epub:type=\"z3998:(poem|verse)\"[^>]*?>\s*<p>(?!\s*<span)", file_contents, flags=regex.DOTALL)
					if matches:
						messages.append(LintMessage("s-006", "Poem or verse included without `<span>` element.", se.MESSAGE_TYPE_ERROR, filename, matches))

					# Check to see if we included poetry or verse without the appropriate styling
					if filename not in se.IGNORED_FILENAMES:
						if "z3998:poem" in file_contents and not local_css_has_poem_style:
							messages.append(LintMessage("s-043", "Poem included without styling in `local.css`.", se.MESSAGE_TYPE_ERROR, filename))

						if "z3998:verse" in file_contents and not local_css_has_verse_style:
							messages.append(LintMessage("s-044", "Verse included without styling in `local.css`.", se.MESSAGE_TYPE_ERROR, filename))

						if "z3998:song" in file_contents and not local_css_has_song_style:
							messages.append(LintMessage("s-045", "Song included without styling in `local.css`.", se.MESSAGE_TYPE_ERROR, filename))

					nodes = dom_lxml.css_select("[epub|type~='z3998:verse'] span + a[epub|type~='noteref']") + dom_lxml.css_select("[epub|type~='z3998:poem'] span + a[epub|type~='noteref']")
					if nodes:
						messages.append(LintMessage("s-046", "`noteref` as a direct child of poetry or verse. `noteref`s should be in their parent `<span>`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for space before endnote backlinks
					if filename == "endnotes.xhtml":
						# Do we have to replace Ibid.?
						matches = regex.findall(r"\bibid\b", file_contents, flags=regex.IGNORECASE)
						if matches:
							messages.append(LintMessage("s-039", "Illegal `Ibid` in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing `Ibid` refers to.", se.MESSAGE_TYPE_ERROR, filename))

						endnote_referrers = dom_soup.select("li[id^=note-] a")
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
							messages.append(LintMessage("t-027", "Endnote referrer link not preceded by exactly one space, or a newline if all previous siblings are elements.", se.MESSAGE_TYPE_WARNING, filename, [str(referrer) for referrer in bad_referrers]))

					# If we're in the imprint, are the sources represented correctly?
					# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
					if filename == "imprint.xhtml":
						matches = regex.findall(r"<dc:source>([^<]+?)</dc:source>", metadata_xhtml)
						if len(matches) <= 2:
							for link in matches:
								if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
									messages.append(LintMessage("m-026", f"Project Gutenberg source not present. Expected: `<a href=\"{link}\">Project Gutenberg</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "hathitrust.org" in link and f"the <a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
									messages.append(LintMessage("m-027", f"HathiTrust source not present. Expected: the `<a href=\"{link}\">HathiTrust Digital Library</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "archive.org" in link and f"the <a href=\"{link}\">Internet Archive</a>" not in file_contents:
									messages.append(LintMessage("m-028", f"Internet Archive source not present. Expected: the `<a href=\"{link}\">Internet Archive</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "books.google.com" in link and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
									messages.append(LintMessage("m-029", f"Google Books source not present. Expected: `<a href=\"{link}\">Google Books</a>`.", se.MESSAGE_TYPE_WARNING, filename))

					# Collect abbr elements for later check
					result = regex.findall("<abbr[^<]+?>", file_contents)
					result = [item.replace("eoc", "").replace(" \"", "").strip() for item in result]
					abbr_elements = list(set(result + abbr_elements))

					# Check if language tags in individual files match the language in content.opf
					if filename not in se.IGNORED_FILENAMES:
						file_language = regex.search(r"<html[^<]+xml\:lang=\"([^\"]+)\"", file_contents).group(1)
						if language != file_language:
							messages.append(LintMessage("s-033", f"File language is `{file_language}`, but `content.opf` language is `{language}`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check LoI descriptions to see if they match associated figcaptions
					if filename == "loi.xhtml":
						illustrations = dom_soup.select("li > a")
						for illustration in illustrations:
							figure_ref = illustration["href"].split("#")[1]
							chapter_ref = regex.findall(r"(.*?)#.*", illustration["href"])[0]
							figcaption_text = ""
							loi_text = illustration.get_text()

							with open(self.path / "src" / "epub" / "text" / chapter_ref, "r", encoding="utf-8") as chapter:
								try:
									figure = BeautifulSoup(chapter, "lxml").select(f"#{figure_ref}")[0]
								except Exception:
									messages.append(LintMessage("s-040", f"`#{figure_ref}` not found in file `{chapter_ref}`.", se.MESSAGE_TYPE_ERROR, "loi.xhtml"))
									continue

								if figure.img:
									figure_img_alt = figure.img.get("alt")

								if figure.figcaption:
									figcaption_text = figure.figcaption.get_text()
							if (figcaption_text != "" and loi_text != "" and figcaption_text != loi_text) and (figure_img_alt != "" and loi_text != "" and figure_img_alt != loi_text):
								messages.append(LintMessage("s-041", f"The `<figcaption>` element of `#{figure_ref}` does not match the text in its LoI entry.", se.MESSAGE_TYPE_WARNING, chapter_ref))

				# Check for missing MARC relators
				if filename == "introduction.xhtml" and ">aui<" not in metadata_xhtml and ">win<" not in metadata_xhtml:
					messages.append(LintMessage("m-030", "`introduction.xhtml` found, but no MARC relator `aui` (Author of introduction, but not the chief author) or `win` (Writer of introduction).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "preface.xhtml" and ">wpr<" not in metadata_xhtml:
					messages.append(LintMessage("m-031", "`preface.xhtml` found, but no MARC relator `wpr` (Writer of preface).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "afterword.xhtml" and ">aft<" not in metadata_xhtml:
					messages.append(LintMessage("m-032", "`afterword.xhtml` found, but no MARC relator `aft` (Author of colophon, afterword, etc.).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "endnotes.xhtml" and ">ann<" not in metadata_xhtml:
					messages.append(LintMessage("m-033", "`endnotes.xhtml` found, but no MARC relator `ann` (Annotator).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "loi.xhtml" and ">ill<" not in metadata_xhtml:
					messages.append(LintMessage("m-034", "`loi.xhtml` found, but no MARC relator `ill` (Illustrator).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				# Check for wrong semantics in frontmatter/backmatter
				if filename in se.FRONTMATTER_FILENAMES and "frontmatter" not in file_contents:
					messages.append(LintMessage("s-036", "No `frontmatter` semantic inflection for what looks like a frontmatter file.", se.MESSAGE_TYPE_WARNING, filename))

				if filename in se.BACKMATTER_FILENAMES and "backmatter" not in file_contents:
					messages.append(LintMessage("s-037", "No `backmatter` semantic inflection for what looks like a backmatter file.", se.MESSAGE_TYPE_WARNING, filename))

	if cover_svg_title != titlepage_svg_title:
		messages.append(LintMessage("s-028", "`cover.svg` and `titlepage.svg` `<title>` elements do not match.", se.MESSAGE_TYPE_ERROR))

	if has_frontmatter and not has_halftitle:
		messages.append(LintMessage("s-020", "Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	if not has_cover_source:
		missing_files.append(str(Path("images/cover.source.jpg")))

	missing_selectors = []
	single_use_css_classes = []

	for css_class in xhtml_css_classes:
		if css_class not in se.IGNORED_CLASSES:
			if f".{css_class}" not in self.local_css:
				missing_selectors.append(css_class)

		if xhtml_css_classes[css_class] == 1 and css_class not in se.IGNORED_CLASSES and not regex.match(r"^i[0-9]$", css_class):
			# Don't count ignored classes OR i[0-9] which are used for poetry styling
			single_use_css_classes.append(css_class)

	if missing_selectors:
		messages.append(LintMessage("x-013", "CSS class found in XHTML, but not in `local.css`.", se.MESSAGE_TYPE_ERROR, "local.css", missing_selectors))

	if single_use_css_classes:
		messages.append(LintMessage("c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks.", se.MESSAGE_TYPE_WARNING, "local.css", single_use_css_classes))

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
				messages.append(LintMessage("m-045", f"Heading `{heading[0]}` found, but not present for that file in the ToC.", se.MESSAGE_TYPE_ERROR, heading[1]))

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
				messages.append(LintMessage("m-043", f"The number of elements in the spine ({len(toc_files)}) does not match the number of elements in the ToC and landmarks ({len(spine_entries)}).", se.MESSAGE_TYPE_ERROR, "content.opf"))
			for index, entry in enumerate(spine_entries):
				if toc_files[index] != entry.attrs["idref"]:
					messages.append(LintMessage("m-044", f"The spine order does not match the order of the ToC and landmarks. Expected `{entry.attrs['idref']}`, found `{toc_files[index]}`.", se.MESSAGE_TYPE_ERROR, "content.opf"))
					break

	for element in abbr_elements:
		try:
			css_class = regex.search(r"class=\"([^\"]+?)\"", element).group(1)
		except Exception:
			continue
		if css_class and css_class in ("temperature", "era", "acronym") and f"abbr.{css_class}" not in abbr_styles:
			messages.append(LintMessage("c-007", f"`<abbr class=\"{css_class}\">` element found, but no required style in `local.css`. See the typography manual for required styls.", se.MESSAGE_TYPE_ERROR, "local.css"))

	if double_spaced_files:
		for double_spaced_file in double_spaced_files:
			messages.append(LintMessage("t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)", se.MESSAGE_TYPE_ERROR, double_spaced_file))

	for missing_file in missing_files:
		messages.append(LintMessage("f-002", "Missing expected file or directory.", se.MESSAGE_TYPE_ERROR, missing_file))

	if unused_selectors:
		messages.append(LintMessage("c-002", "Unused CSS selectors.", se.MESSAGE_TYPE_ERROR, "local.css", unused_selectors))

	# Now that we have our lint messages, we filter out ones that we've ignored.
	if ignored_codes:
		# Iterate over a copy of messages, so that we can remove from them while iterating.
		for message in messages[:]:
			for path, codes in ignored_codes.items():
				for code in codes:
					try:
						# fnmatch.translate() converts shell-style globs into a regex pattern
						if regex.match(fr"{translate(path)}", message.filename) and message.code == code["code"]:
							messages.remove(message)
							code["used"] = True

					except ValueError as ex:
						# This gets raised if the message has already been removed by a previous rule.
						# For example, chapter-*.xhtml gets t-001 removed, then subsequently *.xhtml gets t-001 removed.
						pass
					except Exception as ex:
						raise se.InvalidInputException(f"Invalid path in `se-lint-ignore.xml` rule: `{path}`")

		# Check for unused ignore rules
		unused_codes: List[str] = []
		for path, codes in ignored_codes.items():
			for code in codes:
				if not code["used"]:
					unused_codes.append(f"{path}, {code['code']}")

		if unused_codes:
			messages.append(LintMessage("m-048", "Unused se-lint-ignore.xml rule.", se.MESSAGE_TYPE_ERROR, "se-lint-ignore.xml", unused_codes))

	messages = natsorted(messages, key=lambda x: (x.filename, x.code))

	return messages
