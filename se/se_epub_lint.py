#!/usr/bin/env python3
"""
Contains the LintMessage class and the Lint function, which is broken out of
the SeEpub class for readability and maintainability.

Strictly speaking, the lint() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

from copy import deepcopy
import filecmp
from fnmatch import translate
import io
import os
from pathlib import Path
from typing import Dict, List, Set, Union
import importlib_resources

import cssutils
import lxml.cssselect
import lxml.etree as etree
from PIL import Image, UnidentifiedImageError
import regex
import roman
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
"c-006", "Semantic found, but missing corresponding style in `local.css`."
"c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks."
"c-009", "Duplicate CSS selectors. Duplicates are only acceptable if overriding SE base styles."
vvvvvvvvUNUSEDvvvvvvvvvv
"c-007", f"`<abbr class=\"{css_class}\">` element found, but no required style in `local.css`. See the typography manual for required styles."

FILESYSTEM
"f-001", "Illegal file or directory."
"f-002", "Missing expected file or directory."
"f-003", f"File does not match `{license_file_path}`."
"f-004", f"File does not match `{core_css_file_path}`."
"f-005", f"File does not match `{logo_svg_file_path}`."
"f-006", f"File does not match `{uncopyright_file_path}`."
"f-007", f"File does not match `{gitignore_file_path}`."
"f-008", "Filename is not URL-safe. Expected: `{url_safe_filename}`."
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
"m-009", f"`<meta property=\"se:url.vcs.github\">` value does not match expected: `{self.generated_github_repo_url}`."
"m-010", "Invalid `refines` property."
"m-011", "Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: `https://catalog.hathitrust.org/Record/<RECORD-ID>`."
"m-012", "Non-typogrified character in `<dc:title>` element."
"m-013", "Non-typogrified character in `<dc:description>` element."
"m-014", "Non-typogrified character in `<meta property=\"se:long-description\">` element."
"m-015", "Metadata long description is not valid XHTML. LXML says: "
"m-016", "Long description must be escaped HTML."
"m-017", "`<![CDATA[` found. Run `se clean` to canonicalize `<![CDATA[` sections."
"m-018", "HTML entities found. Use Unicode equivalents instead."
"m-019", "Illegal em-dash in `<dc:subject>` element; use `--`."
"m-020", "Illegal value for `<meta property="se:subject">` element."
"m-021", "No `<meta property=\"se:subject\">` element found."
"m-022", "Empty `<meta property=\"se:production-notes\">` element."
"m-023", f"`<dc:identifier>` does not match expected: `{self.generated_identifier}`."
"m-024", "`<meta property=\"se:name.person.full-name\">` property identical to regular name. If the two are identical the full name `<meta>` element must be removed."
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
"m-048", "Unused `se-lint-ignore.xml` rule."
"m-049", "No `se-lint-ignore.xml` rules. Delete the file if there are no rules."
"m-050", "Non-typogrified character in `<meta property=\"file-as\" refines=\"#title\">` element."
"m-051", "Missing expected element in metadata."

SEMANTICS & CONTENT
"s-001", "Illegal numeric entity (like `&#913;`)."
"s-002", "Lowercase letters in cover. Cover text must be all uppercase."
"s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except `translated by` and `illustrated by`."
"s-004", "`img` element missing `alt` attribute."
"s-005", "Nested `<blockquote>` element."
"s-006", "Poem or verse `<p>` (stanza) without `<span>` (line) element."
"s-007", "`<li>` element without direct block-level child."
"s-008", "`<br/>` element found before closing tag of block-level element."
"s-009", "`<h2>` element without `epub:type=\"title\"` attribute."
"s-010", "Empty element. Use `<hr/>` for thematic breaks if appropriate."
"s-011", "Element without `id` attribute."
"s-012", "Illegal `<hr/>` element as last child."
"s-013", "Illegal `<pre>` element."
"s-014", "`<br/>` after block-level element."
"s-015", f"`<{match.name}>` element has `<span epub:type=\"subtitle\">` child, but first child is not `<span>`. See semantics manual for structure of headers with subtitles."
"s-017", F"`<m:mfenced>` is deprecated in the MathML spec. Use `<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>`."
"s-018", "`<img>` element with `id` attribute. `id` attributes go on parent `<figure>` elements."
"s-019", "`<h#>` element with `id` attribute. `<h#>` elements should be wrapped in `<section>` elements, which should hold the `id` attribute."
"s-020", "Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present."
"s-021", f"Unexpected value for `<title>` element. Expected: `{title}`. (Beware hidden Unicode characters!)"
"s-022", f"The `<title>` element of `{image_ref}` does not match the `alt` attribute text in `{filename}`."
"s-023", f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`."
"s-024", "Half title `<title>` elements must contain exactly: \"Half Title\"."
"s-025", "Titlepage `<title>` elements must contain exactly: `Titlepage`."
"s-026", "Invalid Roman numeral."
"s-027", f"{image_ref} missing `<title>` element."
"s-028", "`cover.svg` and `titlepage.svg` `<title>` elements do not match."
"s-029", "If a `<span>` exists only for the `z3998:roman` semantic, then `z3998:roman` should be pulled into parent element instead."
"s-030", "`z3998:nonfiction` should be `z3998:non-fiction`."
"s-031", "Illegal colon (`:`) in SE identifier. SE identifiers are separated by dots, not colons. E.g., `se:name.vessel.ship`."
"s-032", "SE namespace must be followed by a colon (`:`), not a dot. E.g., `se:name.vessel`."
"s-033", f"File language is `{file_language}`, but `content.opf` language is `{language}`."
"s-034", "Semantic used from the z3998 vocabulary, but the same semantic exists in the EPUB vocabulary."
"s-035", "`<h#>` element has the `z3998:roman` semantic, but is not a Roman numeral."
"s-036", "No `frontmatter` semantic inflection for what looks like a frontmatter file."
"s-037", "No `backmatter` semantic inflection for what looks like a backmatter file."
"s-038", "Illegal asterism (`***`). Section/scene breaks must be defined by an `<hr/>` element."
"s-039", "Illegal `Ibid` in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing `Ibid` refers to."
"s-040", f"`#{figure_ref}` not found in file `{chapter_ref}`."
"s-041", f"The `<figcaption>` element of `#{figure_ref}` does not match the text in its LoI entry."
"s-042", "`<table>` element without `<tbody>` child."
"s-047", "`noteref` as a direct child of element with `z3998:poem` semantic. `noteref`s should be in their parent `<span>`."
"s-048", "`noteref` as a direct child of element with `z3998:verse` semantic. `noteref`s should be in their parent `<span>`."
"s-049", "`noteref` as a direct child of element with `z3998:song` semantic. `noteref`s should be in their parent `<span>`."
"s-050", "`noteref` as a direct child of element with `z3998:hymn` semantic. `noteref`s should be in their parent `<span>`."
"s-051", "Wrong height or width. `cover.jpg` must be exactly 1400 × 2100."
"s-052", "`<attr>` element with illegal `title` attribute."
"s-053", "Colophon line not preceded by `<br/>`."
"s-054", "`<cite>` as child of `<p>` in `<blockquote>`. `<cite>` should be the direct child of `<blockquote>`."
vvvvvvvvUNUSEDvvvvvvvvvv
"s-016", "`<br/>` element must be followed by a newline, and subsequent content must be indented to the same level."
"s-043", "Poem included without styling in `local.css`."
"s-044", "Verse included without styling in `local.css`."
"s-045", "Song included without styling in `local.css`."
"s-046", "Hymn included without styling in `local.css`."

TYPOGRAPHY
"t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)"
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
"t-017", "Ending punctuation inside italics. Ending punctuation is only allowed within italics if the phrase is an independent clause."
"t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction."
"t-019", "When a complete clause is italicized, ending punctuation except commas must be within containing italics."
"t-020", "Endnote links must be outside of punctuation, including quotation marks."
"t-021", "Measurement not to standard. Numbers are followed by a no-break space and abbreviated units require an `<abbr>` element. See `semos://1.0.0/8.8.5`."
"t-022", "No-break space found in `<abbr class=\"name\">`. This is redundant."
"t-023", "Comma inside `<i>` element before closing dialog."
"t-024", "When italicizing language in dialog, italics go inside quotation marks."
"t-025", "Non-typogrified `'`, `\"` (as `&quot;`), or `--` in image `alt` attribute."
"t-026", "`alt` attribute does not appear to end with punctuation. `alt` attributes must be composed of complete sentences ending in appropriate punctuation."
"t-027", "Endnote referrer link not preceded by exactly one space."
"t-028", "Possible mis-curled quotation mark."
"t-029", "Period followed by lowercase letter. Hint: Abbreviations require an `<abbr>` element."
"t-030", "Initialism with spaces or without periods."
"t-031", "`A B C` must be set as `A.B.C.` It is not an abbreviation."
"t-032", "Initialism or name followed by period. Hint: Periods go within `<abbr>`. `<abbr>`s containing periods that end a clause require the `eoc` class."
"t-033", "Space after dash."
"t-034", "`<cite>` element preceded by em-dash. Hint: em-dashes go within `<cite>` elements."
"t-035", "`<cite>` element not preceded by space."

XHTML
"x-001", "String `UTF-8` must always be lowercase."
"x-002", "Uppercase in attribute value. Attribute values must be all lowercase."
"x-003", "Illegal `transform` attribute. SVGs should be optimized to remove use of `transform`. Try using Inkscape to save as an “optimized SVG”."
"x-004", "Illegal `style=\"fill: #000\"` or `fill=\"#000\"`."
"x-005", "Illegal `height` or `width` attribute on root `<svg>` element. Size SVGs using the `viewBox` attribute only."
"x-006", f"`{match}` found instead of `viewBox`. `viewBox` must be correctly capitalized."
"x-007", "`id` attributes starting with a number are illegal XHTML."
"x-008", "Elements should end with a single `>`."
"x-009", "Illegal leading 0 in `id` attribute."
"x-010", "Illegal element in `<title>` element."
"x-011", "Uppercased HTML tag."
"x-012", "Illegal `style` attribute. Do not use inline styles, any element can be targeted with a clever enough selector."
"x-013", "CSS class found in XHTML, but not in `local.css`."
"x-014", "Illegal `id` attribute."
"x-015", f"Illegal element in `<head>`. Only `<title>` and `<link rel=\"stylesheet\">` are allowed."
"""

class LintMessage:
	"""
	An object representing an output message for the lint function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	def __init__(self, code: str, text: str, message_type=se.MESSAGE_TYPE_WARNING, filename: str = "", submessages: Union[List[str], Set[str]] = None):
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

# Cache dom objects so we don't have to create them multiple times
_DOM_CACHE: Dict[str, Union[se.easy_xml.EasyXmlTree, se.easy_xml.EasyXhtmlTree, se.easy_xml.EasySvgTree]] = {}
def _dom(file_path: Path) -> Union[se.easy_xml.EasyXmlTree, se.easy_xml.EasyXhtmlTree, se.easy_xml.EasySvgTree]:
	file_path_str = str(file_path)
	if file_path_str not in _DOM_CACHE:
		with open(file_path, "r", encoding="utf-8") as file:
			try:
				if file_path.suffix == ".xml":
					_DOM_CACHE[file_path_str] = se.easy_xml.EasyXmlTree(file.read())

				if file_path.suffix == ".xhtml":
					_DOM_CACHE[file_path_str] = se.easy_xml.EasyXhtmlTree(file.read())

				if file_path.suffix == ".svg":
					_DOM_CACHE[file_path_str] = se.easy_xml.EasySvgTree(file.read())

				# Remove comments
				for node in _DOM_CACHE[file_path_str].xpath("//comment()"):
					node.remove()

			except etree.XMLSyntaxError as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in `{file_path}`\n`lxml` says: {str(ex)}")
			except FileNotFoundError as ex:
				raise ex
			except Exception:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in `{file_path}`")

	return _DOM_CACHE[file_path_str]

def lint(self, skip_lint_ignore: bool) -> list:
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
	missing_metadata_elements = []
	abbr_elements: List[se.easy_xml.EasyXmlElement] = []
	initialism_exceptions = ["MS.", "MSS.", "κ.τ.λ.", "TV"] # semos://1.0.0/8.10.5.1; κ.τ.λ. is "etc." in Greek, and we don't match Greek chars.

	# This is a dict with where keys are the path and values are a list of code dicts.
	# Each code dict has a key "code" which is the actual code, and a key "used" which is a
	# bool indicating whether or not the code has actually been caught in the linting run.
	ignored_codes: Dict[str, List[Dict]] = {}

	# First, check if we have an se-lint-ignore.xml file in the ebook root. If so, parse it. For an example se-lint-ignore file, see semos://1.0.0/2.3
	if not skip_lint_ignore and (self.path / "se-lint-ignore.xml").exists():
		lint_config = _dom(self.path / "se-lint-ignore.xml")

		elements = lint_config.xpath("/se-lint-ignore/file")

		if not elements:
			messages.append(LintMessage("m-049", "No `se-lint-ignore.xml` rules. Delete the file if there are no rules.", se.MESSAGE_TYPE_ERROR, "se-lint-ignore.xml"))

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

	# Done parsing ignore list

	# Get the ebook language for later use
	try:
		language = self.metadata_dom.xpath("/package/metadata/dc:language")[0].text
	except se.InvalidXmlException as ex:
		raise ex
	except Exception:
		raise se.InvalidSeEbookException("Missing `<dc:language>` element in `content.opf`.")

	# Check local.css for various items, for later use
	try:
		with open(self.path / "src" / "epub" / "css" / "local.css", "r", encoding="utf-8") as file:
			self.local_css = file.read()
	except:
		raise se.InvalidSeEbookException(f"Couldn’t open `{self.path / 'src' / 'epub' / 'css' / 'local.css'}`.")

	# cssutils prints warnings/errors to stdout by default, so shut it up here
	cssutils.log.enabled = False

	# Construct a set of CSS selectors and rules in local.css
	# We'll check against this set in each file to see if any of them are unused.
	local_css_rules: Dict[str, str] = {} # A dict where key = selector and value = rules
	duplicate_selectors = []
	single_selectors: List[str] = []
	# cssutils doesn't understand @supports, but it *does* understand @media, so do a replacement here for the purposes of parsing
	for rule in cssutils.parseString(self.local_css.replace("@supports", "@media"), validate=False):
		# i.e. @supports
		if isinstance(rule, cssutils.css.CSSMediaRule):
			for supports_rule in rule.cssRules:
				for selector in supports_rule.selectorList:
					if selector.selectorText not in local_css_rules:
						local_css_rules[selector.selectorText] = ""

					local_css_rules[selector.selectorText] += supports_rule.style.cssText + ";"

		# top-level rule
		if isinstance(rule, cssutils.css.CSSStyleRule):
			for selector in rule.selectorList:
				# Check for duplicate selectors.
				# We consider a selector a duplicate if it's a TOP LEVEL selector (i.e. we don't check within @supports)
				# and ALSO if it is a SINGLE selector (i.e. not multiple selectors separated by ,)
				# For example abbr{} abbr{} would be a duplicate, but not abbr{} abbr,p{}
				if "," not in rule.selectorText:
					if selector.selectorText in single_selectors:
						duplicate_selectors.append(selector.selectorText)
					else:
						single_selectors.append(selector.selectorText)

				local_css_rules[selector.selectorText] = rule.style.cssText + ";"

	if duplicate_selectors:
		messages.append(LintMessage("c-009", "Duplicate CSS selectors. Duplicates are only acceptable if overriding SE base styles.", se.MESSAGE_TYPE_WARNING, "local.css", list(set(duplicate_selectors))))

	# Store a list of CSS selectors, and duplicate it into a list of unused selectors, for later checks
	# We use a regex to remove pseudo-elements like ::before, because we want the *selectors* to see if they're unused.
	local_css_selectors = [regex.sub(r"::[a-z\-]+", "", selector) for selector in local_css_rules]
	unused_selectors = local_css_selectors.copy()

	local_css_has_subtitle_style = False
	local_css_has_halftitle_subtitle_style = False
	local_css_has_poem_style = False
	local_css_has_verse_style = False
	local_css_has_song_style = False
	local_css_has_hymn_style = False
	local_css_has_elision_style = False
	abbr_styles = regex.findall(r"abbr\.[a-z]+", self.local_css)
	missing_styles: List[str] = []

	# Iterate over rules to do some other checks
	selected_h = []
	abbr_with_whitespace = []
	for selector, rules in local_css_rules.items():
		if regex.search(r"^h[0-6]", selector, flags=regex.IGNORECASE):
			selected_h.append(selector)

		if selector == "span[epub|type~=\"subtitle\"]":
			local_css_has_subtitle_style = True

		if selector == "section[epub|type~=\"halftitlepage\"] span[epub|type~=\"subtitle\"]":
			local_css_has_halftitle_subtitle_style = True

		if "z3998:poem" in selector:
			local_css_has_poem_style = True

		if "z3998:verse" in selector:
			local_css_has_verse_style = True

		if "z3998:song" in selector:
			local_css_has_song_style = True

		if "z3998:hymn" in selector:
			local_css_has_hymn_style = True

		if "span.elision" in selector:
			local_css_has_elision_style = True

		if "abbr" in selector and "nowrap" in rules:
			abbr_with_whitespace.append(selector)

		if regex.search(r"\[\s*xml\s*\|", selector, flags=regex.IGNORECASE) and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in self.local_css:
			messages.append(LintMessage("c-003", "`[xml|attr]` selector in CSS, but no XML namespace declared (`@namespace xml \"http://www.w3.org/XML/1998/namespace\";`).", se.MESSAGE_TYPE_ERROR, "local.css"))

	if selected_h:
		messages.append(LintMessage("c-001", "Do not directly select `<h#>` elements, as they are used in template files; use more specific selectors.", se.MESSAGE_TYPE_ERROR, "local.css", selected_h))

	if abbr_with_whitespace:
		messages.append(LintMessage("c-005", "`abbr` selector does not need `white-space: nowrap;` as it inherits it from `core.css`.", se.MESSAGE_TYPE_ERROR, "local.css", abbr_with_whitespace))

	# Don't specify border color
	# Since we have match with a regex anyway, no point in putting it in the loop above
	matches = regex.findall(r"(?:border|color).+?(?:#[a-f0-9]{0,6}|black|white|red)", self.local_css, flags=regex.IGNORECASE)
	if matches:
		messages.append(LintMessage("c-004", "Do not specify border colors, so that reading systems can adjust for night mode.", se.MESSAGE_TYPE_WARNING, "local.css", matches))

	# If we select on the xml namespace, make sure we define the namespace in the CSS, otherwise the selector won't work
	# We do this using a regex and not with cssutils, because cssutils will barf in this particular case and not even record the selector.
	matches = regex.findall(r"\[\s*xml\s*\|", self.local_css)
	if matches and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in self.local_css:
		messages.append(LintMessage("c-003", "`[xml|attr]` selector in CSS, but no XML namespace declared (`@namespace xml \"http://www.w3.org/XML/1998/namespace\";`).", se.MESSAGE_TYPE_ERROR, "local.css"))

	# Done checking local.css

	root_files = os.listdir(self.path)
	expected_root_files = [".git", "images", "src", "LICENSE.md"]
	illegal_files = [x for x in root_files if x not in expected_root_files and x != ".gitignore" and x != "se-lint-ignore.xml"] # .gitignore and se-lint-ignore.xml are optional
	missing_files = [x for x in expected_root_files if x not in root_files and x != "LICENSE.md"] # We add more to this later on. LICENSE.md gets checked later on, so we don't want to add it twice

	for illegal_file in illegal_files:
		messages.append(LintMessage("f-001", "Illegal file or directory.", se.MESSAGE_TYPE_ERROR, illegal_file))

	# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
	try:
		# lxml unescapes this for us
		# Also, remove HTML elements like <a href> so that we don't catch quotation marks in attribute values
		long_description = self.metadata_dom.xpath("/package/metadata/meta[@property='se:long-description']")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", regex.sub(r"<[^<]+?>", "", long_description))
		if matches:
			messages.append(LintMessage("m-014", "Non-typogrified character in `<meta property=\"se:long-description\">` element.", se.MESSAGE_TYPE_ERROR, "content.opf", matches))
	except:
		raise se.InvalidSeEbookException("No `<meta property=\"se:long-description\">` element in `content.opf`.")

	# Check if there are non-typogrified quotes or em-dashes in the title.
	try:
		title = self.metadata_dom.xpath("/package/metadata/dc:title")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", title)
		if matches:
			messages.append(LintMessage("m-012", "Non-typogrified character in `<dc:title>` element.", se.MESSAGE_TYPE_ERROR, "content.opf", matches))
	except:
		missing_metadata_elements.append("<dc:title>")

	try:
		file_as = self.metadata_dom.xpath("/package/metadata/meta[@property='file-as' and @refines='#title']")[0].text
		matches = regex.findall(r".(?:['\"]|\-\-|\s-\s).", file_as)
		if matches:
			messages.append(LintMessage("m-050", "Non-typogrified character in `<meta property=\"file-as\" refines=\"#title\">` element.", se.MESSAGE_TYPE_ERROR, "content.opf", matches))
	except:
		missing_metadata_elements.append("<meta property=\"file-as\" refines=\"#title\">")

	try:
		description = self.metadata_dom.xpath("/package/metadata/dc:description")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", description)
		if matches:
			messages.append(LintMessage("m-013", "Non-typogrified character in `<dc:description>` element.", se.MESSAGE_TYPE_ERROR, "content.opf", matches))
	except:
		missing_metadata_elements.append("<dc:description>")

	# Check for double spacing
	matches = regex.findall(fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}", self.metadata_xml)
	if matches:
		double_spaced_files.append("content.opf")

	# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
	matches = regex.findall(r"[a-zA-Z][”][,\.]", self.metadata_xml)
	if matches:
		messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, "content.opf"))

	# Make sure long-description is escaped HTML
	if "<" not in long_description:
		messages.append(LintMessage("m-016", "Long description must be escaped HTML.", se.MESSAGE_TYPE_ERROR, "content.opf"))
	else:
		# Check for malformed long description HTML
		try:
			etree.parse(io.StringIO(f"<?xml version=\"1.0\"?><html xmlns=\"http://www.w3.org/1999/xhtml\">{long_description}</html>"))
		except lxml.etree.XMLSyntaxError as ex:
			messages.append(LintMessage("m-015", f"Metadata long description is not valid XHTML. LXML says: {ex}", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for HTML entities in long-description, but allow &amp;amp;
	matches = regex.findall(r"&[a-z0-9]+?;", long_description.replace("&amp;", ""))
	if matches:
		messages.append(LintMessage("m-018", "HTML entities found. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, "content.opf", matches))

	# Check for illegal em-dashes in <dc:subject>
	nodes = self.metadata_dom.xpath("/package/metadata/dc:subject[contains(text(), '—')]")
	if nodes:
		messages.append(LintMessage("m-019", "Illegal em-dash in `<dc:subject>` element; use `--`.", se.MESSAGE_TYPE_ERROR, "content.opf", [node.text for node in nodes]))

	# Check for empty production notes
	if self.metadata_dom.xpath("/package/metadata/meta[@property='se:production-notes' and text()='Any special notes about the production of this ebook for future editors/producers? Remove this element if not.']"):
		messages.append(LintMessage("m-022", "Empty `<meta property=\"se:production-notes\">` element.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal VCS URLs
	nodes = self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:url.vcs.github' and not(text() = '{self.generated_github_repo_url}')]")
	if nodes:
		messages.append(LintMessage("m-009", f"`<meta property=\"se:url.vcs.github\">` value does not match expected: `{self.generated_github_repo_url}`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for HathiTrust scan URLs instead of actual record URLs
	if "babel.hathitrust.org" in self.metadata_xml or "hdl.handle.net" in self.metadata_xml:
		messages.append(LintMessage("m-011", "Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: `https://catalog.hathitrust.org/Record/<RECORD-ID>`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for illegal se:subject tags
	illegal_subjects = []
	nodes = self.metadata_dom.xpath("/package/metadata/meta[@property='se:subject']")
	if nodes:
		for node in nodes:
			if node.text not in se.SE_GENRES:
				illegal_subjects.append(node.text)

		if illegal_subjects:
			messages.append(LintMessage("m-020", "Illegal value for `<meta property=\"se:subject\">` element.", se.MESSAGE_TYPE_ERROR, "content.opf", illegal_subjects))
	else:
		messages.append(LintMessage("m-021", "No `<meta property=\"se:subject\">` element found.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check for CDATA tags
	if "<![CDATA[" in self.metadata_xml:
		messages.append(LintMessage("m-017", "`<![CDATA[` found. Run `se clean` to canonicalize `<![CDATA[` sections.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Check that our provided identifier matches the generated identifier
	try:
		identifier = self.metadata_dom.xpath("/package/metadata/dc:identifier")[0].text
		if identifier != self.generated_identifier:
			messages.append(LintMessage("m-023", f"`<dc:identifier>` does not match expected: `{self.generated_identifier}`.", se.MESSAGE_TYPE_ERROR, "content.opf"))
	except:
		missing_metadata_elements.append("<dc:identifier>")

	# Check if se:name.person.full-name matches their titlepage name
	duplicate_names = []
	invalid_refines = []
	nodes = self.metadata_dom.xpath("/package/metadata/meta[@property='se:name.person.full-name']")
	for node in nodes:
		try:
			refines = node.attribute("refines").replace("#", "")
			try:
				name = self.metadata_dom.xpath(f"/package/metadata/*[@id = '{refines}']")[0].text
				if name == node.text:
					duplicate_names.append(name)
			except:
				invalid_refines.append(refines)
		except:
			invalid_refines.append("<meta property=\"se:name.person.full-name\">")

	if duplicate_names:
		messages.append(LintMessage("m-024", "`<meta property=\"se:name.person.full-name\">` property identical to regular name. If the two are identical the full name `<meta>` element must be removed.", se.MESSAGE_TYPE_ERROR, "content.opf", duplicate_names))

	if invalid_refines:
		messages.append(LintMessage("m-010", "Invalid `refines` property.", se.MESSAGE_TYPE_ERROR, "content.opf", invalid_refines))

	# Check for malformed URLs
	messages = messages + _get_malformed_urls(self.metadata_xml, "content.opf")

	if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", self.metadata_xml):
		messages.append(LintMessage("m-008", "id.loc.gov URL ending with illegal `.html`.", se.MESSAGE_TYPE_ERROR, "content.opf"))

	# Does the manifest match the generated manifest?
	try:
		manifest = self.metadata_dom.xpath("/package/manifest")[0]
		if manifest.tostring().replace("\t", "") != self.generate_manifest().replace("\t", ""):
			messages.append(LintMessage("m-042", "`<manifest>` element does not match expected structure.", se.MESSAGE_TYPE_ERROR, "content.opf"))
	except:
		missing_metadata_elements.append("<manifest>")

	if missing_metadata_elements:
		messages.append(LintMessage("m-051", "Missing expected element in metadata.", se.MESSAGE_TYPE_ERROR, "content.opf", missing_metadata_elements))

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

	# Now iterate over individual files for some checks
	for root, _, filenames in os.walk(self.path):
		for filename in natsorted(filenames):
			if ".git" in str(Path(root) / filename):
				continue

			if filename.endswith(".jpeg"):
				messages.append(LintMessage("f-011", "JPEG files must end in `.jpg`.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.endswith(".tiff"):
				messages.append(LintMessage("f-012", "TIFF files must end in `.tif`.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.startswith("cover.source."):
				has_cover_source = True

			if "-0" in filename:
				messages.append(LintMessage("f-009", "Illegal leading `0` in filename.", se.MESSAGE_TYPE_ERROR, filename))

			if Path(filename).stem != "LICENSE":
				url_safe_filename = se.formatting.make_url_safe(Path(filename).stem) + Path(filename).suffix
				if filename != url_safe_filename and not Path(filename).stem.endswith(".source"):
					messages.append(LintMessage("f-008", f"Filename is not URL-safe. Expected: `{url_safe_filename}`.", se.MESSAGE_TYPE_ERROR, filename))

			if filename == "cover.jpg":
				try:
					image = Image.open(Path(root) / filename)
					if image.size != (1400, 2100):
						messages.append(LintMessage("s-051", "Wrong height or width. `cover.jpg` must be exactly 1400 × 2100.", se.MESSAGE_TYPE_ERROR, filename))

				except UnidentifiedImageError:
					raise se.InvalidFileException(f"Couldn’t identify image type of `{filename}`.")

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

				if filename.endswith(".svg"):
					svg_dom = _dom(Path(root) / filename)

					# Check for fill: #000 which should simply be removed
					nodes = svg_dom.xpath("//*[contains(@fill, '#000') or contains(translate(@style, ' ', ''), 'fill:#000')]")
					if nodes:
						messages.append(LintMessage("x-004", "Illegal `style=\"fill: #000\"` or `fill=\"#000\"`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for illegal height or width on root <svg> element
					if filename != "logo.svg": # Do as I say, not as I do...
						if svg_dom.xpath("//svg[@height or @width]"):
							messages.append(LintMessage("x-005", "Illegal `height` or `width` attribute on root `<svg>` element. Size SVGs using the `viewBox` attribute only.", se.MESSAGE_TYPE_ERROR, filename))

					match = regex.search(r"viewbox", file_contents, flags=regex.IGNORECASE)
					if match and match[0] != "viewBox":
							messages.append(LintMessage("x-006", f"`{match}` found instead of `viewBox`. `viewBox` must be correctly capitalized.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for illegal transform or id attribute
					nodes = svg_dom.xpath("//*[@transform or @id]")
					if nodes:
						invalid_transform_attributes = set()
						invalid_id_attributes = []
						for node in nodes:
							if node.attribute("transform"):
								invalid_transform_attributes.add(f"transform=\"{node.attribute('transform')}\"")

							if node.attribute("id"):
								invalid_id_attributes.append(f"id=\"{node.attribute('id')}\"")

						if invalid_transform_attributes:
							messages.append(LintMessage("x-003", "Illegal `transform` attribute. SVGs should be optimized to remove use of `transform`. Try using Inkscape to save as an “optimized SVG”.", se.MESSAGE_TYPE_ERROR, filename, invalid_transform_attributes))

						if invalid_id_attributes:
							messages.append(LintMessage("x-014", "Illegal `id` attribute.", se.MESSAGE_TYPE_ERROR, filename, invalid_id_attributes))

					if f"{os.sep}src{os.sep}" not in root:
						# Check that cover and titlepage images are in all caps
						if filename == "cover.svg":
							nodes = svg_dom.xpath("//text[re:test(., '[a-z]')]")
							if nodes:
								messages.append(LintMessage("s-002", "Lowercase letters in cover. Cover text must be all uppercase.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

							# For later comparison with titlepage
							cover_svg_title = svg_dom.xpath("/svg/title/text()", True).replace("The cover for ", "") # <title> can appear on any element in SVG, but we only want to check the root one

						if filename == "titlepage.svg":
							nodes = svg_dom.xpath("//text[re:test(., '[a-z]') and not(text() = 'translated by' or text() = 'illustrated by' or text() = 'and')]")
							if nodes:
								messages.append(LintMessage("s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except `translated by` and `illustrated by`.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

							# For later comparison with cover
							titlepage_svg_title = svg_dom.xpath("/svg/title/text()", True).replace("The titlepage for ", "") # <title> can appear on any element in SVG, but we only want to check the root one

				if filename.endswith(".xhtml"):
					# Read file contents into a DOM for querying
					dom = _dom(Path(root) / filename)

					messages = messages + _get_malformed_urls(file_contents, filename)

					if filename == "titlepage.xhtml":
						if not dom.xpath("/html/head/title[text() = 'Titlepage']"):
							messages.append(LintMessage("s-025", "Titlepage `<title>` elements must contain exactly: `Titlepage`.", se.MESSAGE_TYPE_ERROR, filename))

					if filename == "halftitle.xhtml":
						has_halftitle = True
						if not dom.xpath("/html/head/title[text() = 'Half Title']"):
							messages.append(LintMessage("s-024", "Half title `<title>` elements must contain exactly: \"Half Title\".", se.MESSAGE_TYPE_ERROR, filename))

					if filename == "colophon.xhtml":
						se_url = self.generated_identifier.replace('url:', '')
						if not dom.xpath(f"//a[@href = '{se_url}' and text() = '{se_url.replace('https://', '')}']"):
							messages.append(LintMessage("m-035", f"Unexpected SE identifier in colophon. Expected: `{se_url}`.", se.MESSAGE_TYPE_ERROR, filename))

						if ">trl<" in self.metadata_xml and "translated from" not in file_contents:
							messages.append(LintMessage("m-025", "Translator found in metadata, but no `translated from LANG` block in colophon.", se.MESSAGE_TYPE_ERROR, filename))

						# Check if we forgot to fill any variable slots
						missing_colophon_vars = [x for x in COLOPHON_VARIABLES if regex.search(fr"\b{x}\b", file_contents)]
						if missing_colophon_vars:
							messages.append(LintMessage("m-036", "Missing data in colophon.", se.MESSAGE_TYPE_ERROR, filename, missing_colophon_vars))

						# Check that we have <br/>s at the end of lines
						# First, check for b or a elements that are preceded by a newline but not by a br
						nodes = [node.tostring() for node in dom.xpath("/html/body/section/p/*[name() = 'b' or name() = 'a'][(preceding-sibling::node()[1])[contains(., '\n')]][not((preceding-sibling::node()[2])[self::br]) or (normalize-space(preceding-sibling::node()[1]) and re:test(preceding-sibling::node()[1], '\\n\\s*$')) ]")]
						# Next, check for text nodes that contain newlines but are not preceded by brs
						nodes = nodes + [node.strip() for node in dom.xpath("/html/body/section/p/text()[contains(., '\n') and normalize-space(.)][(preceding-sibling::node()[1])[not(self::br)]]")]
						if nodes:
							messages.append(LintMessage("s-053", "Colophon line not preceded by `<br/>`.", se.MESSAGE_TYPE_ERROR, filename, nodes))

						# Are the sources represented correctly?
						# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
						nodes = self.metadata_dom.xpath("/package/metadata/dc:source")
						if len(nodes) <= 2:
							for node in nodes:
								link = node.text
								if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
									messages.append(LintMessage("m-037", f"Source not represented in colophon.xhtml. Expected: `<a href=\"{link}\">Project Gutenberg</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "hathitrust.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
									messages.append(LintMessage("m-038", f"Source not represented in colophon.xhtml. Expected: `the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "archive.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">Internet Archive</a>" not in file_contents:
									messages.append(LintMessage("m-039", f"Source not represented in colophon.xhtml. Expected: `the<br/> <a href=\"{link}\">Internet Archive</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "books.google.com" in link and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
									messages.append(LintMessage("m-040", f"Source not represented in colophon.xhtml. Expected: `<a href=\"{link}\">Google Books</a>`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for unused selectors
					if not filename.endswith("titlepage.xhtml") and not filename.endswith("imprint.xhtml") and not filename.endswith("uncopyright.xhtml"):
						for selector in local_css_selectors:
							try:
								sel = se.easy_xml.css_selector(selector)
							except lxml.cssselect.ExpressionError as ex:
								# This gets thrown on some selectors not yet implemented by lxml, like *:first-of-type
								unused_selectors.remove(selector)
								continue
							except Exception as ex:
								raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: `{selector}`\n`lxml` says: {ex}")

							if dom.xpath(sel.path):
								unused_selectors.remove(selector)

					# Update our list of local.css selectors to check in the next file
					local_css_selectors = list(unused_selectors)

					# Done checking for unused selectors.

					# Check if this is a frontmatter file
					if filename not in ("titlepage.xhtml", "imprint.xhtml", "toc.xhtml"):
						if dom.xpath("//*[contains(@epub:type, 'frontmatter')]"):
							has_frontmatter = True

					# Add new CSS classes to global list
					if filename not in se.IGNORED_FILENAMES:
						for node in dom.xpath("//*[@class]"):
							for css_class in node.attribute("class").split():
								if css_class in xhtml_css_classes:
									xhtml_css_classes[css_class] += 1
								else:
									xhtml_css_classes[css_class] = 1

					if filename != "toc.xhtml":
						for node in dom.xpath("//*[re:test(name(), '^h[1-6]$')]"):
							# Decide whether to remove subheadings based on the following logic:
							# If the closest parent <section> or <article> is a part, division, or volume, then keep subtitle
							# Else, if the closest parent <section> or <article> is a halftitlepage, then discard subtitle
							# Else, if the first child of the heading is not z3998:roman, then also discard subtitle
							# Else, keep the subtitle.
							node_copy = deepcopy(node)

							for noteref_node in node_copy.xpath(".//a[contains(@epub:type, 'noteref')]"):
								noteref_node.remove()

							heading_subtitle = node_copy.xpath(".//*[contains(@epub:type, 'subtitle')]")

							if heading_subtitle:
								# If an <h#> tag has a subtitle, the non-subtitle text must also be wrapped in a <span>.
								# This xpath returns all text nodes that are not white space. We don't want any text nodes,
								# so if it returns anything then we know we're missing a <span> somewhere.
								if node_copy.xpath("./text()[not(normalize-space(.) = '')]"):
									messages.append(LintMessage("s-015", f"Element has `<span epub:type=\"subtitle\">` child, but first child is not `<span>`. See semantics manual for structure of headers with subtitles.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring()]))

								# OK, move on with processing headers.
								closest_section_epub_type = node.xpath(".//ancestor::*[name()='section' or name()='article' or name()='body'][1]/@epub:type", True) or ""
								heading_first_child_epub_type = node_copy.xpath("./span/@epub:type", True) or ""

								if regex.search(r"(part|division|volume)", closest_section_epub_type) and "se:short-story" not in closest_section_epub_type:
									remove_subtitle = False
								elif "halftitlepage" in closest_section_epub_type:
									remove_subtitle = True
								elif "z3998:roman" not in heading_first_child_epub_type:
									remove_subtitle = True
								else:
									remove_subtitle = False

								if remove_subtitle:
									heading_subtitle[0].remove()

							normalized_text = " ".join(node_copy.inner_text().split())
							headings = headings + [(normalized_text, filename)]

					# Check for direct z3998:roman spans that should have their semantic pulled into the parent element
					nodes = dom.xpath("//span[contains(@epub:type, 'z3998:roman')][not(preceding-sibling::*)][not(following-sibling::*)][not(preceding-sibling::text()[normalize-space(.)])][not(following-sibling::text()[normalize-space(.)])]")
					if nodes:
						messages.append(LintMessage("s-029", "If a `<span>` exists only for the `z3998:roman` semantic, then `z3998:roman` should be pulled into parent element instead.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check for z3998:roman elements with invalid values
					nodes = dom.xpath("//*[contains(@epub:type, 'z3998:roman')][re:test(text(), '[^ivxlcdmIVXLCDM]')]")
					if nodes:
						messages.append(LintMessage("s-026", "Invalid Roman numeral.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check for "Hathi Trust" instead of "HathiTrust"
					if "Hathi Trust" in file_contents:
						messages.append(LintMessage("m-041", "`Hathi Trust` should be `HathiTrust`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for uppercase letters in IDs or classes
					nodes = dom.xpath("//*[re:test(@id, '[A-Z]') or re:test(@class, '[A-Z]') or re:test(@epub:type, '[A-Z]')]")
					if nodes:
						messages.append(LintMessage("x-002", "Uppercase in attribute value. Attribute values must be all lowercase.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					nodes = dom.xpath("//*[re:test(@id, '^[0-9]+')]")
					if nodes:
						messages.append(LintMessage("x-007", "`id` attributes starting with a number are illegal XHTML.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					# Check for <section> and <article> without ID attribute
					nodes = dom.xpath("//*[self::section or self::article][not(@id)]")
					if nodes:
						messages.append(LintMessage("s-011", "Element without `id` attribute.", se.MESSAGE_TYPE_ERROR, filename, {node.totagstring() for node in nodes}))

					# Check for numeric entities
					matches = regex.findall(r"&#[0-9]+?;", file_contents)
					if matches:
						messages.append(LintMessage("s-001", "Illegal numeric entity (like `&#913;`).", se.MESSAGE_TYPE_ERROR, filename))

					# Check nested <blockquote> elements, but only if it's the first child of another <blockquote>
					nodes = dom.xpath("//blockquote/*[1][name()='blockquote']")
					if nodes:
						messages.append(LintMessage("s-005", "Nested `<blockquote>` element.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for <hr> tags before the end of a section, which is a common PG artifact
					if dom.xpath("//hr[count(following-sibling::*) = 0]"):
						messages.append(LintMessage("s-012", "Illegal `<hr/>` as last child.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for space after dash
					nodes = dom.xpath("//*[name() = 'p' or name() = 'span' or name = 'em' or name = 'i' or name = 'b' or name = 'strong'][not(self::comment())][re:test(., '[a-zA-Z]-\\s(?!(and|or|nor|to|und|…)\\b)')]")
					if nodes:
						messages.append(LintMessage("t-033", "Space after dash.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					# Check for double greater-than at the end of a tag
					matches = regex.findall(r"(>>|>&gt;)", file_contents)
					if matches:
						messages.append(LintMessage("x-008", "Elements should end with a single `>`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for periods followed by lowercase.
					temp_xhtml = regex.sub(r"<title>.+?</title>", "", file_contents) # Remove <title> because it might contain something like <title>Chapter 2: The Antechamber of M. de Tréville</title>
					temp_xhtml = regex.sub(r"<abbr[^>]*?>", "<abbr>", temp_xhtml) # Replace things like <abbr xml:lang="la">
					temp_xhtml = regex.sub(r"<img[^>]*?>", "", temp_xhtml) # Remove <img alt> attributes
					temp_xhtml = temp_xhtml.replace("A.B.C.", "X") # Remove A.B.C, which is not an abbreviations.
					# Note the regex also excludes preceding numbers, so that we can have inline numbering like:
					# "A number of questions: 1. regarding those who make heretics; 2. concerning those who were made heretics..."
					matches = regex.findall(r"[^\s0-9]+\.\s+[a-z](?!’[A-Z])[a-z]+", temp_xhtml)
					# If <abbr> is in the match, remove it from the matches so we exclude things like <abbr>et. al.</abbr>
					matches = [match for match in matches if "<abbr>" not in match]
					if matches:
						messages.append(LintMessage("t-029", "Period followed by lowercase letter. Hint: Abbreviations require an `<abbr>` element.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Ignore the title page here, because we often have publishers with ampersands as
					# translators, but in alt tags. Like "George Allen & Unwin".
					if filename != "titlepage.xhtml":
						# Before we process this, we remove the eoc class from <abbr class="name"> because negative lookbehind
						# must be fixed-width. I.e. we can't do `class="name( eoc)?"`
						temp_file_contents = file_contents.replace("\"name eoc\"", "\"name\"")

						# Check for nbsp before ampersand (&amp)
						matches = regex.findall(fr"(?<!\<abbr class=\"name\")[^>]*? \&amp;", temp_file_contents)
						if matches:
							messages.append(LintMessage("t-007", "Required no-break space not found before `&amp;`.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for nbsp after ampersand (&amp)
						matches = regex.findall(fr"(?<!\<abbr class=\"name\")>[^>]*?\&amp; ", temp_file_contents)
						if matches:
							messages.append(LintMessage("t-008", "Required no-break space not found after `&amp;`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for nbsp before times
					nodes = dom.xpath(f"//text()[re:test(., '[0-9][^{se.NO_BREAK_SPACE}]?$')][(following-sibling::abbr[1])[contains(@class, 'time')]]")
					if nodes:
						messages.append(LintMessage("t-009", "Required no-break space not found before `<abbr class=\"time\">`.", se.MESSAGE_TYPE_WARNING, filename, [node[-10:] + "<abbr" for node in nodes]))

					# Check for low-hanging misquoted fruit
					matches = regex.findall(r"[A-Za-z]+[“‘]", file_contents) + regex.findall(r"[^>]+</(?:em|i|b|span)>‘[a-z]+", file_contents)
					if matches:
						messages.append(LintMessage("t-028", "Possible mis-curled quotation mark.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check that times have colons and not periods
					nodes = dom.xpath(f"//text()[ (re:test(., '[0-9]\\.[0-9]+\\s$') and (following-sibling::abbr[1])[contains(@class, 'time')]) or re:test(., '(at|the) [0-9]\\.[0-9]+$')]")
					if nodes:
						messages.append(LintMessage("t-010", "Times must be separated by colons (`:`) not periods (`.`).", se.MESSAGE_TYPE_ERROR, filename, [node[-10:] + "<abbr" for node in nodes]))

					# Check for leading 0 in IDs (note: not the same as checking for IDs that start with an integer)
					nodes = dom.xpath("//*[contains(@id, '-0')]")
					if nodes:
						messages.append(LintMessage("x-009", "Illegal leading 0 in `id` attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					# Check for stage direction that ends in ?! but also has a trailing period
					nodes = dom.xpath("//i[contains(@epub:type, 'z3998:stage-direction')][re:test(., '\\.$')][(following-sibling::node()[1])[re:test(., '^[,:;!?]')]]")
					if nodes:
						messages.append(LintMessage("t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check for ending punctuation inside italics that have semantics.
					# Ignore the colophon because paintings might have punctuation in their names
					if filename != "colophon.xhtml":
						# This xpath matches b or i elements with epub:type="se:name...", that are not stage direction, whose last text node ends in punctuation.
						# Note that we check that the last node is a text node, because we may have <abbr> a sthe last node
						matches = [node.tostring() for node in dom.xpath("(//b | //i)[contains(@epub:type, 'se:name') and not(contains(@epub:type, 'z3998:stage-direction'))][(text()[last()])[re:test(., '[\\.,!\\?]$')]]")]

						# ...and also check for ending punctuation inside em tags, if it looks like a *part* of a clause
						# instead of a whole clause. If the <em> is preceded by an em dash or quotes, or if there's punctuation
						# and a space bofore it, then it's presumed to be a whole clause.
						# We can't use xpath for this one because xpath's regex engine doesn't seem to work with {1,2}
						matches = matches + [match.strip() for match in regex.findall(r"(?<!.[—“‘]|[!\.\?…]\s)<em>(?:\w+?\s*){1,2}?[\.,\!\?]</em>", file_contents) if match.islower()]

						if matches:
							messages.append(LintMessage("t-017", "Ending punctuation inside italics. Ending punctuation is only allowed within italics if the phrase is an independent clause.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for <table> tags without a <tbody> child
					if dom.xpath("//table[not(tbody)]"):
						messages.append(LintMessage("s-042", "`<table>` element without `<tbody>` child.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for money not separated by commas
					matches = regex.findall(r"[£\$][0-9]{4,}", file_contents)
					if matches:
						messages.append(LintMessage("t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for deprecated MathML elements
					# Note we dont select directly on element name, because we want to ignore any namespaces that may (or may not) be defined
					nodes = dom.xpath("//*[name()='mfenced']")
					if nodes:
						messages.append(LintMessage("s-017", f"`<m:mfenced>` is deprecated in the MathML spec. Use `<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>`.", se.MESSAGE_TYPE_ERROR, filename, {node.totagstring() for node in nodes}))

					# Check for period following Roman numeral, which is an old-timey style we must fix
					# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
					nodes = dom.xpath("//node()[name()='span' and contains(@epub:type, 'z3998:roman') and not(position() = 1)][(following-sibling::node()[1])[re:test(., '^\\.\\s*[a-z]')]]")
					if nodes:
						messages.append(LintMessage("t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() + "." for node in nodes]))

					# Check for two em dashes in a row
					matches = regex.findall(fr"—{se.WORD_JOINER}*—+", file_contents)
					if matches:
						messages.append(LintMessage("t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename))

					nodes = dom.xpath("//blockquote//p[parent::*[name() = 'footer'] or parent::*[name() = 'blockquote']]//cite") # Sometimes the <p> may be in a <footer>
					if nodes:
						messages.append(LintMessage("s-054", "`<cite>` as child of `<p>` in `<blockquote>`. `<cite>` should be the direct child of `<blockquote>`.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check for empty <h2> missing epub:type="title" attribute
					if dom.xpath("//h2[not(contains(@epub:type, 'title'))]"):
						messages.append(LintMessage("s-009", "`<h2>` element without `epub:type=\"title\"` attribute.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for a common typo
					if "z3998:nonfiction" in file_contents:
						messages.append(LintMessage("s-030", "`z3998:nonfiction` should be `z3998:non-fiction`.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for initialisms without periods
					nodes = [node.tostring() for node in dom.xpath("//abbr[contains(@class, 'initialism') and not(re:test(., '^([a-zA-Z]\\.)+$'))]") if node.text not in initialism_exceptions]
					if nodes:
						messages.append(LintMessage("t-030", "Initialism with spaces or without periods.", se.MESSAGE_TYPE_WARNING, filename, set(nodes)))

					# Check for <abbr class="name"> that does not contain spaces
					nodes = dom.xpath("//abbr[contains(@class, 'name')][re:test(., '[A-Z]\\.[A-Z]\\.')]")
					if nodes:
						messages.append(LintMessage("t-016", "Initials in `<abbr class=\"name\">` not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					# Check for abbreviations followed by periods
					# But we exclude some SI units, which don't take periods, and some Imperial abbreviations that are multi-word
					nodes = dom.xpath("//abbr[(contains(@class, 'initialism') or contains(@class, 'name') or not(@class))][not(re:test(., '[cmk][mgl]')) and not(text()='mpg' or text()='mph' or text()='hp' or text()='TV')][following-sibling::text()[1][starts-with(self::text(), '.')]]")

					if nodes:
						messages.append(LintMessage("t-032", "Initialism or name followed by period. Hint: Periods go within `<abbr>`. `<abbr>`s containing periods that end a clause require the `eoc` class.", se.MESSAGE_TYPE_WARNING, filename, [f"{node.tostring()}." for node in nodes]))

					# Check for block-level tags that end with <br/>
					nodes = dom.xpath("//*[self::p or self::blockquote or self::table or self::ol or self::ul or self::section or self::article][br[last()][not(following-sibling::text()[normalize-space()])][not(following-sibling::*)]]")
					if nodes:
						messages.append(LintMessage("s-008", "`<br/>` element found before closing tag of block-level element.", se.MESSAGE_TYPE_ERROR, filename, {node.totagstring() for node in nodes}))

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

					# Check for trailing commas inside <i> tags at the close of dialog
					# More sophisticated version of: \b[^\s]+?,</i>”
					nodes = dom.xpath("//i[re:test(., ',$')][(following-sibling::node()[1])[starts-with(., '”')]]")
					if nodes:
						messages.append(LintMessage("t-023", "Comma inside `<i>` element before closing dialog.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() + "”" for node in nodes]))

					# Check for quotation marks in italicized dialog
					nodes = dom.xpath("//i[@xml:lang][starts-with(., '“') or re:test(., '”$')]")
					if nodes:
						messages.append(LintMessage("t-024", "When italicizing language in dialog, italics go inside quotation marks.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check for style attributes
					nodes = dom.xpath("//*[@style]")
					if nodes:
						messages.append(LintMessage("x-012", "Illegal `style` attribute. Do not use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename, {node.totagstring() for node in nodes}))

					# Check for illegal elements in <head>
					nodes = dom.xpath("/html/head/*[not(self::title) and not(self::link[@rel='stylesheet'])]")
					if nodes:
						messages.append(LintMessage("x-015", f"Illegal element in `<head>`. Only `<title>` and `<link rel=\"stylesheet\">` are allowed.", se.MESSAGE_TYPE_ERROR, filename, [f"<{node.lxml_element.tag}>" for node in nodes]))

					# Check for uppercase HTML tags
					nodes = dom.xpath("//*[re:test(name(), '[A-Z]')]")
					for node in nodes:
						messages.append(LintMessage("x-011", "Uppercased HTML tag.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					# Check for nbsp within <abbr class="name">, which is redundant
					nodes = dom.xpath(f"//abbr[contains(@class, 'name')][contains(text(), '{se.NO_BREAK_SPACE}')]")
					if nodes:
						messages.append(LintMessage("t-022", "No-break space found in `<abbr class=\"name\">`. This is redundant.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					# Check for empty elements. Elements are empty if they have no children and no non-whitespace text
					empty_elements = [node.tostring() for node in dom.xpath("//*[not(self::br) and not(self::hr) and not(self::img) and not(self::td) and not(self::th) and not(self::link)][not(*)][not(normalize-space())]")]
					if empty_elements:
						messages.append(LintMessage("s-010", "Empty element. Use `<hr/>` for thematic breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename, empty_elements))

					# Check for HTML tags in <title> tags
					nodes = dom.xpath("/html/head/title/*")
					if nodes:
						messages.append(LintMessage("x-010", "Illegal element in `<title>` element.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					# Check for legal cases that aren't italicized
					# We can't use this because v. appears as short for "volume", and we may also have sporting events without italics.
					#nodes = dom.xpath("//abbr[text() = 'v.' or text() = 'versus'][not(parent::i)]")
					#if nodes:
					#	messages.append(LintMessage("t-123", "Legal case without parent `<i>`.", se.MESSAGE_TYPE_WARNING, filename, {f"{node.tostring()}." for node in nodes}))

					unexpected_titles = []
					# Only do this check if there's one <h#> tag. If there's more than one, then the xhtml file probably requires an overarching title
					if len(dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')]")) == 1:
						# If the chapter has a number and no subtitle, check the <title> tag...
						nodes = dom.xpath("/html/body//*[contains(concat(' ', @epub:type, ' '), ' title ') and contains(@epub:type, 'z3998:roman')][re:test(name(), '^h[1-6]$')]")
						if nodes:
							try:
								chapter_number = roman.fromRoman(nodes[0].inner_text())

								if not dom.xpath(f"/html/head/title[re:match(., '(Chapter|Section|Part) {chapter_number}')]"):
									unexpected_titles.append((f"Chapter {chapter_number}", filename))

							except Exception:
								messages.append(LintMessage("s-035", f"`{nodes[0].totagstring()}` element has the `z3998:roman` semantic, but is not a Roman numeral.", se.MESSAGE_TYPE_ERROR, filename))

						# If the chapter has a number and subtitle, check the <title> tag...
						nodes = dom.xpath("/html/body//*[contains(concat(' ', @epub:type, ' '), ' title ')][re:test(name(), '^h[1-6]$')][(./span[1])[contains(@epub:type, 'z3998:roman')]][(./span[2])[contains(@epub:type, 'subtitle')]]")
						if nodes:
							chapter_number = roman.fromRoman(nodes[0].lxml_element[0].text)

							subtitle_node = se.easy_xml.EasyXmlElement(deepcopy(nodes[0].lxml_element[1]))

							# First, remove endnotes in the subtitle
							for noteref_node in subtitle_node.xpath("./a[contains(@epub:type, 'noteref')]"):
								noteref_node.remove()

							# Now remove all other tags (but not tag contents)
							chapter_title = subtitle_node.inner_text()

							if not dom.xpath(f"/html/head/title[re:match(., '(Chapter|Section|Part) {chapter_number}: {regex.escape(chapter_title)}')]"):
								unexpected_titles.append((f"Chapter {chapter_number}: {chapter_title}", filename))

					# Now, we try to select the first <h#> element in a <section> or <article>.
					# If it doesn't have children and its content is a text string, check to see
					# if the <title> tag matches. This catches for example <h2 epub:type="title">Introduction</h2>
					# However, skip this step if the file contains 3+ <article> tags at the top level. That makes it likely
					# that the book is a collection (like a poetry collection) and so the <title> tag can't be inferred.
					if len(dom.xpath("/html/body/article")) <= 3:
						# The xpath count(preceding-sibling::section) = 0 emulates :first-child
						# Select the first <h#> element with no <span> children that is the child of the first <section> or <article>
						nodes = dom.xpath("(/html/body//*[ (name()='section' and count(preceding-sibling::section) = 0) or (name()='article' and count(preceding-sibling::article) = 0)]//*[re:test(name(), '^h[1-6]$')])[1][contains(concat(' ', @epub:type, ' '), ' title ') and not(contains(concat(' ', @epub:type, ' '), ' z3998:roman '))][not(span)]")
						if nodes:
							node_copy = deepcopy(nodes[0])

							for noteref_node in node_copy.xpath(".//a[contains(@epub:type, 'noteref')]"):
								noteref_node.remove()

							title = node_copy.inner_text()
							if not dom.xpath(f"/html/head/title[text()='{title}']"):
								unexpected_titles.append((title, filename))

					for title, title_filename in unexpected_titles:
						messages.append(LintMessage("s-021", f"Unexpected value for `<title>` element. Expected: `{title}`. (Beware hidden Unicode characters!)", se.MESSAGE_TYPE_ERROR, title_filename))

					# Check for missing subtitle styling
					# Half titles have slightly different subtitle styles than regular subtitles
					if filename == "halftitle.xhtml":
						if not local_css_has_halftitle_subtitle_style:
							missing_styles += [node.totagstring() for node in dom.xpath("/html/body//*[contains(@epub:type, 'subtitle')]")]
					else:
						if not local_css_has_subtitle_style:
							missing_styles += [node.totagstring() for node in dom.xpath("/html/body//*[contains(@epub:type, 'subtitle')]")]

					if not local_css_has_elision_style:
						missing_styles += [node.totagstring() for node in dom.xpath("/html/body//span[contains(@class, 'elision')]")]

					matches = regex.findall(r"\bA\s*B\s*C\s*\b", file_contents)
					if matches:
						messages.append(LintMessage("t-031", "`A B C` must be set as `A.B.C.` It is not an abbreviation.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for <li> elements that don't have a direct block child
					# allow white space and comments before the first child
					if filename not in ("toc.xhtml", "loi.xhtml"):
						nodes = dom.xpath("//li[(node()[normalize-space(.) and not(self::comment())])[1][not(name()='p' or name()='blockquote' or name()='div' or name()='table' or name()='header' or name()='ul' or name()='ol')]]")
						if nodes:
							messages.append(LintMessage("s-007", "`<li>` element without direct block-level child.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

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
					nodes = dom.xpath("//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6][@id]")
					if nodes:
						messages.append(LintMessage("s-019", "`<h#>` element with `id` attribute. `<h#>` elements should be wrapped in `<section>` elements, which should hold the `id` attribute.", se.MESSAGE_TYPE_WARNING, filename, [node.totagstring() for node in nodes]))

					# Check for <cite> preceded by em dash
					nodes = dom.xpath("/html/body//cite[(preceding-sibling::node()[1])[re:match(., '—$')]]")
					if nodes:
						messages.append(LintMessage("t-034", "`<cite>` element preceded by em-dash. Hint: em-dashes go within `<cite>` elements.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check for <cite> without preceding space in text node. (preceding ( or [ are also OK)
					nodes = dom.xpath("/html/body//cite[(preceding-sibling::node()[1])[not(re:match(., '[\\[\\(\\s]$'))]]")
					if nodes:
						messages.append(LintMessage("t-035", "`<cite>` element not preceded by space.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# Check to see if <h#> tags are correctly titlecased
					nodes = dom.xpath("//*[re:test(name(), '^h[1-6]$')][not(contains(@epub:type, 'z3998:roman'))]")
					for node in nodes:
						node_copy = deepcopy(node)

						# Remove *leading* Roman spans
						# This matches the first child node excluding white space nodes, if it contains the z3998:roman semantic.
						for element in node_copy.xpath("./node()[normalize-space(.)][1][contains(@epub:type, 'z3998:roman')]"):
							element.remove()

						# Remove noterefs
						for element in node_copy.xpath(".//a[contains(@epub:type, 'noteref')]"):
							element.remove()

						# Remove hidden elements, for example in poetry identified by first line (keats)
						for element in node_copy.xpath(".//*[@hidden]"):
							element.remove()

						title = node_copy.inner_xml()

						# Remove leading leftover spacing and punctuation
						title = regex.sub(r"^[\s\.\,\!\?\:\;]*", "", title)

						# Normalize whitespace
						title = regex.sub(r"\s+", " ", title, flags=regex.DOTALL).strip()

						# Remove nested <span>s in subtitles, which might trip up the next regex block
						# We can't do this with the lxml element because it has no unwrap() function. remove() is not the same thing--
						# we want to keep the tag contents.
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
							titlecased_title = se.formatting.titlecase(se.formatting.remove_tags(title))
							title = se.formatting.remove_tags(title)
							if title != titlecased_title:
								messages.append(LintMessage("s-023", f"Title `{title}` not correctly titlecased. Expected: `{titlecased_title}`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check for <figure> tags without id attributes
					nodes = dom.xpath("//img[@id]")
					if nodes:
						messages.append(LintMessage("s-018", "`<img>` element with `id` attribute. `id` attributes go on parent `<figure>` elements.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					# Check for closing dialog without comma
					matches = regex.findall(r"[a-z]+?” [a-zA-Z]+? said", file_contents)
					if matches:
						messages.append(LintMessage("t-005", "Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check alt attributes on images, except for the logo
					nodes = dom.xpath("//img[not(re:test(@src, '/logo.svg$'))]")
					img_no_alt = []
					img_alt_not_typogrified = []
					img_alt_lacking_punctuation = []
					for node in nodes:
						alt = node.lxml_element.get("alt")

						if alt:
							# Check for non-typogrified img alt attributes
							if regex.search(r"""('|"|--|\s-\s|&quot;)""", alt):
								img_alt_not_typogrified.append(node.totagstring())

							# Check alt attributes not ending in punctuation
							if filename not in se.IGNORED_FILENAMES and not regex.search(r"""[\.\!\?]”?$""", alt):
								img_alt_lacking_punctuation.append(node.totagstring())

							# Check that alt attributes match SVG titles
							img_src = node.lxml_element.get("src")
							if img_src and img_src.endswith("svg"):
								title_text = ""
								image_ref = img_src.split("/").pop()
								try:
									svg_dom = _dom(self.path / "src" / "epub" / "images" / image_ref)
									try:
										title_text = svg_dom.xpath("/svg/title")[0].text
									except Exception:
										messages.append(LintMessage("s-027", f"{image_ref} missing `<title>` element.", se.MESSAGE_TYPE_ERROR, image_ref))

									if title_text != "" and alt != "" and title_text != alt:
										messages.append(LintMessage("s-022", f"The `<title>` element of `{image_ref}` does not match the `alt` attribute text in `{filename}`.", se.MESSAGE_TYPE_ERROR, filename))

								except FileNotFoundError:
									missing_files.append(str(Path(f"src/epub/images/{image_ref}")))

						else:
							img_no_alt.append(node.totagstring())

					if img_alt_not_typogrified:
						messages.append(LintMessage("t-025", "Non-typogrified `'`, `\"` (as `&quot;`), or `--` in image `alt` attribute.", se.MESSAGE_TYPE_ERROR, filename, img_alt_not_typogrified))

					if img_alt_lacking_punctuation:
						messages.append(LintMessage("t-026", "`alt` attribute does not appear to end with punctuation. `alt` attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename, img_alt_lacking_punctuation))

					if img_no_alt:
						messages.append(LintMessage("s-004", "`img` element missing `alt` attribute.", se.MESSAGE_TYPE_ERROR, filename, img_no_alt))

					# Check for punctuation after endnotes
					nodes = dom.xpath(f"//a[contains(@epub:type, 'noteref')][(following-sibling::node()[1])[re:test(., '^[^\\s<–\\]\\)—{se.WORD_JOINER}]')]]")
					if nodes:
						messages.append(LintMessage("t-020", "Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename, [node.totagstring() for node in nodes]))

					# Check for whitespace before noteref
					# Do this early because we remove noterefs from headers later
					nodes = dom.xpath("//a[contains(@epub:type, 'noteref') and re:test(preceding-sibling::node()[1], '\\s+$')]")
					if nodes:
						messages.append(LintMessage("t-012", "Illegal white space before noteref.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					# Check for correct typography around measurements like 2 ft.
					# But first remove href and id attrs because URLs and IDs may contain strings that look like measurements
					# Note that while we check m,min (minutes) and h,hr (hours) we don't check s (seconds) because we get too many false positives on years, like `the 1540s`
					matches = regex.findall(fr"\b[0-9]+[{se.NO_BREAK_SPACE}\-]?(?:[mck]?[mgl]|ft|in|min?|h|sec|hr)\.?\b", regex.sub(r"(href|id)=\"[^\"]*?\"", "", file_contents))
					# Exclude number ordinals, they're not measurements
					matches = [match for match in matches if not regex.search(r"(st|nd|rd|th)", match)]
					if matches:
						messages.append(LintMessage("t-021", "Measurement not to standard. Numbers are followed by a no-break space and abbreviated units require an `<abbr>` element. See `semos://1.0.0/8.8.5`.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for <pre> tags
					if dom.xpath("//pre"):
						messages.append(LintMessage("s-013", "Illegal `<pre>` element.", se.MESSAGE_TYPE_ERROR, filename))

					# Check for <br/> after block-level elements
					nodes = dom.xpath("//*[self::p or self::blockquote or self::table or self::ol or self::ul or self::section or self::article][following-sibling::br]")
					if nodes:
						messages.append(LintMessage("s-014", "`<br/>` after block-level element.", se.MESSAGE_TYPE_ERROR, filename, {node.totagstring() for node in nodes}))

					# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
					matches = regex.findall(r"\b.+?”[,\.](?! …)", file_contents)
					if matches:
						messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check for double spacing
					matches = regex.search(fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}", file_contents)
					if matches:
						double_spaced_files.append(str(Path(filename)))

					# Run some checks on epub:type values
					incorrect_attrs = set()
					illegal_colons = set()
					illegal_se_namespaces = set()
					for attrs in dom.xpath("//*/@epub:type"):
						for attr in attrs.split():
							# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
							for match in regex.findall(r"^se:[a-z]+:(?:[a-z]+:?)*", attr):
								illegal_colons.add(match)

							# Did someone use periods instead of colons for the SE namespace? e.g. se.name.vessel.ship
							for match in regex.findall(r"^se\.[a-z]+(?:\.[a-z]+)*", attr):
								illegal_se_namespaces.add(match)

							# Did we draw from the z3998 vocabulary when the item exists in the epub vocabulary?
							if attr.startswith("z3998:"):
								bare_attr = attr.replace("z3998:", "")
								if bare_attr in EPUB_SEMANTIC_VOCABULARY:
									incorrect_attrs.add((attr, bare_attr))

					if illegal_colons:
						messages.append(LintMessage("s-031", "Illegal colon (`:`) in SE identifier. SE identifiers are separated by dots, not colons. E.g., `se:name.vessel.ship`.", se.MESSAGE_TYPE_ERROR, filename, illegal_colons))

					if illegal_se_namespaces:
						messages.append(LintMessage("s-032", "SE namespace must be followed by a colon (`:`), not a dot. E.g., `se:name.vessel`.", se.MESSAGE_TYPE_ERROR, filename, illegal_se_namespaces))

					if incorrect_attrs:
						messages.append(LintMessage("s-034", "Semantic used from the z3998 vocabulary, but the same semantic exists in the EPUB vocabulary.", se.MESSAGE_TYPE_ERROR, filename, [attr for (attr, bare_attr) in incorrect_attrs]))

					# Check for title attrs on abbr elements
					nodes = dom.xpath("//abbr[@title]")
					if nodes:
						messages.append(LintMessage("s-052", "`<attr>` element with illegal `title` attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.totagstring() for node in nodes]))

					# Check for leftover asterisms
					nodes = dom.xpath("//*[self::p or self::div][re:test(., '^\\s*\\*\\s*(\\*\\s*)+$')]")
					if nodes:
						messages.append(LintMessage("s-038", "Illegal asterism (`***`). Section/scene breaks must be defined by an `<hr/>` element.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					# Check for missing punctuation before closing quotes
					nodes = dom.xpath("//p[not(parent::header and position() = last())][re:test(., '[a-z]+[”’]$')]")
					if nodes:
						messages.append(LintMessage("t-011", "Missing punctuation before closing quotes.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring()[-30:] for node in nodes]))

					# Check to see if we've marked something as poetry or verse, but didn't include a first <span>
					# This xpath selects the p elements, whose parents are poem/verse, and whose first child is not a span
					nodes = dom.xpath("//*[contains(@epub:type, 'z3998:poem') or contains(@epub:type, 'z3998:verse') or contains(@epub:type, 'z3998:song') or contains(@epub:type, 'z3998:hymn')]/p[not(*[name()='span' and position()=1])]")
					if nodes:
						matches = []
						for node in nodes:
							# Get the first line of the poem, if it's a text node, so that we can include it in the error messages.
							# If it's not a text node then just ignore it and add the error anyway.
							first_line = node.lxml_element.xpath("descendant-or-self::text()[normalize-space(.)]", namespaces=se.XHTML_NAMESPACES)
							if first_line:
								match = first_line[0].strip()
								if match: # Make sure we don't append an empty string
									matches.append(match)

						messages.append(LintMessage("s-006", "Poem or verse `<p>` (stanza) without `<span>` (line) element.", se.MESSAGE_TYPE_WARNING, filename, matches))

					# Check to see if we included poetry or verse without the appropriate styling
					if filename not in se.IGNORED_FILENAMES:
						nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:poem') or contains(@epub:type, 'z3998:verse') or contains(@epub:type, 'z3998:song') or contains(@epub:type, 'z3998:hymn')][./p/span]")
						for node in nodes:
							if "z3998:poem" in node.attribute("epub:type") and not local_css_has_poem_style:
								missing_styles.append(node.totagstring())

							if "z3998:verse" in node.attribute("epub:type") and not local_css_has_verse_style:
								missing_styles.append(node.totagstring())

							if "z3998:song" in node.attribute("epub:type") and not local_css_has_song_style:
								missing_styles.append(node.totagstring())

							if "z3998:hymn" in node.attribute("epub:type") and not local_css_has_hymn_style:
								missing_styles.append(node.totagstring())

					# For this series of selections, we select spans that are direct children of p, because sometimes a line of poetry may have a nested span.
					nodes = dom.css_select("[epub|type~='z3998:poem'] p > span + a[epub|type~='noteref']")
					if nodes:
						messages.append(LintMessage("s-047", "`noteref` as a direct child of element with `z3998:poem` semantic. `noteref`s should be in their parent `<span>`.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					nodes = dom.css_select("[epub|type~='z3998:verse'] p > span + a[epub|type~='noteref']")
					if nodes:
						messages.append(LintMessage("s-048", "`noteref` as a direct child of element with `z3998:verse` semantic. `noteref`s should be in their parent `<span>`.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					nodes = dom.css_select("[epub|type~='z3998:song'] p > span + a[epub|type~='noteref']")
					if nodes:
						messages.append(LintMessage("s-049", "`noteref` as a direct child of element with `z3998:song` semantic. `noteref`s should be in their parent `<span>`.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					nodes = dom.css_select("[epub|type~='z3998:hymn'] p > span + a[epub|type~='noteref']")
					if nodes:
						messages.append(LintMessage("s-050", "`noteref` as a direct child of element with `z3998:hymn` semantic. `noteref`s should be in their parent `<span>`.", se.MESSAGE_TYPE_ERROR, filename, [node.tostring() for node in nodes]))

					# Check for space before endnote backlinks
					if filename == "endnotes.xhtml":
						# Do we have to replace Ibid.?
						matches = regex.findall(r"\bibid\b", file_contents, flags=regex.IGNORECASE)
						if matches:
							messages.append(LintMessage("s-039", "Illegal `Ibid` in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing `Ibid` refers to.", se.MESSAGE_TYPE_ERROR, filename))

						# Match backlink elements whose preceding node doesn't end with ' ', and is also not all whitespace
						nodes = dom.xpath("//a[@epub:type='backlink'][(preceding-sibling::node()[1])[not(re:test(., ' $')) and not(normalize-space(.) = '')]]")
						if nodes:
							messages.append(LintMessage("t-027", "Endnote referrer link not preceded by exactly one space.", se.MESSAGE_TYPE_WARNING, filename, [node.tostring() for node in nodes]))

					# If we're in the imprint, are the sources represented correctly?
					# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
					if filename == "imprint.xhtml":
						links = self.metadata_dom.xpath("/package/metadata/dc:source/text()")
						if len(links) <= 2:
							for link in links:
								if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
									messages.append(LintMessage("m-026", f"Project Gutenberg source not present. Expected: `<a href=\"{link}\">Project Gutenberg</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "hathitrust.org" in link and f"the <a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
									messages.append(LintMessage("m-027", f"HathiTrust source not present. Expected: the `<a href=\"{link}\">HathiTrust Digital Library</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "archive.org" in link and f"the <a href=\"{link}\">Internet Archive</a>" not in file_contents:
									messages.append(LintMessage("m-028", f"Internet Archive source not present. Expected: the `<a href=\"{link}\">Internet Archive</a>`.", se.MESSAGE_TYPE_WARNING, filename))

								if "books.google.com" in link and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
									messages.append(LintMessage("m-029", f"Google Books source not present. Expected: `<a href=\"{link}\">Google Books</a>`.", se.MESSAGE_TYPE_WARNING, filename))

					# Collect certain abbr elements for later check
					abbr_elements += dom.xpath("//abbr[contains(@class, 'temperature')]")

					# note that 'temperature' contains 'era'...
					abbr_elements += dom.xpath("//abbr[contains(concat(' ', @class, ' '), ' era ')]")

					abbr_elements += dom.xpath("//abbr[contains(@class, 'acronym')]")

					# Check if language tags in individual files match the language in content.opf
					if filename not in se.IGNORED_FILENAMES:
						file_language = dom.xpath("/html/@xml:lang", True)
						if language != file_language:
							messages.append(LintMessage("s-033", f"File language is `{file_language}`, but `content.opf` language is `{language}`.", se.MESSAGE_TYPE_WARNING, filename))

					# Check LoI descriptions to see if they match associated figcaptions
					if filename == "loi.xhtml":
						nodes = dom.xpath("//li/a")
						for node in nodes:
							figure_ref = node.attribute("href").split("#")[1]
							chapter_ref = regex.findall(r"(.*?)#.*", node.attribute("href"))[0]
							figcaption_text = ""
							loi_text = node.inner_text()
							file_dom = _dom(self.path / "src" / "epub" / "text" / chapter_ref)

							try:
								figure = file_dom.xpath(f"//*[@id='{figure_ref}']")[0]
							except Exception:
								messages.append(LintMessage("s-040", f"`#{figure_ref}` not found in file `{chapter_ref}`.", se.MESSAGE_TYPE_ERROR, "loi.xhtml"))
								continue

							for child in figure.lxml_element:
								if child.tag == "img":
									figure_img_alt = child.get("alt")

								if child.tag == "figcaption":
									figcaption_text = se.easy_xml.EasyXmlElement(child).inner_text()

							if (figcaption_text != "" and loi_text != "" and figcaption_text != loi_text) and (figure_img_alt != "" and loi_text != "" and figure_img_alt != loi_text):
								messages.append(LintMessage("s-041", f"The `<figcaption>` element of `#{figure_ref}` does not match the text in its LoI entry.", se.MESSAGE_TYPE_WARNING, chapter_ref))

				# Check for missing MARC relators
				if filename == "introduction.xhtml" and ">aui<" not in self.metadata_xml and ">win<" not in self.metadata_xml:
					messages.append(LintMessage("m-030", "`introduction.xhtml` found, but no MARC relator `aui` (Author of introduction, but not the chief author) or `win` (Writer of introduction).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "preface.xhtml" and ">wpr<" not in self.metadata_xml:
					messages.append(LintMessage("m-031", "`preface.xhtml` found, but no MARC relator `wpr` (Writer of preface).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "afterword.xhtml" and ">aft<" not in self.metadata_xml:
					messages.append(LintMessage("m-032", "`afterword.xhtml` found, but no MARC relator `aft` (Author of colophon, afterword, etc.).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "endnotes.xhtml" and ">ann<" not in self.metadata_xml:
					messages.append(LintMessage("m-033", "`endnotes.xhtml` found, but no MARC relator `ann` (Annotator).", se.MESSAGE_TYPE_WARNING, "content.opf"))

				if filename == "loi.xhtml" and ">ill<" not in self.metadata_xml:
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

		if xhtml_css_classes[css_class] == 1 and css_class not in se.IGNORED_CLASSES and not regex.match(r"^i[0-9]+$", css_class):
			# Don't count ignored classes OR i[0-9] which are used for poetry styling
			single_use_css_classes.append(css_class)

	if missing_selectors:
		messages.append(LintMessage("x-013", "CSS class found in XHTML, but not in `local.css`.", se.MESSAGE_TYPE_ERROR, "local.css", missing_selectors))

	if single_use_css_classes:
		messages.append(LintMessage("c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks.", se.MESSAGE_TYPE_WARNING, "local.css", single_use_css_classes))

	# Check our headings against the ToC and landmarks
	headings = list(set(headings))
	toc_dom = _dom(self.path / "src" / "epub" / "toc.xhtml")
	toc_headings = []
	toc_files = []
	toc_entries = toc_dom.xpath("/html/body/nav[@epub:type='toc']//a")

	# Match ToC headings against text headings
	# Unlike main headings, ToC entries have a ‘:’ before the subheading so we need to strip these for comparison
	for node in toc_entries:
		entry_text = " ".join(node.inner_text().replace(":", "").split())
		# This regex removes both the path portion of the filename, and and # anchors afterwards (for books like Aesop's fables)
		entry_file = regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", node.attribute("href"))
		toc_headings.append((entry_text, entry_file))
	for heading in headings:
		# Occasionally we find a heading with a colon, but as we’ve stripped our
		# ToC-only colons above we also need to do that here for the comparison.
		heading_without_colons = (heading[0].replace(":", ""), heading[1])
		if heading_without_colons not in toc_headings:
			messages.append(LintMessage("m-045", f"Heading `{heading[0]}` found, but not present for that file in the ToC.", se.MESSAGE_TYPE_ERROR, heading[1]))

	# Check our ordered ToC entries against the spine
	# To cover all possibilities, we combine the toc and the landmarks to get the full set of entries
	for node in toc_dom.xpath("/html/body/nav[@epub:type='landmarks']//a[re:test(@epub:type, '(front|body)matter')]"):
		toc_files.append(regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", node.attribute("href")))
	for node in toc_entries:
		toc_files.append(regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", node.attribute("href")))

	# We can't convert to set() to get unique items because set() is unordered
	unique_toc_files: List[str] = []
	for toc_file in toc_files:
		if toc_file not in unique_toc_files:
			unique_toc_files.append(toc_file)
	toc_files = unique_toc_files

	spine_entries = self.metadata_dom.xpath("/package/spine/itemref")
	if len(toc_files) != len(spine_entries):
		messages.append(LintMessage("m-043", f"The number of elements in the spine ({len(toc_files)}) does not match the number of elements in the ToC and landmarks ({len(spine_entries)}).", se.MESSAGE_TYPE_ERROR, "content.opf"))
	for index, node in enumerate(spine_entries):
		if toc_files[index] != node.attribute("idref"):
			messages.append(LintMessage("m-044", f"The spine order does not match the order of the ToC and landmarks. Expected `{node.attribute('idref')}`, found `{toc_files[index]}`.", se.MESSAGE_TYPE_ERROR, "content.opf"))
			break

	for element in abbr_elements:
		abbr_class = element.attribute("class").replace(" eoc", "").strip()
		if f"abbr.{abbr_class}" not in abbr_styles:
			missing_styles.append(element.totagstring())

	if missing_styles:
		messages.append(LintMessage("c-006", "Semantic found, but missing corresponding style in `local.css`.", se.MESSAGE_TYPE_ERROR, "local.css", set(missing_styles)))

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
			messages.append(LintMessage("m-048", "Unused `se-lint-ignore.xml` rule.", se.MESSAGE_TYPE_ERROR, "se-lint-ignore.xml", unused_codes))

	messages = natsorted(messages, key=lambda x: (x.filename, x.code))

	return messages
