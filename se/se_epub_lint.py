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
from natsort import natsorted, ns

import se
import se.easy_xml
import se.formatting
import se.images

METADATA_VARIABLES = ["TITLE", "TITLE_SORT", "SUBJECT_1", "SUBJECT_2", "LCSH_ID_1", "LCSH_ID_2", "TAG", "DESCRIPTION", "LONG_DESCRIPTION", "LANG", "PG_URL", "IA_URL", "EBOOK_WIKI_URL", "VCS_IDENTIFIER", "AUTHOR", "AUTHOR_SORT", "AUTHOR_FULL_NAME", "AUTHOR_WIKI_URL", "AUTHOR_NACOAF_URL", "TRANSLATOR", "TRANSLATOR_SORT", "TRANSLATOR_WIKI_URL", "TRANSLATOR_NACOAF_URL", "COVER_ARTIST", "COVER_ARTIST_SORT", "COVER_ARTIST_WIKI_URL", "COVER_ARTIST_NACOAF_URL", "TRANSCRIBER", "TRANSCRIBER_SORT", "TRANSCRIBER_URL", "PRODUCER", "PRODUCER_SORT", "PRODUCER_URL"]
COLOPHON_VARIABLES = ["TITLE", "YEAR", "AUTHOR_WIKI_URL", "AUTHOR", "PRODUCER_URL", "PRODUCER", "PG_YEAR", "TRANSCRIBER_1", "TRANSCRIBER_2", "PG_URL", "IA_URL", "PAINTING", "ARTIST_WIKI_URL", "ARTIST"]
EPUB_SEMANTIC_VOCABULARY = ["cover", "frontmatter", "bodymatter", "backmatter", "volume", "part", "chapter", "division", "foreword", "preface", "prologue", "introduction", "preamble", "conclusion", "epilogue", "afterword", "epigraph", "toc", "landmarks", "loa", "loi", "lot", "lov", "appendix", "colophon", "index", "index-headnotes", "index-legend", "index-group", "index-entry-list", "index-entry", "index-term", "index-editor-note", "index-locator", "index-locator-list", "index-locator-range", "index-xref-preferred", "index-xref-related", "index-term-category", "index-term-categories", "glossary", "glossterm", "glossdef", "bibliography", "biblioentry", "titlepage", "halftitlepage", "copyright-page", "acknowledgments", "imprint", "imprimatur", "contributors", "other-credits", "errata", "dedication", "revision-history", "notice", "tip", "halftitle", "fulltitle", "covertitle", "title", "subtitle", "bridgehead", "learning-objective", "learning-resource", "assessment", "qna", "panel", "panel-group", "balloon", "text-area", "sound-area", "footnote", "endnote", "footnotes", "endnotes", "noteref", "keyword", "topic-sentence", "concluding-sentence", "pagebreak", "page-list", "table", "table-row", "table-cell", "list", "list-item", "figure", "aside"]
SE_GENRES = ["Adventure", "Autobiography", "Biography", "Childrens", "Comedy", "Drama", "Fantasy", "Fiction", "Horror", "Memoir", "Mystery", "Nonfiction", "Philosophy", "Poetry", "Romance", "Satire", "Science Fiction", "Shorts", "Spirituality", "Tragedy", "Travel"]
IGNORED_CLASSES = ["elision", "name", "temperature", "state", "era", "compass", "acronym", "postal", "eoc", "initialism", "degree", "time", "compound", "timezone", "full-page", "continued"]
BINARY_EXTENSIONS = [".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".png", ".epub", ".xcf", ".otf"]
FRONTMATTER_FILENAMES = ["dedication.xhtml", "introduction.xhtml", "preface.xhtml", "foreword.xhtml", "preamble.xhtml", "titlepage.xhtml", "halftitlepage.xhtml", "imprint.xhtml"]
BACKMATTER_FILENAMES = ["endnotes.xhtml", "loi.xhtml", "afterword.xhtml", "appendix.xhtml", "colophon.xhtml", "uncopyright.xhtml"]

"""
POSSIBLE BBCODE TAGS
See the se.print_error function for a comprehensive list of allowed codes.

LIST OF ALL SE LINT MESSAGES

CSS
"c-002", "Unused CSS selectors."
"c-003", "[css]\\[xml|attr][/] selector in CSS, but no XML namespace declared ([css]@namespace xml \"http://www.w3.org/XML/1998/namespace\";[/])."
"c-004", "Don’t specify border colors, so that reading systems can adjust for night mode."
"c-005", f"[css]abbr[/] selector does not need [css]white-space: nowrap;[/] as it inherits it from [path][link=file://{self.path / 'src/epub/css/core.css'}]core.css[/][/]."
"c-006", f"Semantic found, but missing corresponding style in [path][link=file://{local_css_path}]local.css[/][/]."
"c-007", "[css]hyphens[/css] CSS property without [css]-epub-hyphens[/css] copy."
"c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks."
"c-009", "Duplicate CSS selectors. Duplicates are only acceptable if overriding SE base styles."
UNUSED
vvvvvvvvvvvvvvvvvvvvvvv
"c-001", "Don’t directly select [xhtml]<h#>[/] elements, as they are used in template files; use more specific selectors."

FILESYSTEM
"f-001", "Illegal file or directory."
"f-002", "Missing expected file or directory."
"f-003", f"File does not match [path][link=file://{self.path / 'LICENSE.md'}]{license_file_path}[/][/]."
"f-004", f"File does not match [path][link=file://{self.path / 'src/epub/css/core.css'}]{core_css_file_path}[/][/]."
"f-005", f"File does not match [path][link=file://{self.path / 'src/epub/images/logo.svg'}]{logo_svg_file_path}[/][/]."
"f-006", f"File does not match [path][link=file://{self.path / 'src/epub/text/uncopyright.xhtml'}]{uncopyright_file_path}[/][/]."
"f-008", f"Filename is not URL-safe. Expected: [path]{url_safe_filename}[/]."
"f-008", f"Filename is not URL-safe. Expected: [path]{url_safe_filename}[/]."
"f-009", "Illegal leading [text]0[/] in filename."
"f-010", "Problem decoding file as utf-8."
"f-011", "JPEG files must end in [path].jpg[/]."
"f-012", "TIFF files must end in [path].tif[/]."
"f-013", "Glossary search key map must be named [path]glossary-search-key-map.xml[/]."
"f-014", f"File does not match [path][link=file://{self.path / 'src/epub/css/se.css'}]{core_css_file_path}[/][/]."

METADATA
"m-001", "gutenberg.org URL missing leading [text]www.[/]."
"m-002", "archive.org URL should not have leading [text]www.[/]."
"m-003", "Non-HTTPS URL."
"m-004", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://books.google.com/books?id=<BOOK-ID>[/]."
"m-005", "Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like [url]https://catalog.hathitrust.org/Record/<BOOK-ID>[/]."
"m-006", "Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like [url]https://www.gutenberg.org/ebooks/<BOOK-ID>[/]."
"m-007", "Non-canonical archive.org URL. Internet Archive URLs must look exactly like [url]https://archive.org/details/<BOOK-ID>[/]."
"m-008", "[url]id.loc.gov[/] URL ending with illegal [path].html[/]."
"m-009", f"[xml]<meta property=\"se:url.vcs.github\">[/] value does not match expected: [url]{self.generated_github_repo_url}[/]."
"m-010", "Invalid [xml]refines[/] property."
"m-011", "Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: [url]https://catalog.hathitrust.org/Record/<RECORD-ID>[/]."
"m-012", "Non-typogrified character in [xml]<dc:title>[/] element."
"m-013", "Non-typogrified character in [xml]<dc:description>[/] element."
"m-014", "Non-typogrified character in [xml]<meta property=\"se:long-description\">[/] element."
"m-015", f"Metadata long description is not valid XHTML. LXML says: {ex}"
"m-016", "Long description must be escaped HTML."
"m-017", "[xml]<!\\[CDATA\\[[/] found. Run [bash]se clean[/] to canonicalize [xml]<!\\[CDATA\\[[/] sections."
"m-018", "HTML entities found. Use Unicode equivalents instead."
"m-019", "Illegal em-dash in [xml]<dc:subject>[/] element; use [text]--[/]."
"m-020", "Illegal value for [xml]<meta property=\"se:subject\">[/] element."
"m-021", "No [xml]<meta property=\"se:subject\">[/] element found."
"m-022", "Empty [xml]<meta property=\"se:production-notes\">[/] element."
"m-023", f"[xml]<dc:identifier>[/] does not match expected: [text]{self.generated_identifier}[/]."
"m-024", "[xml]<meta property=\"se:name.person.full-name\">[/] property identical to regular name. If the two are identical the full name [xml]<meta>[/] element must be removed."
"m-025", "Translator found in metadata, but no [text]translated from LANG[/] block in colophon."
"m-026", f"Project Gutenberg source not present. Expected: [xhtml]<a href=\"{link}\">Project Gutenberg</a>[/]."
"m-027", f"HathiTrust source not present. Expected: the [xhtml]<a href=\"{link}\">HathiTrust Digital Library</a>[/]."
"m-028", f"Internet Archive source not present. Expected: the [xhtml]<a href=\"{link}\">Internet Archive</a>[/]."
"m-029", f"Google Books source not present. Expected: [xhtml]<a href=\"{link}\">Google Books</a>[/]."
"m-030", f"[val]introduction[/] semantic inflection found, but no MARC relator [val]aui[/] (Author of introduction, but not the chief author) or [val]win[/] (Writer of introduction)."
"m-031", f"[val]preface[/] semantic inflection found, but no MARC relator [val]wpr[/] (Writer of preface)."
"m-032", f"[val]afterword[/] semantic inflection found, but no MARC relator [val]aft[/] (Author of colophon, afterword, etc.)."
"m-033", f"[val]endnotes[/] semantic inflection found, but no MARC relator [val]ann[/] (Annotator)."
"m-034", f"[val]loi[/] semantic inflection found, but no MARC relator [val]ill[/] (Illustrator)."
"m-035", f"Unexpected SE identifier in colophon. Expected: [url]{se_url}[/]."
"m-036", "Missing data in colophon."
"m-037", f"Source not represented in colophon.xhtml. Expected: [xhtml]<a href=\"{link}\">Project Gutenberg</a>[/]."
"m-038", f"Source not represented in colophon.xhtml. Expected: [xhtml]the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>[/]."
"m-039", f"Source not represented in colophon.xhtml. Expected: [xhtml]the<br/> <a href=\"{link}\">Internet Archive</a>[/]."
"m-040", f"Source not represented in colophon.xhtml. Expected: [xhtml]<a href=\"{link}\">Google Books</a>[/]."
"m-041", "[text]Hathi Trust[/] should be [text]HathiTrust[/]."
"m-042", "[xml]<manifest>[/] element does not match expected structure."
"m-043", f"The number of elements in the spine ({len(toc_files)}) does not match the number of elements in the ToC and landmarks ({len(spine_entries)})."
"m-044", f"The spine order does not match the order of the ToC and landmarks. Expected [text]{node.get_attr('idref')}[/], found [text]{toc_files[index]}[/]."
"m-045", f"Heading [text]{heading[0]}[/] found, but not present for that file in the ToC."
"m-046", "Missing or empty [xml]<reason>[/] element."
"m-047", "Ignoring [path]*[/] is too general. Target specific files if possible."
"m-048", f"Unused [path][link=file://{lint_ignore_path}]se-lint-ignore.xml[/][/] rule."
"m-049", "No [path]se-lint-ignore.xml[/] rules. Delete the file if there are no rules."
"m-050", "Non-typogrified character in [xml]<meta property=\"file-as\" refines=\"#title\">[/] element."
"m-051", "Missing expected element in metadata."
"m-052", "[xml]<dc:title>[/] element contains numbers, but no [xml]<meta property=\"se:alternate-title\"> element in metadata."
"m-053", "[xml]<meta property=\"se:subject\">[/] elements not in alphabetical order."
"m-054", "Standard Ebooks URL with illegal trailing slash."
"m-055", "Missing data in metadata."
"m-056", "Author name present in [xml]<meta property=\"se:long-description\">[/] element, but the first instance of their name is not hyperlinked to their SE author page."
"m-057", "[xml]xml:lang[/] attribute in [xml]<meta property=\"se:long-description\">[/] element should be [xml]lang[/]."
"m-058", "[val]se:subject[/] of [text]{implied_tag}[/] found, but [text]{tag}[/] implies [text]{implied_tag}[/]."
"m-059", f"Link to [url]{node.get_attr('href')}[/] found in colophon, but missing matching [xhtml]dc:source[/] element in metadata."
"m-060", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://www.google.com/books/edition/<BOOK-NAME>/<BOOK-ID>[/]."

SEMANTICS & CONTENT
"s-001", "Illegal numeric entity (like [xhtml]&#913;[/])."
"s-002", "Lowercase letters in cover. Cover text must be all uppercase."
"s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except [text]translated by[/] and [text]illustrated by[/]."
"s-004", "[xhtml]img[/] element missing [attr]alt[/] attribute."
"s-005", "Nested [xhtml]<blockquote>[/] element."
"s-006", "Poem or verse [xhtml]<p>[/] (stanza) without [xhtml]<span>[/] (line) element."
"s-007", "Element requires at least one block-level child."
"s-008", "[xhtml]<br/>[/] element found before closing tag of block-level element."
"s-009", "[xhtml]<hgroup>[/] element with only one child."
"s-010", "Empty element. Use [xhtml]<hr/>[/] for thematic breaks if appropriate."
"s-011", "Element without [attr]id[/] attribute."
"s-012", "Illegal [xhtml]<hr/>[/] as last child."
"s-013", "Illegal [xhtml]<pre>[/] element."
"s-014", "[xhtml]<br/>[/] after block-level element."
"s-015", "Element has [val]subtitle[/] semantic, but without a sibling having a [val]title[/] semantic."
"s-016", "Incorrect [text]the[/] before Google Books link."
"s-017", "[xhtml]<m:mfenced>[/] is deprecated in the MathML spec. Use [xhtml]<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>[/]."
"s-018", "[xhtml]<img>[/] element with [attr]id[/] attribute. [attr]id[/] attributes go on parent [xhtml]<figure>[/] elements."
"s-019", "[xhtml]<h#>[/] element with [attr]id[/] attribute. [xhtml]<h#>[/] elements should be wrapped in [xhtml]<section>[/] elements, which should hold the [attr]id[/] attribute."
"s-020", "Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present."
"s-021", f"Unexpected value for [xhtml]<title>[/] element. Expected: [text]{title}[/]. (Beware hidden Unicode characters!)"
"s-022", f"The [xhtml]<title>[/] element of [path][link=file://{svg_path}]{image_ref}[/][/] does not match the [attr]alt[/] attribute text in [path][link=file://{filename}]{filename.name}[/][/]."
"s-023", f"Title [text]{title}[/] not correctly titlecased. Expected: [text]{titlecased_title}[/]."
"s-024", "Header elements that are entirely non-English should not be set in italics. Instead, the [xhtml]<h#>[/] element has the [attr]xml:lang[/] attribute."
"s-025", "Titlepage [xhtml]<title>[/] elements must contain exactly: [text]Titlepage[/]."
"s-026", "Invalid Roman numeral."
"s-027", f"{image_ref} missing [xhtml]<title>[/] element."
"s-028", f"[path][link=file://{self.path / 'images/cover.svg'}]cover.svg[/][/] and [path][link=file://{self.path / 'images/titlepage.svg'}]titlepage.svg[/][/] [xhtml]<title>[/] elements don’t match."
"s-029", "If a [xhtml]<span>[/] exists only for the [val]z3998:roman[/] semantic, then [val]z3998:roman[/] should be pulled into parent element instead."
"s-030", "[val]z3998:nonfiction[/] should be [val]z3998:non-fiction[/]."
"s-031", "Illegal [text]:[/] in SE identifier. SE identifiers are separated by [text].[/], not [text]:[/]. E.g., [val]se:name.vessel.ship[/]."
"s-032", "SE namespace must be followed by a [text]:[/], not a [text].[/]. E.g., [val]se:name.vessel[/]."
"s-033", f"File language is [val]{file_language}[/], but [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/] language is [val]{language}[/]."
"s-034", "Semantic used from the z3998 vocabulary, but the same semantic exists in the EPUB vocabulary."
"s-035", f"[xhtml]{nodes[0].to_tag_string()}[/] element has the [val]z3998:roman[/] semantic, but is not a Roman numeral."
"s-036", "No [val]frontmatter[/] semantic inflection for what looks like a frontmatter file."
"s-037", "No [val]backmatter[/] semantic inflection for what looks like a backmatter file."
"s-038", "Illegal asterism. Section/scene breaks must be defined by an [xhtml]<hr/>[/] element."
"s-039", "[text]Ibid[/] in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes"
"s-040", f"[attr]#{figure_ref}[/] not found in file [path][link=file://{self.path / 'src/epub/text' / chapter_ref}]{chapter_ref}[/][/]."
"s-041", f"The [xhtml]<figcaption>[/] element of [attr]#{figure_ref}[/] does not match the text in its LoI entry."
"s-042", "[xhtml]<table>[/] element without [xhtml]<tbody>[/] child."
"s-043", "[val]se:short-story[/] semantic on element that is not [xhtml]<article>[/]."
"s-044", "Element with poem or verse semantic, without descendant [xhtml]<p>[/] (stanza) element."
"s-045", "[xhtml]<abbr>[/] element without semantic class like [class]name[/] or [class]initialism[/]."
"s-046", "[xhtml]<p>[/] element containing only [xhtml]<span>[/] and [xhtml]<br>[/] elements, but its parent doesn’t have the [val]z3998:poem[/], [val]z3998:verse[/], [val]z3998:song[/], [val]z3998:hymn[/], or [val]z3998:lyrics[/] semantic. Multi-line clauses that are not verse don’t require [xhtml]<span>[/]s."
"s-047", "[val]noteref[/] as a direct child of element with poem or verse semantic. [val]noteref[/]s should be in their parent [xhtml]<span>[/]."
"s-048", "[val]se:name[/] semantic on block element. [val]se:name[/] indicates the contents is the name of something."
"s-049", "[xhtml]<header>[/] element whose only child is an [xhtml]<h#>[/] element."
"s-050", "[xhtml]<span>[/] element appears to exist only to apply [attr]epub:type[/]. [attr]epub:type[/] should go on the parent element instead, without a [xhtml]<span>[/] element."
"s-051", f"Wrong height or width. [path][link=file://{self.path / 'images/cover.jpg'}]cover.jpg[/][/] must be exactly {se.COVER_WIDTH} × {se.COVER_HEIGHT}."
"s-052", "[xhtml]<abbr>[/] element with illegal [attr]title[/] attribute."
"s-053", "Colophon line not preceded by [xhtml]<br/>[/]."
"s-054", "[xhtml]<cite>[/] as child of [xhtml]<p>[/] in [xhtml]<blockquote>[/]. [xhtml]<cite>[/] should be the direct child of [xhtml]<blockquote>[/]."
"s-055", "[xhtml]<th>[/] element not in [xhtml]<thead>[/] ancestor."
"s-056", "Last [xhtml]<p>[/] child of endnote missing backlink."
"s-057", "Backlink noteref fragment identifier doesn’t match endnote number."
"s-058", "[attr]z3998:stage-direction[/] semantic only allowed on [xhtml]<i>[/], [xhtml]<abbr>[/], and [xhtml]<p>[/] elements."
"s-059", "Internal link beginning with [val]../text/[/]."
"s-060", "Italics on name that requires quotes instead."
"s-061", "Title and following header content not in a [xhtml]<header>[/] element."
"s-062", "[xhtml]<dt>[/] element in a glossary without exactly one [xhtml]<dfn>[/] child."
"s-063", "[val]z3998:persona[/] semantic on element that is not a [xhtml]<b>[/] or [xhtml]<td>[/]."
"s-064", "Endnote citation not wrapped in [xhtml]<cite>[/]. Em dashes go within [xhtml]<cite>[/] and it is preceded by one space."
"s-065", "[val]fulltitle[/] semantic on element that is not [xhtml]<h1>[/] or [xhtml]<hgroup>[/]."
"s-066", "Header element missing [val]label[/] semantic."
"s-067", "Header element with a [val]label[/] semantic child, but without an [val]ordinal[/] semantic child."
"s-068", "Header element missing [val]ordinal[/] semantic."
"s-069", "[xhtml]<body>[/] element missing direct child [xhtml]<section>[/] or [xhtml]<article>[/] element."
"s-070", "[xhtml]<h#>[/] element without [xhtml]<hgroup>[/] parent and without semantic inflection."
"s-071", "Sectioning element with more than one heading element."
"s-072", "Element with single [xhtml]<span>[/] child. [xhtml]<span>[/] should be removed and its attributes promoted to the parent element."
"s-073", "Header element that requires [val]label[/] and [val]ordinal[/] semantic children."
"s-074", "[xhtml]<hgroup>[/] element containing sequential [xhtml]<h#>[/] elements at the same heading level."

TYPOGRAPHY
"t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)"
"t-002", "Comma or period outside of double quote. Generally punctuation goes within single and double quotes."
"t-003", "[text]“[/] missing matching [text]”[/]. Note: When dialog from the same speaker spans multiple [xhtml]<p>[/] elements, it’s correct grammar to omit closing [text]”[/] until the last [xhtml]<p>[/] of dialog."
"t-004", "[text]‘[/] missing matching [text]’[/]."
"t-005", "Dialog without ending comma."
"t-006", "Comma after producer name, but there are only two producers."
"t-007", "Possessive [text]’s[/] within name italics. If the name in italics is doing the possessing, [text]’s[/] goes outside italics."
"t-008", "Repeated punctuation."
"t-009", "Required no-break space not found before [xhtml]<abbr class=\"time\">[/]."
"t-010", "Time set with [text].[/] instead of [text]:[/]."
"t-011", "Missing punctuation before closing quotes."
"t-012", "Illegal white space before noteref."
"t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period."
"t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash."
"t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals."
"t-016", "Initials in [xhtml]<abbr class=\"name\">[/] not separated by spaces."
"t-017", "Ending punctuation inside italics. Ending punctuation is only allowed within italics if the phrase is an independent clause."
"t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction."
"t-019", "When a complete clause is italicized, ending punctuation except commas must be within containing italics."
"t-020", "Endnote links must be outside of punctuation, including quotation marks."
"t-021", "Measurement not to standard. Numbers are followed by a no-break space and abbreviated units require an [xhtml]<abbr>[/] element. See [path][link=https://standardebooks.org/manual/1.0.0/8-typography#8.8.5]semos://1.0.0/8.8.5[/][/]."
"t-022", "No-break space found in [xhtml]<abbr class=\"name\">[/]. This is redundant."
"t-023", "Comma inside [xhtml]<i>[/] element before closing dialog."
"t-024", "When italicizing language in dialog, italics go inside quotation marks."
"t-025", "Non-typogrified [text]'[/], [text]\"[/] (as [xhtml]&quot;[/]), or [text]--[/] in image [attr]alt[/] attribute."
"t-026", "[attr]alt[/] attribute does not appear to end with punctuation. [attr]alt[/] attributes must be composed of complete sentences ending in appropriate punctuation."
"t-027", "Endnote referrer link not preceded by exactly one space."
"t-028", "Possible mis-curled quotation mark."
"t-029", "Period followed by lowercase letter. Hint: Abbreviations require an [xhtml]<abbr>[/] element."
"t-030", "Initialism with spaces or without periods."
"t-031", "[text]A B C[/] must be set as [text]A.B.C.[/] It is not an abbreviation."
"t-032", "Initialism or name followed by period. Hint: Periods go within [xhtml]<abbr>[/]. [xhtml]<abbr>[/]s containing periods that end a clause require the [class]eoc[/] class."
"t-033", "Space after dash."
"t-034", "[xhtml]<cite>[/] element preceded by em-dash. Hint: em-dashes go within [xhtml]<cite>[/] elements."
"t-035", "[xhtml]<cite>[/] element not preceded by space."
"t-036", "[text]”[/] missing matching [text]“[/]."
"t-037", "[text]”[/] preceded by space."
"t-038", "[text]“[/] before closing [xhtml]</p>[/]."
"t-039", "Initialism followed by [text]’s[/]. Hint: Plurals of initialisms are not followed by [text]’[/]."
"t-040", "Subtitle with illegal ending period."
"t-041", "Illegal space before punctuation."
"t-042", "Possible typo."
"t-043", "Dialog tag missing punctuation."
"t-044", "Comma required after leading [text]Or[/] in subtitles."
"t-045", "[xhtml]<p>[/] preceded by [xhtml]<blockquote>[/] and starting in a lowercase letter, but without [val]continued[/] class."

XHTML
"x-001", "String [text]UTF-8[/] must always be lowercase."
"x-002", "Uppercase in attribute value. Attribute values must be all lowercase."
"x-003", "Illegal [xml]transform[/] attribute. SVGs should be optimized to remove use of [xml]transform[/]. Try using Inkscape to save as an “optimized SVG”."
"x-004", "Illegal [xml]style=\"fill: #000\"[/] or [xml]fill=\"#000\"[/]."
"x-005", "Illegal [xml]height[/] or [xml]width[/] attribute on root [xml]<svg>[/] element. Size SVGs using the [xml]viewBox[/] attribute only."
"x-006", f"[xml]{match}[/] found instead of [xml]viewBox[/]. [xml]viewBox[/] must be correctly capitalized."
"x-007", "[attr]id[/] attributes starting with a number are illegal XHTML."
"x-008", "Elements should end with a single [text]>[/]."
"x-009", "Illegal leading 0 in [attr]id[/] attribute."
"x-010", "Illegal element in [xhtml]<title>[/] element."
"x-011", "Illegal underscore in attribute. Use dashes instead of underscores."
"x-012", "Illegal [attr]style[/] attribute. Don’t use inline styles, any element can be targeted with a clever enough selector."
"x-013", f"CSS class found in XHTML, but not in [path][link=file://{local_css_path}]local.css[/][/]."
"x-014", "Illegal [xml]id[/] attribute."
"x-015", "Illegal element in [xhtml]<head>[/]. Only [xhtml]<title>[/] and [xhtml]<link rel=\"stylesheet\">[/] are allowed."
"x-016", "[attr]xml:lang[/] attribute with value starting in uppercase letter."
"x-017", "Duplicate value for [attr]id[/] attribute. [attr]id[/] attribute values must be unique across the entire ebook on all non-sectioning elements."
"""

class LintMessage:
	"""
	An object representing an output message for the lint function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	def __init__(self, code: str, text: str, message_type=se.MESSAGE_TYPE_WARNING, filename: Path = None, submessages: Union[List[str], Set[str]] = None):
		self.code = code
		self.text = text.strip()
		self.filename = filename
		self.message_type = message_type

		if submessages:
			self.submessages: Union[List[str], Set[str], None] = []
			smallest_indent = 1000
			for submessage in submessages:
				# Try to flatten leading indentation
				for indent in regex.findall(r"^\t+(?=<)", submessage, flags=regex.MULTILINE):
					if len(indent) < smallest_indent:
						smallest_indent = len(indent)

			if smallest_indent == 1000:
				smallest_indent = 0

			if smallest_indent:
				for submessage in submessages:
					self.submessages.append(regex.sub(fr"^\t{{{smallest_indent}}}", "", submessage, flags=regex.MULTILINE))
			else:
				self.submessages = submessages
		else:
			self.submessages = None

def _get_malformed_urls(xhtml: str, filename: Path) -> list:
	"""
	Helper function used in self.lint()
	Get a list of URLs in the epub that don't match SE standards.

	INPUTS
	xhtml: A string of XHTML to check

	OUTPUTS
	A list of LintMessages representing any malformed URLs in the XHTML string
	"""

	messages = []

	# Check for non-https URLs
	matches = regex.findall(r"(?<!www\.)gutenberg\.org[^\"<\s]*", xhtml)
	if matches:
		messages.append(LintMessage("m-001", "gutenberg.org URL missing leading [text]www.[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"www\.archive\.org[^\"<\s]*", xhtml)
	if matches:
		messages.append(LintMessage("m-002", "archive.org URL should not have leading [text]www.[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"http://(?:gutenberg\.org|archive\.org|pgdp\.net|catalog\.hathitrust\.org|en\.wikipedia\.org|standardebooks\.org)[^\"<\s]*", xhtml)
	if matches:
		messages.append(LintMessage("m-003", "Non-HTTPS URL.", se.MESSAGE_TYPE_ERROR, filename, matches))

	# Check for malformed canonical URLs
	matches = regex.findall(r"https?://books\.google\.com/books\?id=.+?[&#][^<\s\"]+", xhtml)
	if matches:
		messages.append(LintMessage("m-004", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://books.google.com/books?id=<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"https?://www\.google\.com/books/edition/[^/]+?/[^/?#]+/?[&#?][^<\s\"]+", xhtml)
	if matches:
		messages.append(LintMessage("m-060", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://www.google.com/books/edition/<BOOK-NAME>/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"https?://babel\.hathitrust\.org[^<\s\"]+", xhtml)
	if matches:
		messages.append(LintMessage("m-005", "Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like [url]https://catalog.hathitrust.org/Record/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"https?://.*?gutenberg\.org/(?:files|cache)[^<\s\"]+", xhtml)
	if matches:
		messages.append(LintMessage("m-006", "Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like [url]https://www.gutenberg.org/ebooks/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"https?://.*?archive\.org/stream[^<\s\"]+", xhtml)
	if matches:
		messages.append(LintMessage("m-007", "Non-canonical archive.org URL. Internet Archive URLs must look exactly like [url]https://archive.org/details/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, matches))

	matches = regex.findall(r"https?://standardebooks.org/[^<\s\"]/(?![<\s\"])", xhtml)
	if matches:
		messages.append(LintMessage("m-054", "Standard Ebooks URL with illegal trailing slash.", se.MESSAGE_TYPE_ERROR, filename, matches))

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
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/]. Exception: {ex}")
			except FileNotFoundError as ex:
				raise ex
			except Exception as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/].") from ex

	return _DOM_CACHE[file_path_str]

def lint(self, skip_lint_ignore: bool) -> list:
	"""
	Check this ebook for some common SE style errors.

	INPUTS
	None

	OUTPUTS
	A list of LintMessage objects.
	"""

	local_css_path = self.path / "src/epub/css/local.css"
	messages: List[LintMessage] = []
	has_halftitle = False
	has_frontmatter = False
	has_cover_source = False
	cover_svg_title = ""
	titlepage_svg_title = ""
	xhtml_css_classes: Dict[str, int] = {}
	headings: List[tuple] = []
	double_spaced_files: List[Path] = []
	unused_selectors: List[str] = []
	missing_metadata_elements = []
	abbr_elements: List[se.easy_xml.EasyXmlElement] = []

	# These are partly defined in semos://1.0.0/8.10.9.2
	initialism_exceptions = ["G", # as in `G-Force`
				"1D", "2D", "3D", "4D", # as in `n-dimensional`
				"MS.", "MSS.", # Manuscript(s)
				"MM.",  # Messiuers
				"κ.τ.λ.", # "etc." in Greek, and we don't match Greek chars.
				"TV",
				"AC", "DC" # electrical current
	]

	# This is a dict with where keys are the path and values are a list of code dicts.
	# Each code dict has a key "code" which is the actual code, and a key "used" which is a
	# bool indicating whether or not the code has actually been caught in the linting run.
	ignored_codes: Dict[str, List[Dict]] = {}

	# First, check if we have an se-lint-ignore.xml file in the ebook root. If so, parse it. For an example se-lint-ignore file, see semos://1.0.0/2.3
	lint_ignore_path = self.path / "se-lint-ignore.xml"
	if not skip_lint_ignore and lint_ignore_path.exists():
		lint_config = _dom(lint_ignore_path)

		elements = lint_config.xpath("/se-lint-ignore/file")

		if not elements:
			messages.append(LintMessage("m-049", "No [path]se-lint-ignore.xml[/] rules. Delete the file if there are no rules.", se.MESSAGE_TYPE_ERROR, lint_ignore_path))

		has_illegal_path = False

		for element in elements:
			path = element.get_attr("path").strip()

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
						messages.append(LintMessage("m-046", "Missing or empty [xml]<reason>[/] element.", se.MESSAGE_TYPE_ERROR, lint_ignore_path))

		if has_illegal_path:
			messages.append(LintMessage("m-047", "Ignoring [path]*[/] is too general. Target specific files if possible.", se.MESSAGE_TYPE_WARNING, lint_ignore_path))

	# Done parsing ignore list

	# Get the ebook language for later use
	try:
		language = self.metadata_dom.xpath("/package/metadata/dc:language")[0].text
	except se.InvalidXmlException as ex:
		raise ex
	except Exception as ex:
		raise se.InvalidSeEbookException(f"Missing [xml]<dc:language>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/].") from ex

	# Check local.css for various items, for later use
	try:
		with open(local_css_path, "r", encoding="utf-8") as file:
			self.local_css = file.read()
	except Exception as ex:
		raise se.InvalidSeEbookException(f"Couldn’t open [path]{local_css_path}[/].") from ex

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
		messages.append(LintMessage("c-009", "Duplicate CSS selectors. Duplicates are only acceptable if overriding SE base styles.", se.MESSAGE_TYPE_WARNING, local_css_path, list(set(duplicate_selectors))))

	# Store a list of CSS selectors, and duplicate it into a list of unused selectors, for later checks
	# We use a regex to remove pseudo-elements like ::before, because we want the *selectors* to see if they're unused.
	local_css_selectors = [regex.sub(r"::[\p{Lowercase_Letter}\-]+", "", selector) for selector in local_css_rules]
	unused_selectors = local_css_selectors.copy()

	local_css_has_poem_style = False
	local_css_has_verse_style = False
	local_css_has_song_style = False
	local_css_has_hymn_style = False
	local_css_has_lyrics_style = False
	local_css_has_elision_style = False
	local_css_has_signature_style = False
	abbr_styles = regex.findall(r"abbr\.[\p{Lowercase_Letter}]+", self.local_css)
	missing_styles: List[str] = []
	directories_not_url_safe = []
	files_not_url_safe = []
	id_values = {}
	duplicate_id_values = []

	# Iterate over rules to do some other checks
	abbr_with_whitespace = []
	for selector, rules in local_css_rules.items():
		if "z3998:poem" in selector:
			local_css_has_poem_style = True

		if "z3998:verse" in selector:
			local_css_has_verse_style = True

		if "z3998:song" in selector:
			local_css_has_song_style = True

		if "z3998:hymn" in selector:
			local_css_has_hymn_style = True

		if "z3998:lyrics" in selector:
			local_css_has_lyrics_style = True

		if "span.elision" in selector:
			local_css_has_elision_style = True

		if "z3998:signature" in selector:
			local_css_has_signature_style = True

		if "abbr" in selector and "nowrap" in rules:
			abbr_with_whitespace.append(selector)

		if regex.search(r"\[\s*xml\s*\|", selector, flags=regex.IGNORECASE) and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in self.local_css:
			messages.append(LintMessage("c-003", "[css]\\[xml|attr][/] selector in CSS, but no XML namespace declared ([css]@namespace xml \"http://www.w3.org/XML/1998/namespace\";[/]).", se.MESSAGE_TYPE_ERROR, local_css_path))

	if regex.search(r"\s+hyphens:.+?;(?!\s+-epub-hyphens)", self.local_css):
		messages.append(LintMessage("c-007", "[css]hyphens[/css] CSS property without [css]-epub-hyphens[/css] copy.", se.MESSAGE_TYPE_ERROR, local_css_path))

	if abbr_with_whitespace:
		messages.append(LintMessage("c-005", f"[css]abbr[/] selector does not need [css]white-space: nowrap;[/] as it inherits it from [path][link=file://{self.path / 'src/epub/css/core.css'}]core.css[/][/].", se.MESSAGE_TYPE_ERROR, local_css_path, abbr_with_whitespace))

	# Don't specify border color
	# Since we have match with a regex anyway, no point in putting it in the loop above
	matches = regex.findall(r"(?:border|color).+?(?:#[a-f0-9]{0,6}|black|white|red)", self.local_css, flags=regex.IGNORECASE)
	if matches:
		messages.append(LintMessage("c-004", "Don’t specify border colors, so that reading systems can adjust for night mode.", se.MESSAGE_TYPE_WARNING, local_css_path, matches))

	# If we select on the xml namespace, make sure we define the namespace in the CSS, otherwise the selector won't work
	# We do this using a regex and not with cssutils, because cssutils will barf in this particular case and not even record the selector.
	matches = regex.findall(r"\[\s*xml\s*\|", self.local_css)
	if matches and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in self.local_css:
		messages.append(LintMessage("c-003", "[css]\\[xml|attr][/] selector in CSS, but no XML namespace declared ([css]@namespace xml \"http://www.w3.org/XML/1998/namespace\";[/]).", se.MESSAGE_TYPE_ERROR, local_css_path))

	# Done checking local.css

	root_files = os.listdir(self.path)
	expected_root_files = ["images", "src", "LICENSE.md"]
	illegal_files = [root_file for root_file in root_files if root_file not in expected_root_files and root_file != "se-lint-ignore.xml"] # se-lint-ignore.xml is optional
	missing_files = [Path(self.path / expected_root_file) for expected_root_file in expected_root_files if expected_root_file not in root_files and expected_root_file != "LICENSE.md"] # We add more to this later on. LICENSE.md gets checked later on, so we don't want to add it twice

	# If we have illegal files, check if they are tracked in Git.
	# If they are, then they're still illegal.
	# If not, ignore them for linting purposes.
	if illegal_files:
		try:
			illegal_files = self.repo.git.ls_files(illegal_files).split("\n")
			if illegal_files and illegal_files[0] == "":
				illegal_files = []
		except:
			# If we can't initialize Git, then just pass through the list of illegal files
			pass

	for illegal_file in illegal_files:
		messages.append(LintMessage("f-001", "Illegal file or directory.", se.MESSAGE_TYPE_ERROR, Path(illegal_file)))

	# Check the long description for some errors
	try:
		# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
		# lxml unescapes this for us
		# Also, remove HTML elements like <a href> so that we don't catch quotation marks in attribute values
		long_description = self.metadata_dom.xpath("/package/metadata/meta[@property='se:long-description']")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", regex.sub(r"<[^<]+?>", "", long_description))
		if matches:
			messages.append(LintMessage("m-014", "Non-typogrified character in [xml]<meta property=\"se:long-description\">[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

		# Is the first instance of the author's last name a hyperlink in the metadata?
		authors = self.metadata_dom.xpath("/package/metadata/dc:creator")
		for author in authors:
			author_sort = self.metadata_dom.xpath(f"/package/metadata/meta[@property='file-as'][@refines='#{author.get_attr('id')}']/text()")
			if author_sort:
				author_last_name = regex.sub(r",.+$", "", author_sort[0])
				author_last_name = author_last_name.replace("'", "’") # Typogrify apostrophes so that we correctly match in the long description
				# We can't use xpath here because the long description is escaped; it has no dom to query against.
				if author_last_name in long_description and not regex.search(fr"<a href=\"https://standardebooks\.org/ebooks/.+?\">.*?{author_last_name}.*?</a>", long_description):
					messages.append(LintMessage("m-056", "Author name present in [xml]<meta property=\"se:long-description\">[/] element, but the first instance of their name is not hyperlinked to their SE author page.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# xml:lang is correct for the rest of the publication, but should be lang in the long desc
		if "xml:lang" in long_description:
			messages.append(LintMessage("m-057", "[xml]xml:lang[/] attribute in [xml]<meta property=\"se:long-description\">[/] element should be [xml]lang[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# Check for repeated punctuation
		# First replace html entities so we don't catch `&gt;,`
		matches = regex.findall(r"[,;]{2,}.{0,20}", regex.sub(r"&[a-z0-9]+?;", "", self.metadata_xml))
		if matches:
			messages.append(LintMessage("t-008", "Repeated punctuation.", se.MESSAGE_TYPE_WARNING, self.metadata_file_path, matches))

	except Exception as ex:
		raise se.InvalidSeEbookException(f"No [xml]<meta property=\"se:long-description\">[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/].") from ex

	missing_metadata_vars = [var for var in METADATA_VARIABLES if regex.search(fr"\b{var}\b", self.metadata_xml)]
	if missing_metadata_vars:
		messages.append(LintMessage("m-055", "Missing data in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, missing_metadata_vars))

	# Check if there are non-typogrified quotes or em-dashes in the title.
	try:
		title = self.metadata_dom.xpath("/package/metadata/dc:title")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", title)
		if matches:
			messages.append(LintMessage("m-012", "Non-typogrified character in [xml]<dc:title>[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

		# Do we need an se:alternate-title meta element?
		# Match spelled-out numbers with a word joiner, so for ex. we don't print "eight" if we matched "eighty"
		matches = regex.findall(r"(?:[0-9]+|\bone\b|\btwo\b|\bthree\b|\bfour\b|\bfive\b|\bsix\b|\bseven\b|\beight\b|\bnine\b|\bten\b|\beleven\b|\btwelve\b|\bthirteen\b|\bfourteen\b|\bfifteen\b|\bsixteen\b|\bseventeen\b|\beighteen\b|\bnineteen\b|\btwenty\b|\bthirty\b|\bforty\b|\bfifty\b|\bsixty\b|\bseventy\b|\beighty|\bninety)", title, flags=regex.IGNORECASE)
		if matches and not self.metadata_dom.xpath("/package/metadata/meta[@property = 'se:alternate-title']"):
			messages.append(LintMessage("m-052", "[xml]<dc:title>[/] element contains numbers, but no [xml]<meta property=\"se:alternate-title\"> element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))
	except:
		missing_metadata_elements.append("<dc:title>")

	try:
		file_as = self.metadata_dom.xpath("/package/metadata/meta[@property='file-as' and @refines='#title']")[0].text
		matches = regex.findall(r".(?:['\"]|\-\-|\s-\s).", file_as)
		if matches:
			messages.append(LintMessage("m-050", "Non-typogrified character in [xml]<meta property=\"file-as\" refines=\"#title\">[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))
	except:
		missing_metadata_elements.append("<meta property=\"file-as\" refines=\"#title\">")

	try:
		description = self.metadata_dom.xpath("/package/metadata/dc:description")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", description)
		if matches:
			messages.append(LintMessage("m-013", "Non-typogrified character in [xml]<dc:description>[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))
	except:
		missing_metadata_elements.append("<dc:description>")

	# Check for double spacing
	matches = regex.findall(fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}", self.metadata_xml)
	if matches:
		double_spaced_files.append(self.metadata_file_path)

	# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
	matches = regex.findall(r"[\p{Letter}]+”[,\.](?! …)", self.metadata_xml)
	if matches:
		messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation goes within single and double quotes.", se.MESSAGE_TYPE_WARNING, self.metadata_file_path))

	# Make sure long-description is escaped HTML
	if "<" not in long_description:
		messages.append(LintMessage("m-016", "Long description must be escaped HTML.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
	else:
		# Check for malformed long description HTML
		try:
			etree.parse(io.StringIO(f"<?xml version=\"1.0\"?><html xmlns=\"http://www.w3.org/1999/xhtml\">{long_description}</html>"))
		except lxml.etree.XMLSyntaxError as ex:
			messages.append(LintMessage("m-015", f"Metadata long description is not valid XHTML. LXML says: {ex}", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for HTML entities in long-description, but allow &amp;amp;
	matches = regex.findall(r"&[a-z0-9]+?;", long_description.replace("&amp;", ""))
	if matches:
		messages.append(LintMessage("m-018", "HTML entities found. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

	# Check for tags that imply other tags
	implied_tags = {"Fiction": ["Science Fiction", "Drama", "Fantasy"]}
	for implied_tag, tags in implied_tags.items():
		if self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:subject' and text()='{implied_tag}']"):
			for tag in tags:
				if self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:subject' and text()='{tag}']"):
					messages.append(LintMessage("m-058", f"[val]se:subject[/] of [text]{implied_tag}[/] found, but [text]{tag}[/] implies [text]{implied_tag}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

	# Check for illegal em-dashes in <dc:subject>
	nodes = self.metadata_dom.xpath("/package/metadata/dc:subject[contains(text(), '—')]")
	if nodes:
		messages.append(LintMessage("m-019", "Illegal em-dash in [xml]<dc:subject>[/] element; use [text]--[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.text for node in nodes]))

	# Check for empty production notes
	if self.metadata_dom.xpath("/package/metadata/meta[@property='se:production-notes' and text()='Any special notes about the production of this ebook for future editors/producers? Remove this element if not.']"):
		messages.append(LintMessage("m-022", "Empty [xml]<meta property=\"se:production-notes\">[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for illegal VCS URLs
	nodes = self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:url.vcs.github' and not(text() = '{self.generated_github_repo_url}')]")
	if nodes:
		messages.append(LintMessage("m-009", f"[xml]<meta property=\"se:url.vcs.github\">[/] value does not match expected: [url]{self.generated_github_repo_url}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for HathiTrust scan URLs instead of actual record URLs
	if "babel.hathitrust.org" in self.metadata_xml or "hdl.handle.net" in self.metadata_xml:
		messages.append(LintMessage("m-011", "Use HathiTrust record URLs, not page scan URLs, in metadata, imprint, and colophon. Record URLs look like: [url]https://catalog.hathitrust.org/Record/<RECORD-ID>[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for illegal se:subject tags
	illegal_subjects = []
	nodes = self.metadata_dom.xpath("/package/metadata/meta[@property='se:subject']/text()")
	if nodes:
		for node in nodes:
			if node not in SE_GENRES:
				illegal_subjects.append(node)

		if illegal_subjects:
			messages.append(LintMessage("m-020", "Illegal value for [xml]<meta property=\"se:subject\">[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, illegal_subjects))

		if sorted(nodes) != nodes:
			messages.append(LintMessage("m-053", "[xml]<meta property=\"se:subject\">[/] elements not in alphabetical order.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	else:
		messages.append(LintMessage("m-021", "No [xml]<meta property=\"se:subject\">[/] element found.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for CDATA tags
	if "<![CDATA[" in self.metadata_xml:
		messages.append(LintMessage("m-017", "[xml]<!\\[CDATA\\[[/] found. Run [bash]se clean[/] to canonicalize [xml]<!\\[CDATA\\[[/] sections.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check that our provided identifier matches the generated identifier
	try:
		identifier = self.metadata_dom.xpath("/package/metadata/dc:identifier")[0].text
		if identifier != self.generated_identifier:
			messages.append(LintMessage("m-023", f"[xml]<dc:identifier>[/] does not match expected: [text]{self.generated_identifier}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
	except:
		missing_metadata_elements.append("<dc:identifier>")

	# Check if se:name.person.full-name matches their titlepage name
	duplicate_names = []
	invalid_refines = []
	nodes = self.metadata_dom.xpath("/package/metadata/meta[@property='se:name.person.full-name']")
	for node in nodes:
		try:
			refines = node.get_attr("refines").replace("#", "")
			try:
				name = self.metadata_dom.xpath(f"/package/metadata/*[@id = '{refines}']")[0].text
				if name == node.text:
					duplicate_names.append(name)
			except:
				invalid_refines.append(refines)
		except:
			invalid_refines.append("<meta property=\"se:name.person.full-name\">")

	if duplicate_names:
		messages.append(LintMessage("m-024", "[xml]<meta property=\"se:name.person.full-name\">[/] property identical to regular name. If the two are identical the full name [xml]<meta>[/] element must be removed.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, duplicate_names))

	if invalid_refines:
		messages.append(LintMessage("m-010", "Invalid [xml]refines[/] property.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, invalid_refines))

	# Check for malformed URLs
	messages = messages + _get_malformed_urls(self.metadata_xml, self.metadata_file_path)

	if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", self.metadata_xml):
		messages.append(LintMessage("m-008", "[url]id.loc.gov[/] URL ending with illegal [path].html[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Does the manifest match the generated manifest?
	try:
		manifest = self.metadata_dom.xpath("/package/manifest")[0]
		if manifest.to_string().replace("\t", "") != self.generate_manifest().replace("\t", ""):
			messages.append(LintMessage("m-042", "[xml]<manifest>[/] element does not match expected structure.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
	except:
		missing_metadata_elements.append("<manifest>")

	if missing_metadata_elements:
		messages.append(LintMessage("m-051", "Missing expected element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, missing_metadata_elements))

	# Check for common typos
	matches = [match[0] for match in regex.findall(r"\s((the|and|of|or|as)\s\2)\s", self.metadata_xml, flags=regex.IGNORECASE)]
	if matches:
		messages.append(LintMessage("t-042", "Possible typo.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

	# Make sure some static files are unchanged
	try:
		with importlib_resources.path("se.data.templates", "LICENSE.md") as license_file_path:
			if not filecmp.cmp(license_file_path, self.path / "LICENSE.md"):
				messages.append(LintMessage("f-003", f"File does not match [path][link=file://{self.path / 'LICENSE.md'}]{license_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.path / "LICENSE.md"))
	except Exception:
		missing_files.append(self.path / "LICENSE.md")

	try:
		with importlib_resources.path("se.data.templates", "core.css") as core_css_file_path:
			if not filecmp.cmp(core_css_file_path, self.path / "src/epub/css/core.css"):
				messages.append(LintMessage("f-004", f"File does not match [path][link=file://{self.path / 'src/epub/css/core.css'}]{core_css_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.path / "src/epub/css/core.css"))
	except Exception:
		missing_files.append(self.path / "src/epub/css/core.css")

	try:
		with importlib_resources.path("se.data.templates", "logo.svg") as logo_svg_file_path:
			if not filecmp.cmp(logo_svg_file_path, self.path / "src/epub/images/logo.svg"):
				messages.append(LintMessage("f-005", f"File does not match [path][link=file://{self.path / 'src/epub/images/logo.svg'}]{logo_svg_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.path / "src/epub/images/logo.svg"))
	except Exception:
		missing_files.append(self.path / "src/epub/images/logo.svg")

	try:
		with importlib_resources.path("se.data.templates", "uncopyright.xhtml") as uncopyright_file_path:
			if not filecmp.cmp(uncopyright_file_path, self.path / "src/epub/text/uncopyright.xhtml"):
				messages.append(LintMessage("f-006", f"File does not match [path][link=file://{self.path / 'src/epub/text/uncopyright.xhtml'}]{uncopyright_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.path / "src/epub/text/uncopyright.xhtml"))
	except Exception:
		missing_files.append(self.path / "src/epub/text/uncopyright.xhtml")

	try:
		with importlib_resources.path("se.data.templates", "se.css") as core_css_file_path:
			if not filecmp.cmp(core_css_file_path, self.path / "src/epub/css/se.css"):
				messages.append(LintMessage("f-014", f"File does not match [path][link=file://{self.path / 'src/epub/css/se.css'}]{core_css_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.path / "src/epub/css/se.css"))
	except Exception:
		missing_files.append(self.path / "src/epub/css/se.css")

	# Now iterate over individual files for some checks
	for root, directories, filenames in os.walk(self.path):
		if ".git" in directories:
			directories.remove(".git")

		for directory in natsorted(directories):
			if directory == "META-INF":
				continue

			url_safe_filename = se.formatting.make_url_safe(directory)
			if directory != url_safe_filename:
				directories_not_url_safe.append(Path(root) / directory)

		for filename in natsorted(filenames):
			filename = (Path(root) / filename).resolve()

			if filename.suffix == ".jpeg":
				messages.append(LintMessage("f-011", "JPEG files must end in [path].jpg[/].", se.MESSAGE_TYPE_ERROR, filename))

			if filename.suffix == ".tiff":
				messages.append(LintMessage("f-012", "TIFF files must end in [path].tif[/].", se.MESSAGE_TYPE_ERROR, filename))

			if filename.stem == "cover.source":
				has_cover_source = True

			if "-0" in filename.name:
				messages.append(LintMessage("f-009", "Illegal leading [text]0[/] in filename.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.stem != "LICENSE":
				url_safe_filename = se.formatting.make_url_safe(filename.stem) + filename.suffix
				if filename.name != url_safe_filename and not filename.stem.endswith(".source"):
					files_not_url_safe.append(filename)

			if filename.name == "cover.jpg":
				try:
					image = Image.open(filename)
					if image.size != (se.COVER_WIDTH, se.COVER_HEIGHT):
						messages.append(LintMessage("s-051", f"Wrong height or width. [path][link=file://{self.path / 'images/cover.jpg'}]cover.jpg[/][/] must be exactly {se.COVER_WIDTH} × {se.COVER_HEIGHT}.", se.MESSAGE_TYPE_ERROR, filename))

				except UnidentifiedImageError as ex:
					raise se.InvalidFileException(f"Couldn’t identify image type of [path][link=file://{filename}]{filename.name}[/][/].") from ex

			if filename.suffix in BINARY_EXTENSIONS or filename.name == "core.css":
				continue

			# Read the file and start doing some serious checks!
			with open(filename, "r", encoding="utf-8") as file:
				try:
					file_contents = file.read()
				except UnicodeDecodeError:
					# This is more to help developers find weird files that might choke 'lint', hopefully unnecessary for end users
					messages.append(LintMessage("f-010", "Problem decoding file as utf-8.", se.MESSAGE_TYPE_ERROR, filename))
					continue

			# Remove comments before we do any further processing
			file_contents = regex.sub(r"<!--.+?-->", "", file_contents, flags=regex.DOTALL)

			matches = regex.findall(r"http://standardebooks\.org[^\"<\s]*", file_contents)
			if matches:
				messages.append(LintMessage("m-003", "Non-HTTPS URL.", se.MESSAGE_TYPE_ERROR, filename, matches))

			if "UTF-8" in file_contents:
				messages.append(LintMessage("x-001", "String [text]UTF-8[/] must always be lowercase.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.suffix == ".svg":
				svg_dom = _dom(filename)

				# Check for fill: #000 which should simply be removed
				nodes = svg_dom.xpath("//*[contains(@fill, '#000') or contains(translate(@style, ' ', ''), 'fill:#000')]")
				if nodes:
					messages.append(LintMessage("x-004", "Illegal [xml]style=\"fill: #000\"[/] or [xml]fill=\"#000\"[/].", se.MESSAGE_TYPE_ERROR, filename))

				# Check for illegal height or width on root <svg> element
				if filename.name != "logo.svg": # Do as I say, not as I do...
					if svg_dom.xpath("//svg[@height or @width]"):
						messages.append(LintMessage("x-005", "Illegal [xml]height[/] or [xml]width[/] attribute on root [xml]<svg>[/] element. Size SVGs using the [xml]viewBox[/] attribute only.", se.MESSAGE_TYPE_ERROR, filename))

				match = regex.search(r"viewbox", file_contents, flags=regex.IGNORECASE)
				if match and match[0] != "viewBox":
					messages.append(LintMessage("x-006", f"[xml]{match}[/] found instead of [xml]viewBox[/]. [xml]viewBox[/] must be correctly capitalized.", se.MESSAGE_TYPE_ERROR, filename))

				# Check for illegal transform or id attribute
				nodes = svg_dom.xpath("//*[@transform or @id]")
				if nodes:
					invalid_transform_attributes = set()
					invalid_id_attributes = []
					for node in nodes:
						if node.get_attr("transform"):
							invalid_transform_attributes.add(f"transform=\"{node.get_attr('transform')}\"")

						if node.get_attr("id"):
							invalid_id_attributes.append(f"id=\"{node.get_attr('id')}\"")

					if invalid_transform_attributes:
						messages.append(LintMessage("x-003", "Illegal [xml]transform[/] attribute. SVGs should be optimized to remove use of [xml]transform[/]. Try using Inkscape to save as an “optimized SVG”.", se.MESSAGE_TYPE_ERROR, filename, invalid_transform_attributes))

					if invalid_id_attributes:
						messages.append(LintMessage("x-014", "Illegal [xml]id[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, invalid_id_attributes))

				if f"{os.sep}src{os.sep}" not in root:
					# Check that cover and titlepage images are in all caps
					if filename.name == "cover.svg":
						nodes = svg_dom.xpath("//text[re:test(., '[a-z]')]")
						if nodes:
							messages.append(LintMessage("s-002", "Lowercase letters in cover. Cover text must be all uppercase.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

						# For later comparison with titlepage
						cover_svg_title = svg_dom.xpath("/svg/title/text()", True).replace("The cover for ", "") # <title> can appear on any element in SVG, but we only want to check the root one

					if filename.name == "titlepage.svg":
						nodes = svg_dom.xpath("//text[re:test(., '[a-z]') and not(text() = 'translated by' or text() = 'illustrated by' or text() = 'and')]")
						if nodes:
							messages.append(LintMessage("s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except [text]translated by[/] and [text]illustrated by[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

						# For later comparison with cover
						titlepage_svg_title = svg_dom.xpath("/svg/title/text()", True).replace("The titlepage for ", "") # <title> can appear on any element in SVG, but we only want to check the root one

			if filename.suffix == ".xml":
				xml_dom = _dom(filename)

				# / selects the root element, so we have to test against the name instead of doing /search-key-map
				if xml_dom.xpath("/*[name() = 'search-key-map']") and filename.name != "glossary-search-key-map.xml":
					messages.append(LintMessage("f-013", "Glossary search key map must be named [path]glossary-search-key-map.xml[/].", se.MESSAGE_TYPE_ERROR, filename))

			if filename.suffix == ".xhtml":
				# Read file contents into a DOM for querying
				dom = _dom(filename)

				messages = messages + _get_malformed_urls(file_contents, filename)

				# concat() to not match `halftitlepage`
				if dom.xpath("/html/body/section[contains(concat(' ', @epub:type, ' '), ' titlepage ')]"):
					if not dom.xpath("/html/head/title[text() = 'Titlepage']"):
						messages.append(LintMessage("s-025", "Titlepage [xhtml]<title>[/] elements must contain exactly: [text]Titlepage[/].", se.MESSAGE_TYPE_ERROR, filename))
				else:
					# Check for common typos
					# Don't check the titlepage because it has a standard format and may raise false positives
					matches = [match[0] for match in regex.findall(r"\s((the|and|of|or|as)\s\2)\s", file_contents, flags=regex.IGNORECASE)]
					if matches:
						messages.append(LintMessage("t-042", "Possible typo.", se.MESSAGE_TYPE_ERROR, filename, matches))

				if dom.xpath("/html/body/section[contains(@epub:type, 'colophon')]"):
					# Check for wrong grammar filled in from template
					nodes = dom.xpath("/html/body//a[starts-with(@href, 'https://books.google.com/') or starts-with(@href, 'https://www.google.com/books/')][(preceding-sibling::text()[normalize-space(.)][1])[re:test(., '\\bthe$')]]")
					if nodes:
						messages.append(LintMessage("s-016", "Incorrect [text]the[/] before Google Books link.", se.MESSAGE_TYPE_ERROR, filename, ["the<br/>\n" + node.to_string() for node in nodes]))

					se_url = self.generated_identifier.replace('url:', '')
					if not dom.xpath(f"/html/body//a[@href = '{se_url}' and text() = '{se_url.replace('https://', '')}']"):
						messages.append(LintMessage("m-035", f"Unexpected SE identifier in colophon. Expected: [url]{se_url}[/].", se.MESSAGE_TYPE_ERROR, filename))

					if ">trl<" in self.metadata_xml and "translated from" not in file_contents:
						messages.append(LintMessage("m-025", "Translator found in metadata, but no [text]translated from LANG[/] block in colophon.", se.MESSAGE_TYPE_ERROR, filename))

					# Check if we forgot to fill any variable slots
					missing_colophon_vars = [var for var in COLOPHON_VARIABLES if regex.search(fr"\b{var}\b", file_contents)]
					if missing_colophon_vars:
						messages.append(LintMessage("m-036", "Missing data in colophon.", se.MESSAGE_TYPE_ERROR, filename, missing_colophon_vars))

					# Check that we have <br/>s at the end of lines
					# First, check for b or a elements that are preceded by a newline but not by a br
					nodes = [node.to_string() for node in dom.xpath("/html/body/section/p/*[name() = 'b' or name() = 'a'][(preceding-sibling::node()[1])[contains(., '\n')]][not((preceding-sibling::node()[2])[self::br]) or (normalize-space(preceding-sibling::node()[1]) and re:test(preceding-sibling::node()[1], '\\n\\s*$')) ]")]
					# Next, check for text nodes that contain newlines but are not preceded by brs
					nodes = nodes + [node.strip() for node in dom.xpath("/html/body/section/p/text()[contains(., '\n') and normalize-space(.)][(preceding-sibling::node()[1])[not(self::br)]]")]
					if nodes:
						messages.append(LintMessage("s-053", "Colophon line not preceded by [xhtml]<br/>[/].", se.MESSAGE_TYPE_ERROR, filename, nodes))

					# Is there a comma after a producer name, if there's only two producers?
					nodes = dom.xpath("/html/body/section/p/*[name() = 'b' or name() = 'a'][(following-sibling::node()[1])[normalize-space(.) = ', and']][(preceding-sibling::*[1])[name() = 'br']]")
					if nodes:
						messages.append(LintMessage("t-006", "Comma after producer name, but there are only two producers.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

					# Are the sources represented correctly?
					# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
					nodes = self.metadata_dom.xpath("/package/metadata/dc:source")
					if len(nodes) <= 2:
						for node in nodes:
							link = node.text
							if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
								messages.append(LintMessage("m-037", f"Source not represented in colophon.xhtml. Expected: [xhtml]<a href=\"{link}\">Project Gutenberg</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

							if "hathitrust.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
								messages.append(LintMessage("m-038", f"Source not represented in colophon.xhtml. Expected: [xhtml]the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

							if "archive.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">Internet Archive</a>" not in file_contents:
								messages.append(LintMessage("m-039", f"Source not represented in colophon.xhtml. Expected: [xhtml]the<br/> <a href=\"{link}\">Internet Archive</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

							if ("books.google.com" in link or "www.google.com/books/" in link) and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
								messages.append(LintMessage("m-040", f"Source not represented in colophon.xhtml. Expected: [xhtml]<a href=\"{link}\">Google Books</a>[/].", se.MESSAGE_TYPE_WARNING, filename))


					# Is there a page scan link in the colophon, but missing in the metadata?
					for node in dom.xpath("/html/body//a[re:test(@href, '(gutenberg\\.org/ebooks/[0-9]+|hathitrust\\.org|archive\\.org|books\\.google\\.com|www\\.google\\.com/books/)')]"):
						if not self.metadata_dom.xpath(f"/package/metadata/dc:source[contains(text(), '{node.get_attr('href')}')]"):
							messages.append(LintMessage("m-059", f"Link to [url]{node.get_attr('href')}[/] found in colophon, but missing matching [xhtml]dc:source[/] element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

				else:
					# This file is not the colophon.
					# Check for ending punctuation inside italics that have semantics.
					# Ignore the colophon because paintings might have punctuation in their names

					# This xpath matches b or i elements with epub:type="se:name...", that are not stage direction, whose last text node ends in punctuation.
					# Note that we check that the last node is a text node, because we may have <abbr> a sthe last node
					matches = [node.to_string() for node in dom.xpath("(//b | //i)[contains(@epub:type, 'se:name') and not(contains(@epub:type, 'z3998:stage-direction'))][(text()[last()])[re:test(., '[\\.,!\\?]$')]]")]

					# ...and also check for ending punctuation inside em tags, if it looks like a *part* of a clause
					# instead of a whole clause. If the <em> is preceded by an em dash or quotes, or if there's punctuation
					# and a space bofore it, then it's presumed to be a whole clause.
					# We can't use xpath for this one because xpath's regex engine doesn't seem to work with {1,2}
					matches = matches + [match.strip() for match in regex.findall(r"(?<!.[—“‘>]|[!\.\?…;]\s)<em>(?:\w+?\s*)+[\.,\!\?;]</em>", file_contents) if match.islower()]

					if matches:
						messages.append(LintMessage("t-017", "Ending punctuation inside italics. Ending punctuation is only allowed within italics if the phrase is an independent clause.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for unused selectors
				if dom.xpath("/html/head/link[contains(@href, 'local.css')]"):
					for selector in local_css_selectors:
						try:
							sel = se.easy_xml.css_selector(selector)
						except lxml.cssselect.ExpressionError as ex:
							# This gets thrown on some selectors not yet implemented by lxml, like *:first-of-type
							unused_selectors.remove(selector)
							continue
						except Exception as ex:
							raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: [css]{selector}[/]. Exception: {ex}")

						if dom.xpath(sel.path):
							unused_selectors.remove(selector)

				# Update our list of local.css selectors to check in the next file
				local_css_selectors = list(unused_selectors)

				# Done checking for unused selectors.

				# Check if this is a frontmatter file
				if filename.name not in ("titlepage.xhtml", "imprint.xhtml", "toc.xhtml"):
					if dom.xpath("//*[contains(@epub:type, 'frontmatter')]"):
						has_frontmatter = True

				# Add new CSS classes to global list
				if filename.name not in se.IGNORED_FILENAMES:
					for node in dom.xpath("//*[@class]"):
						for css_class in node.get_attr("class").split():
							if css_class in xhtml_css_classes:
								xhtml_css_classes[css_class] += 1
							else:
								xhtml_css_classes[css_class] = 1

				# Check for whitespace before noteref
				# Do this early because we remove noterefs from headers later
				nodes = dom.xpath("/html/body//a[contains(@epub:type, 'noteref') and re:test(preceding-sibling::node()[1], '\\s+$')]")
				if nodes:
					messages.append(LintMessage("t-012", "Illegal white space before noteref.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check that internal links don't begin with ../
				nodes = dom.xpath("/html/body//a[re:test(@href, '^\\.\\./text/')]")
				if nodes:
					messages.append(LintMessage("s-059", "Internal link beginning with [val]../text/[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Get the title of this file to compare against the ToC later.
				# We ignore the ToC file itself.
				# Also ignore files that have more than 3 top-level sections or articles, as these are probably compilation works that will have unique titles.
				if not dom.xpath("/html/body/nav[contains(@epub:type, 'toc')]") and not dom.xpath("/html/body[count(./section) + count(./article) > 3]"):
					try:
						header_text = dom.xpath("/html/head/title/text()")[0]
					except:
						header_text = ""

					if header_text != "":
						headings.append((header_text, str(filename)))

				# Check for direct z3998:roman spans that should have their semantic pulled into the parent element
				nodes = dom.xpath("/html/body//span[contains(@epub:type, 'z3998:roman')][not(preceding-sibling::*)][not(following-sibling::*)][not(preceding-sibling::text()[normalize-space(.)])][not(following-sibling::text()[normalize-space(.)])]")
				if nodes:
					messages.append(LintMessage("s-029", "If a [xhtml]<span>[/] exists only for the [val]z3998:roman[/] semantic, then [val]z3998:roman[/] should be pulled into parent element instead.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for z3998:roman elements with invalid values
				nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:roman')][re:test(normalize-space(text()), '[^ivxlcdmIVXLCDM]')]")
				if nodes:
					messages.append(LintMessage("s-026", "Invalid Roman numeral.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for "Hathi Trust" instead of "HathiTrust"
				if "Hathi Trust" in file_contents:
					messages.append(LintMessage("m-041", "[text]Hathi Trust[/] should be [text]HathiTrust[/].", se.MESSAGE_TYPE_ERROR, filename))

				# Check for uppercase letters in IDs or classes
				nodes = dom.xpath("//*[re:test(@id, '[A-Z]') or re:test(@class, '[A-Z]') or re:test(@epub:type, '[A-Z]')]")
				if nodes:
					messages.append(LintMessage("x-002", "Uppercase in attribute value. Attribute values must be all lowercase.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				nodes = dom.xpath("//*[re:test(@id, '^[0-9]+')]")
				if nodes:
					messages.append(LintMessage("x-007", "[attr]id[/] attributes starting with a number are illegal XHTML.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for <section> and <article> without ID attribute
				nodes = dom.xpath("/html/body//*[self::section or self::article][not(@id)]")
				if nodes:
					messages.append(LintMessage("s-011", "Element without [attr]id[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, {node.to_tag_string() for node in nodes}))

				for node in dom.xpath("/html/body//*[name() != 'section' and name() != 'article']/@id"):
					if node in id_values:
						duplicate_id_values.append(node)
					else:
						id_values[node] = True

				# Check for numeric entities
				matches = regex.findall(r"&#[0-9]+?;", file_contents)
				if matches:
					messages.append(LintMessage("s-001", "Illegal numeric entity (like [xhtml]&#913;[/]).", se.MESSAGE_TYPE_ERROR, filename))

				# Check nested <blockquote> elements, but only if it's the first child of another <blockquote>
				nodes = dom.xpath("/html/body//blockquote/*[1][name()='blockquote']")
				if nodes:
					messages.append(LintMessage("s-005", "Nested [xhtml]<blockquote>[/] element.", se.MESSAGE_TYPE_WARNING, filename))

				# Check for <hr> tags before the end of a section, which is a common PG artifact
				if dom.xpath("/html/body//hr[count(following-sibling::*) = 0]"):
					messages.append(LintMessage("s-012", "Illegal [xhtml]<hr/>[/] as last child.", se.MESSAGE_TYPE_ERROR, filename))

				# Check for space after dash
				nodes = dom.xpath("/html/body//*[name() = 'p' or name() = 'span' or name = 'em' or name = 'i' or name = 'b' or name = 'strong'][not(self::comment())][re:test(., '[a-zA-Z]-\\s(?!(and|or|nor|to|und|…)\\b)')]")
				if nodes:
					messages.append(LintMessage("t-033", "Space after dash.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for double greater-than at the end of a tag
				matches = regex.findall(r"(>>|>&gt;)", file_contents)
				if matches:
					messages.append(LintMessage("x-008", "Elements should end with a single [text]>[/].", se.MESSAGE_TYPE_WARNING, filename))

				# Check for periods followed by lowercase.
				temp_xhtml = regex.sub(r"<title>.+?</title>", "", file_contents) # Remove <title> because it might contain something like <title>Chapter 2: The Antechamber of M. de Tréville</title>
				temp_xhtml = regex.sub(r"<abbr[^>]*?>", "<abbr>", temp_xhtml) # Replace things like <abbr xml:lang="la">
				temp_xhtml = regex.sub(r"<img[^>]*?>", "", temp_xhtml) # Remove <img alt> attributes
				temp_xhtml = temp_xhtml.replace("A.B.C.", "X") # Remove A.B.C, which is not an abbreviations.
				# Note the regex also excludes preceding numbers, so that we can have inline numbering like:
				# "A number of questions: 1. regarding those who make heretics; 2. concerning those who were made heretics..."
				matches = regex.findall(r"[^\s0-9]+\.\s+[\p{Lowercase_Letter}](?!’[\p{Uppercase_Letter}])[\p{Lowercase_Letter}]+", temp_xhtml)
				# If <abbr> is in the match, remove it from the matches so we exclude things like <abbr>et. al.</abbr>
				matches = [match for match in matches if "<abbr>" not in match]
				if matches:
					messages.append(LintMessage("t-029", "Period followed by lowercase letter. Hint: Abbreviations require an [xhtml]<abbr>[/] element.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for nbsp before times
				nodes = dom.xpath(f"/html/body//text()[re:test(., '[0-9][^{se.NO_BREAK_SPACE}]?$')][(following-sibling::abbr[1])[contains(@class, 'time')]]")
				if nodes:
					messages.append(LintMessage("t-009", "Required no-break space not found before [xhtml]<abbr class=\"time\">[/].", se.MESSAGE_TYPE_WARNING, filename, [node[-10:] + "<abbr" for node in nodes]))

				# Check for low-hanging misquoted fruit
				matches = regex.findall(r"[\p{Letter}]+[“‘]", file_contents) + regex.findall(r"[^>]+</(?:em|i|b|span)>‘[\p{Lowercase_Letter}]+", file_contents)
				if matches:
					messages.append(LintMessage("t-028", "Possible mis-curled quotation mark.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for times with periods instead of colons.
				# Only check p, because things like tables/td are more likely to contain non-time numbers
				# Exclude numbers preceded by equals, or succeeded by some measurements
				# Also remove <a> first because they are likely to contain numbered section references
				dom_copy = deepcopy(dom)
				for node in dom_copy.xpath("/html/body//p/a"):
					node.remove()

				nodes = dom_copy.xpath("/html/body//p[re:test(., '[^=]\\s[0-9]{1,2}\\.[0-9]{2}(?![0-9′″°%]|\\.[0-9]|\\scubic|\\smetric|\\smeters|\\smiles|\\sfeet|\\sinches)')]")
				matches = []
				for node in nodes:
					for time_match in regex.findall(r"(?<=[^=]\s)[0-9]{1,2}\.[0-9]{2}(?![0-9′″°%]|\.[0-9]|\scubic|\smetric|\smeters|\smiles|\sfeet|\sinches)", node.inner_text()):
						time = time_match.split(".")
						if not time[0].startswith("0") and int(time[0]) >= 1 and int(time[0]) <= 12 and int(time[1]) >= 0 and int(time[1]) <= 59:
							matches.append(time_match)

				if matches:
					messages.append(LintMessage("t-010", "Time set with [text].[/] instead of [text]:[/].", se.MESSAGE_TYPE_WARNING, filename, set(matches)))

				# Do we have a half title?
				if dom.xpath("/html/body/section[contains(@epub:type, 'halftitlepage')]"):
					has_halftitle = True

				# Check for leading 0 in IDs (note: not the same as checking for IDs that start with an integer)
				# We only check for *leading* 0s in numbers; this allows IDs like `wind-force-0` in the Worst Journey in the World glossary.
				nodes = dom.xpath("//*[re:test(@id, '-0[0-9]')]")
				if nodes:
					messages.append(LintMessage("x-009", "Illegal leading 0 in [attr]id[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for underscores in attributes, but not if the attribute is href (links often have underscores) or MathMl alttext, which can have underscores as part of math notation
				nodes = dom.xpath("//@*[contains(., '_') and name() != 'href' and name() != 'alttext']/..")
				if nodes:
					messages.append(LintMessage("x-011", "Illegal underscore in attribute. Use dashes instead of underscores.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for stage direction that ends in ?! but also has a trailing period
				nodes = dom.xpath("/html/body//i[contains(@epub:type, 'z3998:stage-direction')][re:test(., '\\.$')][(following-sibling::node()[1])[re:test(., '^[,:;!?]')]]")
				if nodes:
					messages.append(LintMessage("t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for h# without semantics. h# that are children of hgroup are OK, as are any h# that have child elements (which likely have the correct semantics)
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][not(@epub:type)][not(./*[not(name() = 'a' and contains(@epub:type, 'noteref'))])][ancestor::*[1][name() != 'hgroup']]")
				if nodes:
					messages.append(LintMessage("s-070", "[xhtml]<h#>[/] element without [xhtml]<hgroup>[/] parent and without semantic inflection.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for <table> element without a <tbody> child
				if dom.xpath("/html/body//table[not(tbody)]"):
					messages.append(LintMessage("s-042", "[xhtml]<table>[/] element without [xhtml]<tbody>[/] child.", se.MESSAGE_TYPE_ERROR, filename))

				# Check for <th> element without a <thead> ancestor. However, <th scope="row|rowgroup">  and <th/> are allowed, for use in vertical table headers
				# like in https://standardebooks.org/ebooks/charles-babbage/passages-from-the-life-of-a-philosopher
				if dom.xpath("/html/body//table//th[not(ancestor::thead)][not(contains(@scope, 'row'))][not(count(node())=0)]"):
					messages.append(LintMessage("s-055", "[xhtml]<th>[/] element not in [xhtml]<thead>[/] ancestor. Note: [xhtml]<th>[/] elements used as horizontal row headings require the [attr]scope[/] attribute of [val]row[/] or [val]rowgroup[/].", se.MESSAGE_TYPE_ERROR, filename))

				# Check for money not separated by commas
				matches = regex.findall(r"[£\$][0-9]{4,}", file_contents)
				if matches:
					messages.append(LintMessage("t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for poetry/verse without a descendent <p> element.
				# Skip the ToC landmarks because it may have poem/verse semantic children.
				nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')][not(descendant::p)][not(ancestor::nav[contains(@epub:type, 'landmarks')])]")
				if nodes:
					messages.append(LintMessage("s-044", "Element with poem or verse semantic, without descendant [xhtml]<p>[/] (stanza) element.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

				# Check for dialog starting with a lowercase letter. Only check the first child text node of <p>, because other first children might be valid lowercase, like <m:math> or <b>;
				# exclude <p> inside or preceded by <blockquote>; and exclude <p> inside endnotes, as definitions may start with lowercase letters.
				nodes = dom.xpath("/html/body//p[not(ancestor::blockquote or ancestor::li[contains(@epub:type, 'endnote')]) and not(preceding-sibling::*[1][name() = 'blockquote'])][re:test(./node()[1], '^“[a-z]')]")
				if nodes:
					messages.append(LintMessage("t-042", "Possible typo.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for body element without child section or article. Ignore the ToC because it has a unique structure
				nodes = dom.xpath("/html/body[not(./*[name() = 'section' or name() = 'article' or (name() = 'nav' and contains(@epub:type, 'toc'))])]")
				if nodes:
					messages.append(LintMessage("s-069", "[xhtml]<body>[/] element missing direct child [xhtml]<section>[/] or [xhtml]<article>[/] element.", se.MESSAGE_TYPE_ERROR, filename))

				# Check for header elements that are entirely non-English
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][./i[@xml:lang][count(preceding-sibling::node()[normalize-space(.)]) + count(following-sibling::node()[normalize-space(.)]) = 0]]")
				if nodes:
					messages.append(LintMessage("s-024", "Header elements that are entirely non-English should not be set in italics. Instead, the [xhtml]<h#>[/] element has the [attr]xml:lang[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for header elements that have a label, but are missing the label semantic
				# Find h# nodes whose first child is a text node matching a label type, and where that text node's next sibling is a semantic roman numeral
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][./node()[1][self::text() and not(./*) and re:test(normalize-space(.), '^(Part|Book|Volume|Section|Act|Scene)$') and following-sibling::*[1][contains(@epub:type, 'z3998:roman')]]]")
				if nodes:
					messages.append(LintMessage("s-066", "Header element missing [val]label[/] semantic.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for header elements that are missing both label and ordinal semantics
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][not(./*) and re:match(normalize-space(.), '^(Part|Book|Volume|Section|Act|Scene)\\s+[ixvIXVmcd]+$')]")
				if nodes:
					messages.append(LintMessage("s-073", "Header element that requires [val]label[/] and [val]ordinal[/] semantic children.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for header elements that have a label semantic, but are missing an ordinal sibling
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][./span[contains(@epub:type, 'label')]][not(./span[contains(@epub:type, 'ordinal')])]")
				if nodes:
					messages.append(LintMessage("s-067", "Header element with a [val]label[/] semantic child, but without an [val]ordinal[/] semantic child.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for sectioning elements with more than one heading element
				nodes = dom.xpath("/html/body//*[name() = 'article' or name() = 'section'][count(./*[name() = 'header' or name() = 'hgroup' or re:test(name(), '^h[1-6]$')]) > 1]")
				if nodes:
					messages.append(LintMessage("s-071", "Sectioning element with more than one heading element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for some elements that only have a <span> child (including text inline to the parent).
				# But, exclude such elements that are <p> elements that have poetry-type parents.
				nodes = dom.xpath("/html/body//*[name() != 'p' and not(ancestor-or-self::*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')])][./span[count(preceding-sibling::node()[normalize-space(.)]) + count(following-sibling::node()[normalize-space(.)]) = 0]]")
				if nodes:
					messages.append(LintMessage("s-072", "Element with single [xhtml]<span>[/] child. [xhtml]<span>[/] should be removed and its attributes promoted to the parent element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for header elements with a roman semantic but without an ordinal semantic
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][contains(@epub:type, 'z3998:roman') and not(contains(@epub:type, 'ordinal'))]")
				if nodes:
					messages.append(LintMessage("s-068", "Header element missing [val]ordinal[/] semantic.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for deprecated MathML elements
				# Note we dont select directly on element name, because we want to ignore any namespaces that may (or may not) be defined
				nodes = dom.xpath("/html/body//*[name()='mfenced']")
				if nodes:
					messages.append(LintMessage("s-017", "[xhtml]<m:mfenced>[/] is deprecated in the MathML spec. Use [xhtml]<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>[/].", se.MESSAGE_TYPE_ERROR, filename, {node.to_tag_string() for node in nodes}))

				# Check for period following Roman numeral, which is an old-timey style we must fix
				# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
				nodes = dom.xpath("/html/body//node()[name()='span' and contains(@epub:type, 'z3998:roman') and not(position() = 1)][(following-sibling::node()[1])[re:test(., '^\\.\\s*[a-z]')]]")
				if nodes:
					messages.append(LintMessage("t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() + "." for node in nodes]))

				# Check for <abbr> elements that have two or more letters/periods, that don't have a semantic class
				nodes = [node.to_string() for node in dom.xpath("/html/body//abbr[not(@class)][text() != 'U.S.'][re:test(., '([A-Z]\\.?){2,}')]") if node.text not in initialism_exceptions]
				if nodes:
					messages.append(LintMessage("s-045", "[xhtml]<abbr>[/] element without semantic class like [class]name[/] or [class]initialism[/].", se.MESSAGE_TYPE_WARNING, filename, nodes))

				# Check for two em dashes in a row
				matches = regex.findall(fr"—{se.WORD_JOINER}*—+", file_contents)
				if matches:
					messages.append(LintMessage("t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename))

				nodes = dom.xpath("/html/body//blockquote//p[parent::*[name() = 'footer'] or parent::*[name() = 'blockquote']]//cite") # Sometimes the <p> may be in a <footer>
				if nodes:
					messages.append(LintMessage("s-054", "[xhtml]<cite>[/] as child of [xhtml]<p>[/] in [xhtml]<blockquote>[/]. [xhtml]<cite>[/] should be the direct child of [xhtml]<blockquote>[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for a common typo
				if "z3998:nonfiction" in file_contents:
					messages.append(LintMessage("s-030", "[val]z3998:nonfiction[/] should be [val]z3998:non-fiction[/].", se.MESSAGE_TYPE_ERROR, filename))

				# Check for initialisms without periods
				nodes = [node.to_string() for node in dom.xpath("/html/body//abbr[contains(@class, 'initialism') and not(re:test(., '^[0-9]*([a-zA-Z]\\.)+[0-9]*$'))]") if node.text not in initialism_exceptions]
				if nodes:
					messages.append(LintMessage("t-030", "Initialism with spaces or without periods.", se.MESSAGE_TYPE_WARNING, filename, set(nodes)))

				# Check for <abbr class="name"> that does not contain spaces
				nodes = dom.xpath("/html/body//abbr[contains(@class, 'name')][re:test(., '[A-Z]\\.[A-Z]\\.')]")
				if nodes:
					messages.append(LintMessage("t-016", "Initials in [xhtml]<abbr class=\"name\">[/] not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for z3998:stage-direction on elements that are not <i>
				nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:stage-direction') and name() != 'i' and name() != 'abbr' and name() != 'p']")
				if nodes:
					messages.append(LintMessage("s-058", "[attr]z3998:stage-direction[/] semantic only allowed on [xhtml]<i>[/], [xhtml]<abbr>[/], and [xhtml]<p>[/] elements.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for missing punctuation in continued quotations
				# ” said Bob “
				nodes = dom.xpath(r"/html/body//p[re:test(., '”\s(?:said|[A-Za-z]{2,}ed)\s[A-Za-z]+?(?<!\bthe)(?<!\bto)(?<!\bwith)(?<!\bfrom)(?<!\ba\b)(?<!\bis)\s“') or re:test(., '[^\.]”\s(\bhe\b|\bshe\b|I|[A-Z][a-z]+?)\s(?:said|[A-Za-z]{2,}ed)\s“')]")
				if nodes:
					messages.append(LintMessage("t-043", "Dialog tag missing punctuation.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for abbreviations followed by periods
				# But we exclude some SI units, which don't take periods; abbreviations ending in numbers for example in stage directions; abbreviations like `r^o` (recto) that contain <sup>; and some Imperial abbreviations that are multi-word
				nodes = dom.xpath("/html/body//abbr[(contains(@class, 'initialism') or contains(@class, 'name') or not(@class))][not(re:test(., '[cmk][mgl]')) and not(re:test(., '[0-9]$')) and not(./sup) and not(text()='mpg' or text()='mph' or text()='hp' or text()='TV')][following-sibling::text()[1][starts-with(self::text(), '.')]]")
				if nodes:
					messages.append(LintMessage("t-032", "Initialism or name followed by period. Hint: Periods go within [xhtml]<abbr>[/]. [xhtml]<abbr>[/]s containing periods that end a clause require the [class]eoc[/] class.", se.MESSAGE_TYPE_WARNING, filename, [f"{node.to_string()}." for node in nodes]))

				# Check for block-level tags that end with <br/>
				nodes = dom.xpath("/html/body//*[self::p or self::blockquote or self::table or self::ol or self::ul or self::section or self::article][br[last()][not(following-sibling::text()[normalize-space()])][not(following-sibling::*)]]")
				if nodes:
					messages.append(LintMessage("s-008", "[xhtml]<br/>[/] element found before closing tag of block-level element.", se.MESSAGE_TYPE_ERROR, filename, {node.to_tag_string() for node in nodes}))

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
				matches = [match for match in matches if "epub:type=\"se:name." not in match[0] and "epub:type=\"z3998:taxonomy" not in match[0] and not regex.match(r"^[\p{Lowercase_Letter}’]+\s“", match[0]) and not regex.match(r"^[\p{Lowercase_Letter}’]+,\s“[\p{Lowercase_Letter}]", se.formatting.remove_tags(match[0])) and not regex.match(r"^.*?<.+?>[^Ia]<.+?>", match[0])]
				if matches:
					messages.append(LintMessage("t-019", "When a complete clause is italicized, ending punctuation except commas must be within containing italics.", se.MESSAGE_TYPE_WARNING, filename, [match[0] for match in matches]))

				# Check for trailing commas inside <i> tags at the close of dialog
				# More sophisticated version of: \b[^\s]+?,</i>”
				nodes = dom.xpath("/html/body//i[re:test(., ',$')][(following-sibling::node()[1])[starts-with(., '”')]]")
				if nodes:
					messages.append(LintMessage("t-023", "Comma inside [xhtml]<i>[/] element before closing dialog.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() + "”" for node in nodes]))

				# Check for quotation marks in italicized dialog
				nodes = dom.xpath("/html/body//i[@xml:lang][starts-with(., '“') or re:test(., '”$')]")
				if nodes:
					messages.append(LintMessage("t-024", "When italicizing language in dialog, italics go inside quotation marks.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for comma after leading Or in subtitles
				nodes = dom.xpath("/html/body//*[contains(@epub:type, 'subtitle') and re:test(text(), '^Or\\s')]")
				if nodes:
					messages.append(LintMessage("t-044", "Comma required after leading [text]Or[/] in subtitles.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for style attributes
				nodes = dom.xpath("/html/body//*[@style]")
				if nodes:
					messages.append(LintMessage("x-012", "Illegal [attr]style[/] attribute. Don’t use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename, {node.to_tag_string() for node in nodes}))

				# Check for hgroup elements with only one child
				nodes = dom.xpath("/html/body//hgroup[count(*)=1]")
				if nodes:
					messages.append(LintMessage("s-009", "[xhtml]<hgroup>[/] element with only one child.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for hgroup elements with a subtitle but no title
				nodes = dom.xpath("/html/body//hgroup[./*[contains(@epub:type, 'subtitle')] and not(./*[contains(concat(' ', @epub:type, ' '), ' title ')])]")
				if nodes:
					messages.append(LintMessage("s-015", "Element has [val]subtitle[/] semantic, but without a sibling having a [val]title[/] semantic.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for illegal elements in <head>
				nodes = dom.xpath("/html/head/*[not(self::title) and not(self::link[@rel='stylesheet'])]")
				if nodes:
					messages.append(LintMessage("x-015", "Illegal element in [xhtml]<head>[/]. Only [xhtml]<title>[/] and [xhtml]<link rel=\"stylesheet\">[/] are allowed.", se.MESSAGE_TYPE_ERROR, filename, [f"<{node.lxml_element.tag}>" for node in nodes]))

				nodes = dom.xpath("//*[re:test(@xml:lang, '^[A-Z]')]")
				if nodes:
					messages.append(LintMessage("x-016", "[attr]xml:lang[/] attribute with value starting in uppercase letter.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for nbsp within <abbr class="name">, which is redundant
				nodes = dom.xpath(f"/html/body//abbr[contains(@class, 'name')][contains(text(), '{se.NO_BREAK_SPACE}')]")
				if nodes:
					messages.append(LintMessage("t-022", "No-break space found in [xhtml]<abbr class=\"name\">[/]. This is redundant.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for <span>s that only exist to apply epub:type
				nodes = dom.xpath("/html/body//*[span[@epub:type][count(preceding-sibling::node()[normalize-space(.)]) + count(following-sibling::node()[normalize-space(.)]) = 0]]")
				if nodes:
					messages.append(LintMessage("s-050", "[xhtml]<span>[/] element appears to exist only to apply [attr]epub:type[/]. [attr]epub:type[/] should go on the parent element instead, without a [xhtml]<span>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for <dt> elements without exactly one <dfn> child, but only in glossaries
				nodes = dom.xpath("/html/body//*[contains(@epub:type, 'glossary')]//dt[not(count(./dfn) = 1)]")
				if nodes:
					messages.append(LintMessage("s-062", "[xhtml]<dt>[/] element in a glossary without exactly one [xhtml]<dfn>[/] child.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for empty elements. Elements are empty if they have no children and no non-whitespace text
				nodes = dom.xpath("/html/body//*[not(self::br) and not(self::hr) and not(self::img) and not(self::td) and not(self::th) and not(self::m:none) and not(self::m:mspace) and not(self::m:mprescripts) and not(self::link)][not(*)][not(normalize-space())]")
				if nodes:
					messages.append(LintMessage("s-010", "Empty element. Use [xhtml]<hr/>[/] for thematic breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for fulltitle semantic on non-h1
				nodes = dom.xpath("/html/body//*[contains(@epub:type, 'fulltitle') and name() != 'h1' and name() != 'hgroup']")
				if nodes:
					messages.append(LintMessage("s-065", "[val]fulltitle[/] semantic on element that is not [xhtml]<h1>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for p tags preceded by blockquote that don't have the `continued` class. Exclude matches whose first child is <cite>, so we don't match things like <p><cite>—Editor</cite>
				nodes = dom.xpath("/html/body//p[(preceding-sibling::*[1])[self::blockquote]][not(contains(@class, 'continued')) and re:test(., '^([a-z]|—|…)') and not(./*[1][self::cite])]")
				if nodes:
					messages.append(LintMessage("t-045", "[xhtml]<p>[/] preceded by [xhtml]<blockquote>[/] and starting in a lowercase letter, but without [val]continued[/] class.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for HTML tags in <title> tags
				nodes = dom.xpath("/html/head/title/*")
				if nodes:
					messages.append(LintMessage("x-010", "Illegal element in [xhtml]<title>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for legal cases that aren't italicized
				# We can't use this because v. appears as short for "volume", and we may also have sporting events without italics.
				#nodes = dom.xpath("/html/body//abbr[text() = 'v.' or text() = 'versus'][not(parent::i)]")
				#if nodes:
				#	messages.append(LintMessage("t-xxx", "Legal case without parent [xhtml]<i>[/].", se.MESSAGE_TYPE_WARNING, filename, {f"{node.to_string()}." for node in nodes}))

				# Only do this check if there's one <h#> or one <hgroup> tag. If there's more than one, then the xhtml file probably requires an overarching title
				if len(dom.xpath("/html/body/*[name() = 'section' or name() = 'article']/*[re:test(name(), '^h[1-6]$') or name() = 'hgroup']")) == 1:
					title = se.formatting.generate_title(dom)

					if not dom.xpath(f"/html/head/title[text() = '{title}']"):
						messages.append(LintMessage("s-021", f"Unexpected value for [xhtml]<title>[/] element. Expected: [text]{title}[/]. (Beware hidden Unicode characters!)", se.MESSAGE_TYPE_ERROR, filename))

				if not local_css_has_elision_style:
					missing_styles += [node.to_tag_string() for node in dom.xpath("/html/body//span[contains(@class, 'elision')]")]

				matches = regex.findall(r"\bA\s*B\s*C\s*\b", file_contents)
				if matches:
					messages.append(LintMessage("t-031", "[text]A B C[/] must be set as [text]A.B.C.[/] It is not an abbreviation.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for elements that don't have a direct block child
				# Allow white space and comments before the first child
				# Ignore children of the ToC and landmarks as they do not require p children
				nodes = dom.xpath("/html/body//*[(name() = 'blockquote' or name() = 'dd' or name() = 'header' or name() = 'li' or name() = 'footer') and not(./ancestor::*[contains(@epub:type, 'toc') or contains(@epub:type, 'landmarks')]) and (node()[normalize-space(.) and not(self::comment())])[1][not(name() = 'p' or name() = 'blockquote' or name() = 'div' or name() = 'table' or name() = 'header' or name() = 'ul' or name() = 'ol' or name() = 'footer' or name() = 'hgroup' or re:test(name(), '^h[0-6]'))]]")
				if nodes:
					messages.append(LintMessage("s-007", "Element requires at least one block-level child.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for ldquo not correctly closed
				# Ignore closing paragraphs, line breaks, and closing cells in case ldquo means "ditto mark"
				matches = regex.findall(r"“[^‘”]+?“", file_contents)
				matches = [match for match in matches if "</p" not in match and "<br/>" not in match and "</td>" not in match]
				# xpath to check for opening quote in p, without a next child p that starts with an opening quote or an opening bracket (for editorial insertions within paragraphs of quotation); or that consists of only an ellipses (like an elided part of a longer quotation)
				# Matching <p>s can't have a poem/verse ancestor as formatting is often special for those.
				matches = matches + [regex.findall(r"“[^”]+</p>", node.to_string())[0] for node in dom.xpath("/html/body//p[re:test(., '“[^‘”]+$')][not(ancestor::*[re:test(@epub:type, 'z3998:(verse|poem|song|hymn|lyrics)')])][(following-sibling::*[1])[name()='p'][not(re:test(normalize-space(.), '^[“\\[]') or re:test(normalize-space(.), '^…$'))]]")]

				# Additionally, match short <p> tags (< 100 chars) that lack closing quote, and whose direct siblings do have closing quotes (to exclude runs of same-speaker dialog), and that is not within a blockquote, verse, or letter
				matches = matches + [regex.findall(r"“[^”]+</p>", node.to_string())[0] for node in dom.xpath("/html/body//p[re:test(., '“[^‘”]+$') and not(re:test(., '[…:]$')) and string-length(normalize-space(.)) <= 100][(following-sibling::*[1])[not(re:test(., '“[^”]+$'))] and (preceding-sibling::*[1])[not(re:test(., '“[^”]+$'))]][not(ancestor::*[re:test(@epub:type, 'z3998:(verse|poem|song|hymn|lyrics)')]) and not(ancestor::blockquote) and not (ancestor::*[contains(@epub:type, 'z3998:letter')])][(following-sibling::*[1])[name()='p'][re:test(normalize-space(.), '^[“\\[]') and not(contains(., 'continued'))]]")]
				if matches:
					messages.append(LintMessage("t-003", "[text]“[/] missing matching [text]”[/]. Note: When dialog from the same speaker spans multiple [xhtml]<p>[/] elements, it’s correct grammar to omit closing [text]”[/] until the last [xhtml]<p>[/] of dialog.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for lsquo not correctly closed
				matches = regex.findall(r"‘[^“’]+?‘", file_contents)
				matches = [match for match in matches if "</p" not in match and "<br/>" not in match]
				if matches:
					messages.append(LintMessage("t-004", "[text]‘[/] missing matching [text]’[/].", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for repeated punctuation, but first remove `&amp;` so we don't match `&amp;,`
				matches = regex.findall(r"[,;]{2,}.{0,20}", file_contents.replace("&amp;", ""))
				if matches:
					messages.append(LintMessage("t-008", "Repeated punctuation.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check obviously miscurled quotation marks
				matches = regex.findall(r".*“</p>", file_contents)
				if matches:
					messages.append(LintMessage("t-038", "[text]“[/] before closing [xhtml]</p>[/].", se.MESSAGE_TYPE_WARNING, filename, [match[-20:] for match in matches]))

				# Check for rdquo preceded by space (but not a rsquo, which might indicate a nested quotation)
				matches = regex.findall(r".*[^’]\s”", regex.sub(r"<td>.*?</td>", "", file_contents, regex.DOTALL))
				if matches:
					messages.append(LintMessage("t-037", "[text]”[/] preceded by space.", se.MESSAGE_TYPE_WARNING, filename, [match[-20:] for match in matches]))

				# Remove tds in case ldquo means "ditto mark"
				matches = regex.findall(r"”[^“‘]+?”", regex.sub(r"<td>[”\s]+?</td>", "", file_contents), flags=regex.DOTALL)
				# We create a filter to try to exclude nested quotations
				# Remove tags in case they're enclosing punctuation we want to match against at the end of a sentence.
				matches = [match for match in matches if not regex.search(r"([\.!\?;…—]|”\s)’\s", se.formatting.remove_tags(match))]

				# Try some additional matches before adding the lint message
				# Search for <p> tags that have an ending closing quote but no opening quote; but exclude <p>s that are preceded by a <blockquote>
				# or that have a <blockquote> ancestor, because that may indicate that the opening quote is elsewhere in the quotation.
				nodes = dom.xpath("/html/body//p[not(preceding-sibling::*[1][name() = 'blockquote']) and not(ancestor::blockquote) and re:test(., '^[^“]+?”$')]")
				for node in nodes:
					matches.append(node.to_string()[-20:])

				if matches:
					messages.append(LintMessage("t-036", "[text]”[/] missing matching [text]“[/].", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check if a subtitle ends in a text node with a terminal period; or if it ends in an <i> node containing a terminal period.
				nodes = dom.xpath("/html/body//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6]/*[contains(@epub:type, 'subtitle')][(./text())[last()][re:test(., '\\.$')] or (./i)[last()][re:test(., '\\.$')]]")
				if nodes:
					messages.append(LintMessage("t-040", "Subtitle with illegal ending period.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for incorrectly applied se:name semantic
				nodes = dom.xpath("/html/body//*[self::p or self::blockquote][contains(@epub:type, 'se:name.')]")
				if nodes:
					messages.append(LintMessage("s-048", "[val]se:name[/] semantic on block element. [val]se:name[/] indicates the contents is the name of something.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

				# Check that short stories are on an <article> element
				nodes = dom.xpath("/html/body/section[contains(@epub:type, 'se:short-story') or contains(@epub:type, 'se:novella')]")
				if nodes:
					messages.append(LintMessage("s-043", "[val]se:short-story[/] semantic on element that is not [xhtml]<article>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for IDs on <h#> tags
				nodes = dom.xpath("/html/body//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6][@id]")
				if nodes:
					messages.append(LintMessage("s-019", "[xhtml]<h#>[/] element with [attr]id[/] attribute. [xhtml]<h#>[/] elements should be wrapped in [xhtml]<section>[/] elements, which should hold the [attr]id[/] attribute.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

				nodes = dom.xpath("/html/body//hgroup[./*[following-sibling::*[1][name() != 'h6' and name() = name(preceding-sibling::*[1])]]]")
				if nodes:
					messages.append(LintMessage("s-074", "[xhtml]<hgroup>[/] element containing sequential [xhtml]<h#>[/] elements at the same heading level.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for possessive 's within name italics, but not in ignored files like the colophon which we know have no possessives
				if filename.name not in se.IGNORED_FILENAMES:
					nodes = dom.xpath("/html/body//i[contains(@epub:type, 'se:name.') and re:match(., '’s$')]")
					if nodes:
						messages.append(LintMessage("t-007", "Possessive [text]’s[/] within name italics. If the name in italics is doing the possessing, [text]’s[/] goes outside italics.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for <p> elems that has some element children, which are only <span> and <br> children, but the parent doesn't have poem/verse semantics.
				# Ignore spans that have a class, but not if the class is an i# class (for poetry indentation)
				nodes = dom.xpath("/html/body//p[not(./text()[normalize-space(.)])][*][not(ancestor::*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')])][not(*[not(self::span) and not(self::br)])][ (not(span[@epub:type]) and not(span[@class]) ) or span[re:test(@class, '\\bi[0-9]\\b')]]")
				if nodes:
					messages.append(LintMessage("s-046", "[xhtml]<p>[/] element containing only [xhtml]<span>[/] and [xhtml]<br>[/] elements, but its parent doesn’t have the [val]z3998:poem[/], [val]z3998:verse[/], [val]z3998:song[/], [val]z3998:hymn[/], or [val]z3998:lyrics[/] semantic. Multi-line clauses that are not verse don’t require [xhtml]<span>[/]s.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for <cite> preceded by em dash
				nodes = dom.xpath("/html/body//cite[(preceding-sibling::node()[1])[re:match(., '—$')]]")
				if nodes:
					messages.append(LintMessage("t-034", "[xhtml]<cite>[/] element preceded by em-dash. Hint: em-dashes go within [xhtml]<cite>[/] elements.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for <cite> without preceding space in text node. (preceding ( or [ are also OK)
				nodes = dom.xpath("/html/body//cite[(preceding-sibling::node()[1])[not(re:match(., '[\\[\\(\\s]$'))]]")
				if nodes:
					messages.append(LintMessage("t-035", "[xhtml]<cite>[/] element not preceded by space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check for some known initialisms with incorrect possessive apostrophes
				nodes = dom.xpath("/html/body//abbr[text()='I.O.U.'][(following-sibling::node()[1])[starts-with(., '’s')]]")
				if nodes:
					messages.append(LintMessage("t-039", "Initialism followed by [text]’s[/]. Hint: Plurals of initialisms are not followed by [text]’[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() + "’s" for node in nodes]))

				# Check for <header> elements with only h# child nodes
				nodes = dom.xpath("/html/body//header[./*[re:test(name(), 'h[1-6]') and (count(preceding-sibling::*) + count(following-sibling::*) = 0)]]")
				if nodes:
					messages.append(LintMessage("s-049", "[xhtml]<header>[/] element whose only child is an [xhtml]<h#>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for h# tags followed by header content, that are not children of <header>.
				# Only match if there is a following <p>, because we could have the case where there's an epigraph after a division title.
				nodes = dom.xpath("/html/body//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6][following-sibling::*[contains(@epub:type, 'epigraph') or contains(@epub:type, 'bridgehead')]][following-sibling::p][not(parent::header)]")
				if nodes:
					messages.append(LintMessage("s-061", "Title and following header content not in a [xhtml]<header>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check that `z3998:persona` is only on <b> or <td>. We use the contact() xpath function so we don't catch `z3998:personal-name`
				nodes = dom.xpath("/html/body//*[contains(concat(' ', @epub:type, ' '), ' z3998:persona ') and not(self::b or self::td)]")
				if nodes:
					messages.append(LintMessage("s-063", "[val]z3998:persona[/] semantic on element that is not a [xhtml]<b>[/] or [xhtml]<td>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for italics on things that shouldn't be italics
				nodes = dom.xpath("/html/body//i[contains(@epub:type, 'se:name.music.song') or contains(@epub:type, 'se:name.publication.short-story') or contains(@epub:type, 'se:name.publication.essay')]")
				if nodes:
					messages.append(LintMessage("s-060", "Italics on name that requires quotes instead.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

				# Check to see if <h#> tags are correctly titlecased
				nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][not(contains(@epub:type, 'z3998:roman'))]")
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

					# Unwrap (not remove) any subelements in subtitles, as they may trip up further regexes
					for element in node_copy.xpath(".//*[contains(@epub:type, 'subtitle')]//*"):
						element.unwrap()

					title = node_copy.inner_xml()

					# Remove leading leftover spacing and punctuation
					title = regex.sub(r"^[\s\.\,\!\?\:\;]*", "", title)

					# Normalize whitespace
					title = regex.sub(r"\s+", " ", title, flags=regex.DOTALL).strip()

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
								messages.append(LintMessage("s-023", f"Title [text]{title}[/] not correctly titlecased. Expected: [text]{titlecased_title}[/].", se.MESSAGE_TYPE_WARNING, filename))

					# No subtitle? Much more straightforward
					else:
						titlecased_title = se.formatting.titlecase(se.formatting.remove_tags(title))
						title = se.formatting.remove_tags(title)
						if title != titlecased_title:
							messages.append(LintMessage("s-023", f"Title [text]{title}[/] not correctly titlecased. Expected: [text]{titlecased_title}[/].", se.MESSAGE_TYPE_WARNING, filename))

				# Check for <figure> tags without id attributes
				nodes = dom.xpath("/html/body//img[@id]")
				if nodes:
					messages.append(LintMessage("s-018", "[xhtml]<img>[/] element with [attr]id[/] attribute. [attr]id[/] attributes go on parent [xhtml]<figure>[/] elements.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for closing dialog without comma
				matches = regex.findall(r"[\p{Lowercase_Letter}]+?” [\p{Letter}]+? said", file_contents)
				if matches:
					messages.append(LintMessage("t-005", "Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check alt attributes on images, except for the logo
				nodes = dom.xpath("/html/body//img[not(re:test(@src, '/logo.svg$'))]")
				img_no_alt = []
				img_alt_not_typogrified = []
				img_alt_lacking_punctuation = []
				for node in nodes:
					alt = node.lxml_element.get("alt")

					if alt:
						# Check for non-typogrified img alt attributes
						if regex.search(r"""('|"|--|\s-\s|&quot;)""", alt):
							img_alt_not_typogrified.append(node.to_tag_string())

						# Check alt attributes not ending in punctuation
						if filename.name not in se.IGNORED_FILENAMES and not regex.search(r"""[\.\!\?]”?$""", alt):
							img_alt_lacking_punctuation.append(node.to_tag_string())

						# Check that alt attributes match SVG titles
						img_src = node.lxml_element.get("src")
						if img_src and img_src.endswith("svg"):
							title_text = ""
							image_ref = img_src.split("/").pop()
							try:
								svg_path = self.path / "src" / "epub" / "images" / image_ref
								svg_dom = _dom(svg_path)
								try:
									title_text = svg_dom.xpath("/svg/title")[0].text
								except Exception:
									messages.append(LintMessage("s-027", f"{image_ref} missing [xhtml]<title>[/] element.", se.MESSAGE_TYPE_ERROR, svg_path))

								if title_text != "" and alt != "" and title_text != alt:
									messages.append(LintMessage("s-022", f"The [xhtml]<title>[/] element of [path][link=file://{svg_path}]{image_ref}[/][/] does not match the [attr]alt[/] attribute text in [path][link=file://{filename}]{filename.name}[/][/].", se.MESSAGE_TYPE_ERROR, filename))

							except FileNotFoundError:
								missing_files.append(self.path / f"src/epub/images/{image_ref}")

					else:
						img_no_alt.append(node.to_tag_string())

				if img_alt_not_typogrified:
					messages.append(LintMessage("t-025", "Non-typogrified [text]'[/], [text]\"[/] (as [xhtml]&quot;[/]), or [text]--[/] in image [attr]alt[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, img_alt_not_typogrified))

				if img_alt_lacking_punctuation:
					messages.append(LintMessage("t-026", "[attr]alt[/] attribute does not appear to end with punctuation. [attr]alt[/] attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename, img_alt_lacking_punctuation))

				if img_no_alt:
					messages.append(LintMessage("s-004", "[xhtml]img[/] element missing [attr]alt[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, img_no_alt))

				# Check for punctuation after endnotes
				nodes = dom.xpath(f"/html/body//a[contains(@epub:type, 'noteref')][(following-sibling::node()[1])[re:test(., '^[^\\s<–\\]\\)—{se.WORD_JOINER}a-zA-Z0-9]')]]")
				if nodes:
					messages.append(LintMessage("t-020", "Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

				# Check for correct typography around measurements like 2 ft.
				# But first remove href and id attrs because URLs and IDs may contain strings that look like measurements
				# Note that while we check m,min (minutes) and h,hr (hours) we don't check s (seconds) because we get too many false positives on years, like `the 1540s`
				matches = regex.findall(fr"\b[0-9]+[{se.NO_BREAK_SPACE}\-]?(?:[mck]?[mgl]|ft|in|min?|h|sec|hr)\.?\b", regex.sub(r"(href|id)=\"[^\"]*?\"", "", file_contents))
				# Exclude number ordinals, they're not measurements
				matches = [match for match in matches if not regex.search(r"(st|nd|rd|th)", match)]
				if matches:
					messages.append(LintMessage("t-021", "Measurement not to standard. Numbers are followed by a no-break space and abbreviated units require an [xhtml]<abbr>[/] element. See [path][link=https://standardebooks.org/manual/1.0.0/8-typography#8.8.5]semos://1.0.0/8.8.5[/][/].", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for <pre> tags
				if dom.xpath("/html/body//pre"):
					messages.append(LintMessage("s-013", "Illegal [xhtml]<pre>[/] element.", se.MESSAGE_TYPE_ERROR, filename))

				# Check for <br/> after block-level elements
				nodes = dom.xpath("/html/body//*[self::p or self::blockquote or self::table or self::ol or self::ul or self::section or self::article][following-sibling::br]")
				if nodes:
					messages.append(LintMessage("s-014", "[xhtml]<br/>[/] after block-level element.", se.MESSAGE_TYPE_ERROR, filename, {node.to_tag_string() for node in nodes}))

				# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
				matches = regex.findall(r"[\p{Letter}]+”[,\.](?! …)", file_contents)
				if matches:
					messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation goes within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check for double spacing
				matches = regex.search(fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}", file_contents)
				if matches:
					double_spaced_files.append(filename)

				# Run some checks on epub:type values
				incorrect_attrs = set()
				illegal_colons = set()
				illegal_se_namespaces = set()
				for attrs in dom.xpath("//*/@epub:type"):
					for attr in attrs.split():
						# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
						for match in regex.findall(r"^se:[\p{Lowercase_Letter}]+:(?:[\p{Lowercase_Letter}]+:?)*", attr):
							illegal_colons.add(match)

						# Did someone use periods instead of colons for the SE namespace? e.g. se.name.vessel.ship
						for match in regex.findall(r"^se\.[\p{Lowercase_Letter}]+(?:\.[\p{Lowercase_Letter}]+)*", attr):
							illegal_se_namespaces.add(match)

						# Did we draw from the z3998 vocabulary when the item exists in the epub vocabulary?
						if attr.startswith("z3998:"):
							bare_attr = attr.replace("z3998:", "")
							if bare_attr in EPUB_SEMANTIC_VOCABULARY:
								incorrect_attrs.add((attr, bare_attr))

				if illegal_colons:
					messages.append(LintMessage("s-031", "Illegal [text]:[/] in SE identifier. SE identifiers are separated by [text].[/], not [text]:[/]. E.g., [val]se:name.vessel.ship[/].", se.MESSAGE_TYPE_ERROR, filename, illegal_colons))

				if illegal_se_namespaces:
					messages.append(LintMessage("s-032", "SE namespace must be followed by a [text]:[/], not a [text].[/]. E.g., [val]se:name.vessel[/].", se.MESSAGE_TYPE_ERROR, filename, illegal_se_namespaces))

				if incorrect_attrs:
					messages.append(LintMessage("s-034", "Semantic used from the z3998 vocabulary, but the same semantic exists in the EPUB vocabulary.", se.MESSAGE_TYPE_ERROR, filename, [attr for (attr, bare_attr) in incorrect_attrs]))

				# Check for title attrs on abbr elements
				nodes = dom.xpath("/html/body//abbr[@title]")
				if nodes:
					messages.append(LintMessage("s-052", "[xhtml]<abbr>[/] element with illegal [attr]title[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# Check for leftover asterisms. Asterisms are sequences of any of these chars: * . • -⁠ —
				nodes = dom.xpath("/html/body//*[self::p or self::div][re:test(., '^\\s*[\\*\\.•\\-⁠—]\\s*([\\*\\.•\\-⁠—]\\s*)+$')]")
				if nodes:
					messages.append(LintMessage("s-038", "Illegal asterism. Section/scene breaks must be defined by an [xhtml]<hr/>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				matches = regex.findall(r"[^…]\s[!?;:,].{0,10}", file_contents) # If we don't include preceding chars, the regex is 6x faster
				if matches:
					messages.append(LintMessage("t-041", "Illegal space before punctuation.", se.MESSAGE_TYPE_ERROR, filename, matches))

				# Check for missing punctuation before closing quotes
				nodes = dom.xpath("/html/body//p[not(parent::header and position() = last())][re:test(., '[a-z]+[”’]$')]")
				if nodes:
					messages.append(LintMessage("t-011", "Missing punctuation before closing quotes.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string()[-30:] for node in nodes]))

				# Check to see if we've marked something as poetry or verse, but didn't include a first <span>
				# This xpath selects the p elements, whose parents are poem/verse, and whose first child is not a span
				nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')]/p[not(*[name()='span' and position()=1])]")
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

					messages.append(LintMessage("s-006", "Poem or verse [xhtml]<p>[/] (stanza) without [xhtml]<span>[/] (line) element.", se.MESSAGE_TYPE_WARNING, filename, matches))

				# Check to see if we included poetry or verse without the appropriate styling
				if filename.name not in se.IGNORED_FILENAMES:
					nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')][./p/span]")
					for node in nodes:
						if "z3998:poem" in node.get_attr("epub:type") and not local_css_has_poem_style:
							missing_styles.append(node.to_tag_string())

						if "z3998:verse" in node.get_attr("epub:type") and not local_css_has_verse_style:
							missing_styles.append(node.to_tag_string())

						if "z3998:song" in node.get_attr("epub:type") and not local_css_has_song_style:
							missing_styles.append(node.to_tag_string())

						if "z3998:hymn" in node.get_attr("epub:type") and not local_css_has_hymn_style:
							missing_styles.append(node.to_tag_string())

						if "z3998:lyrics" in node.get_attr("epub:type") and not local_css_has_lyrics_style:
							missing_styles.append(node.to_tag_string())

				if not local_css_has_signature_style:
					nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:signature')]")
					for node in nodes:
						missing_styles.append(node.to_tag_string())

				# For this series of selections, we select spans that are direct children of p, because sometimes a line of poetry may have a nested span.
				nodes = dom.xpath("/html/body/*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')]/descendant-or-self::*/p/span/following-sibling::*[contains(@epub:type, 'noteref') and name() = 'a' and position() = 1]")
				if nodes:
					messages.append(LintMessage("s-047", "[val]noteref[/] as a direct child of element with poem or verse semantic. [val]noteref[/]s should be in their parent [xhtml]<span>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

				# Check for space before endnote backlinks
				if dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]"):
					# Check that citations at the end of endnotes are in a <cite> element. If not typogrify will run the last space together with the em dash.
					# This tries to catch that, but limits the match to 20 chars so that we don't accidentally match a whole sentence that happens to be at the end of an endnote.
					nodes = dom.xpath(f"/html/body//li[contains(@epub:type, 'endnote')]/p[last()][re:test(., '\\.”?{se.WORD_JOINER}?—[A-Z].{{0,20}}\\s*↩$')]")
					if nodes:
						messages.append(LintMessage("s-064", "Endnote citation not wrapped in [xhtml]<cite>[/]. Em dashes go within [xhtml]<cite>[/] and it is preceded by one space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

					# Do we have to replace Ibid.?
					matches = regex.findall(r"\bibid\b", file_contents, flags=regex.IGNORECASE)
					if matches:
						messages.append(LintMessage("s-039", "[text]Ibid[/] in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing [text]Ibid[/] refers to, unless it refers to text within the same endnote.", se.MESSAGE_TYPE_WARNING, filename))

					# Match backlink elements whose preceding node doesn't end with ' ', and is also not all whitespace
					nodes = dom.xpath("/html/body//a[@epub:type='backlink'][(preceding-sibling::node()[1])[not(re:test(., ' $')) and not(normalize-space(.) = '')]]")
					if nodes:
						messages.append(LintMessage("t-027", "Endnote referrer link not preceded by exactly one space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

					# Check that endnotes have their backlink in the last <p> element child of the <li>. This also highlights backlinks that are totally missing.
					nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')][./p[last()][not(a[contains(@epub:type, 'backlink')])] or not(./p[last()])]")
					if nodes:
						messages.append(LintMessage("s-056", "Last [xhtml]<p>[/] child of endnote missing backlink.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

					# Make sure the backlink points to the same note number as the parent endnote ID
					nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')]//a[contains(@epub:type, 'backlink')][not(re:match(@href, '\\-[0-9]+$') = re:match(ancestor::li/@id, '\\-[0-9]+$'))]")
					if nodes:
						messages.append(LintMessage("s-057", "Backlink noteref fragment identifier doesn’t match endnote number.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

				# If we're in the imprint, are the sources represented correctly?
				# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
				if dom.xpath("/html/body/section[contains(@epub:type, 'imprint')]"):
					# Check for wrong grammar filled in from template
					nodes = dom.xpath("/html/body//a[starts-with(@href, 'https://books.google.com/') or starts-with(@href, 'https://www.google.com/books/')][(preceding-sibling::node()[1])[re:test(., 'the\\s+$')]]")
					if nodes:
						messages.append(LintMessage("s-016", "Incorrect [text]the[/] before Google Books link.", se.MESSAGE_TYPE_ERROR, filename, ["the " + node.to_string() for node in nodes]))

					links = self.metadata_dom.xpath("/package/metadata/dc:source/text()")
					if len(links) <= 2:
						for link in links:
							if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
								messages.append(LintMessage("m-026", f"Project Gutenberg source not present. Expected: [xhtml]<a href=\"{link}\">Project Gutenberg</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

							if "hathitrust.org" in link and f"the <a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
								messages.append(LintMessage("m-027", f"HathiTrust source not present. Expected: the [xhtml]<a href=\"{link}\">HathiTrust Digital Library</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

							if "archive.org" in link and f"the <a href=\"{link}\">Internet Archive</a>" not in file_contents:
								messages.append(LintMessage("m-028", f"Internet Archive source not present. Expected: the [xhtml]<a href=\"{link}\">Internet Archive</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

							if ("books.google.com" in link or "www.google.com/books/" in link) and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
								messages.append(LintMessage("m-029", f"Google Books source not present. Expected: [xhtml]<a href=\"{link}\">Google Books</a>[/].", se.MESSAGE_TYPE_WARNING, filename))

				# Collect certain abbr elements for later check, but not in the colophon
				if not dom.xpath("/html/body/*[contains(@epub:type, 'colophon')]"):
					abbr_elements += dom.xpath("/html/body//abbr[contains(@class, 'temperature')]")

					# note that 'temperature' contains 'era'...
					abbr_elements += dom.xpath("/html/body//abbr[contains(concat(' ', @class, ' '), ' era ')]")

					abbr_elements += dom.xpath("/html/body//abbr[contains(@class, 'acronym')]")

				# Check if language tags in individual files match the language in content.opf
				if filename.name not in se.IGNORED_FILENAMES:
					file_language = dom.xpath("/html/@xml:lang", True)
					if language != file_language:
						messages.append(LintMessage("s-033", f"File language is [val]{file_language}[/], but [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/] language is [val]{language}[/].", se.MESSAGE_TYPE_WARNING, filename))

				# Check LoI descriptions to see if they match associated figcaptions
				for node in dom.xpath("/html/body/section[contains(@epub:type, 'loi')]//li//a"):
					figure_ref = node.get_attr("href").split("#")[1]
					chapter_ref = regex.findall(r"(.*?)#.*", node.get_attr("href"))[0]
					figcaption_text = ""
					loi_text = node.inner_text()
					file_dom = _dom(self.path / "src/epub/text" / chapter_ref)

					try:
						figure = file_dom.xpath(f"//*[@id='{figure_ref}']")[0]
					except Exception:
						messages.append(LintMessage("s-040", f"[attr]#{figure_ref}[/] not found in file [path][link=file://{self.path / 'src/epub/text' / chapter_ref}]{chapter_ref}[/][/].", se.MESSAGE_TYPE_ERROR, filename))
						continue

					for child in figure.lxml_element:
						if child.tag == "img":
							figure_img_alt = child.get("alt")

						if child.tag == "figcaption":
							figcaption_text = se.easy_xml.EasyXmlElement(child).inner_text()

					if (figcaption_text != "" and loi_text != "" and figcaption_text != loi_text) and (figure_img_alt != "" and loi_text != "" and figure_img_alt != loi_text):
						messages.append(LintMessage("s-041", f"The [xhtml]<figcaption>[/] element of [attr]#{figure_ref}[/] does not match the text in its LoI entry.", se.MESSAGE_TYPE_WARNING, self.path / "src/epub/text" / chapter_ref))

				# Check for missing MARC relators
				# Don't check the landmarks as that may introduce duplicate errors
				# Only check for top-level elements, to avoid intros in short stories or poems in compilation.
				if not dom.xpath("/html/body//nav[contains(@epub:type, 'landmarks')]"):
					if dom.xpath("/html/body/*[contains(@epub:type, 'introduction')]") and not self.metadata_dom.xpath("/package/metadata/meta[@property='role' and (text() = 'aui' or text() = 'win')]"):
						messages.append(LintMessage("m-030", "[val]introduction[/] semantic inflection found, but no MARC relator [val]aui[/] (Author of introduction, but not the chief author) or [val]win[/] (Writer of introduction).", se.MESSAGE_TYPE_WARNING, filename))

					if dom.xpath("/html/body/*[contains(@epub:type, 'preface')]") and not self.metadata_dom.xpath("/package/metadata/meta[@property='role' and text() = 'wpr']"):
						messages.append(LintMessage("m-031", "[val]preface[/] semantic inflection found, but no MARC relator [val]wpr[/] (Writer of preface).", se.MESSAGE_TYPE_WARNING, filename))

					if dom.xpath("/html/body/*[contains(@epub:type, 'afterword')]") and not self.metadata_dom.xpath("/package/metadata/meta[@property='role' and text() = 'aft']"):
						messages.append(LintMessage("m-032", "[val]afterword[/] semantic inflection found, but no MARC relator [val]aft[/] (Author of colophon, afterword, etc.).", se.MESSAGE_TYPE_WARNING, filename))

					if dom.xpath("/html/body/*[contains(@epub:type, 'endnotes')]") and not self.metadata_dom.xpath("/package/metadata/meta[@property='role' and text() = 'ann']"):
						messages.append(LintMessage("m-033", "[val]endnotes[/] semantic inflection found, but no MARC relator [val]ann[/] (Annotator).", se.MESSAGE_TYPE_WARNING, filename))

					if dom.xpath("/html/body/*[contains(@epub:type, 'loi')]") and not self.metadata_dom.xpath("/package/metadata/meta[@property='role' and text() = 'ill']"):
						messages.append(LintMessage("m-034", "[val]loi[/] semantic inflection found, but no MARC relator [val]ill[/] (Illustrator).", se.MESSAGE_TYPE_WARNING, filename))

			# Check for wrong semantics in frontmatter/backmatter
			if filename.name in FRONTMATTER_FILENAMES and not dom.xpath("//*[contains(@epub:type, 'frontmatter')]"):
				messages.append(LintMessage("s-036", "No [val]frontmatter[/] semantic inflection for what looks like a frontmatter file.", se.MESSAGE_TYPE_WARNING, filename))

			if filename.name in BACKMATTER_FILENAMES and not dom.xpath("//*[contains(@epub:type, 'backmatter')]"):
				messages.append(LintMessage("s-037", "No [val]backmatter[/] semantic inflection for what looks like a backmatter file.", se.MESSAGE_TYPE_WARNING, filename))

	if cover_svg_title != titlepage_svg_title:
		messages.append(LintMessage("s-028", f"[path][link=file://{self.path / 'images/cover.svg'}]cover.svg[/][/] and [path][link=file://{self.path / 'images/titlepage.svg'}]titlepage.svg[/][/] [xhtml]<title>[/] elements don’t match.", se.MESSAGE_TYPE_ERROR, self.path / "images/cover.svg"))

	if has_frontmatter and not has_halftitle:
		messages.append(LintMessage("s-020", "Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	if not has_cover_source:
		missing_files.append(self.path / "images/cover.source.jpg")

	missing_selectors = []
	single_use_css_classes = []

	for css_class in xhtml_css_classes:
		if css_class not in IGNORED_CLASSES:
			if f".{css_class}" not in self.local_css:
				missing_selectors.append(css_class)

		if xhtml_css_classes[css_class] == 1 and css_class not in IGNORED_CLASSES and not regex.match(r"^i[0-9]+$", css_class):
			# Don't count ignored classes OR i[0-9] which are used for poetry styling
			single_use_css_classes.append(css_class)

	if missing_selectors:
		messages.append(LintMessage("x-013", f"CSS class found in XHTML, but not in [path][link=file://{local_css_path}]local.css[/][/].", se.MESSAGE_TYPE_ERROR, local_css_path, missing_selectors))

	if single_use_css_classes:
		messages.append(LintMessage("c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks.", se.MESSAGE_TYPE_WARNING, local_css_path, single_use_css_classes))

	if files_not_url_safe:
		try:
			files_not_url_safe = self.repo.git.ls_files([str(f.relative_to(self.path)) for f in files_not_url_safe]).split("\n")
			if files_not_url_safe and files_not_url_safe[0] == "":
				files_not_url_safe = []
		except:
			# If we can't initialize Git, then just pass through the list of illegal files
			pass

		for filepath in files_not_url_safe:
			filepath = Path(filepath)
			url_safe_filename = se.formatting.make_url_safe(filepath.stem) + filepath.suffix
			messages.append(LintMessage("f-008", f"Filename is not URL-safe. Expected: [path]{url_safe_filename}[/].", se.MESSAGE_TYPE_ERROR, filepath))

	if directories_not_url_safe:
		try:
			directories_not_url_safe = self.repo.git.ls_files([str(f.relative_to(self.path)) for f in directories_not_url_safe]).split("\n")

			if directories_not_url_safe and directories_not_url_safe[0] == "":
				directories_not_url_safe = []

			# Git doesn't story directories, only files. So the above output will be a list of files within a badly-named dir.
			# To get the dir name, get the parent of the file that Git outputs.
			for index, filepath in enumerate(directories_not_url_safe):
				directories_not_url_safe[index] = str(Path(filepath).parent.name)

			# Remove duplicates
			directories_not_url_safe = list(set(directories_not_url_safe))
		except:
			# If we can't initialize Git, then just pass through the list of illegal files
			pass

		for filepath in directories_not_url_safe:
			filepath = Path(filepath)
			url_safe_filename = se.formatting.make_url_safe(filepath.stem)
			messages.append(LintMessage("f-008", f"Filename is not URL-safe. Expected: [path]{url_safe_filename}[/].", se.MESSAGE_TYPE_ERROR, filepath))

	# Check our headings against the ToC and landmarks
	headings = list(set(headings))
	toc_dom = _dom(self.path / "src/epub/toc.xhtml")
	toc_headings = []
	toc_files = []
	toc_entries = toc_dom.xpath("/html/body/nav[@epub:type='toc']//a")

	# Match ToC headings against text headings
	for node in toc_entries:
		# Remove # anchors after filenames (for books like Aesop's fables)
		entry_file = self.path / "src/epub" / regex.sub(r"#.+$", "", node.get_attr("href"))
		toc_headings.append((node.inner_text(), str(entry_file)))

	for heading in headings:
		# Some compliations, like Songs of a Sourdough, have their title in the half title, so check against that before adding an error
		if heading not in toc_headings and (heading[0], str(self.path / "src/epub/text/halftitle.xhtml")) not in toc_headings:
			messages.append(LintMessage("m-045", f"Heading [text]{heading[0]}[/] found, but not present for that file in the ToC.", se.MESSAGE_TYPE_ERROR, Path(heading[1])))

	# Check our ordered ToC entries against the spine
	# To cover all possibilities, we combine the toc and the landmarks to get the full set of entries
	for node in toc_dom.xpath("/html/body/nav[@epub:type='landmarks']//a[re:test(@epub:type, '(front|body)matter')]"):
		toc_files.append(regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", node.get_attr("href")))
	for node in toc_entries:
		toc_files.append(regex.sub(r"^text\/(.*?\.xhtml).*$", r"\1", node.get_attr("href")))

	if duplicate_id_values:
		duplicate_id_values = natsorted(list(set(duplicate_id_values)))
		messages.append(LintMessage("x-017", "Duplicate value for [attr]id[/] attribute. [attr]id[/] attribute values must be unique across the entire ebook on all non-sectioning elements.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, duplicate_id_values))

	# We can't convert to set() to get unique items because set() is unordered
	unique_toc_files: List[str] = []
	for toc_file in toc_files:
		if toc_file not in unique_toc_files:
			unique_toc_files.append(toc_file)
	toc_files = unique_toc_files

	spine_entries = self.metadata_dom.xpath("/package/spine/itemref")
	if len(toc_files) != len(spine_entries):
		messages.append(LintMessage("m-043", f"The number of elements in the spine ({len(spine_entries)}) does not match the number of elements in the ToC and landmarks ({len(toc_files)}).", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
	for index, node in enumerate(spine_entries):
		if toc_files[index] != node.get_attr("idref"):
			messages.append(LintMessage("m-044", f"The spine order does not match the order of the ToC and landmarks. Expected [text]{node.get_attr('idref')}[/], found [text]{toc_files[index]}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
			break

	for element in abbr_elements:
		abbr_class = element.get_attr("class").replace(" eoc", "").strip()
		if f"abbr.{abbr_class}" not in abbr_styles:
			missing_styles.append(element.to_tag_string())

	if missing_styles:
		messages.append(LintMessage("c-006", f"Semantic found, but missing corresponding style in [path][link=file://{local_css_path}]local.css[/][/].", se.MESSAGE_TYPE_ERROR, local_css_path, set(missing_styles)))

	for double_spaced_file in double_spaced_files:
		messages.append(LintMessage("t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)", se.MESSAGE_TYPE_ERROR, double_spaced_file))

	for missing_file in missing_files:
		messages.append(LintMessage("f-002", "Missing expected file or directory.", se.MESSAGE_TYPE_ERROR, missing_file))

	if unused_selectors:
		messages.append(LintMessage("c-002", "Unused CSS selectors.", se.MESSAGE_TYPE_ERROR, local_css_path, unused_selectors))

	# Now that we have our lint messages, we filter out ones that we've ignored.
	if ignored_codes:
		# Iterate over a copy of messages, so that we can remove from them while iterating.
		for message in messages[:]:
			for path, codes in ignored_codes.items():
				for code in codes:
					try:
						# fnmatch.translate() converts shell-style globs into a regex pattern
						if regex.match(fr"{translate(path)}", str(message.filename.name) if message.filename else "") and message.code == code["code"]:
							messages.remove(message)
							code["used"] = True

					except ValueError as ex:
						# This gets raised if the message has already been removed by a previous rule.
						# For example, chapter-*.xhtml gets t-001 removed, then subsequently *.xhtml gets t-001 removed.
						pass
					except Exception as ex:
						raise se.InvalidInputException(f"Invalid path in [path][link=file://{lint_ignore_path}]se-lint-ignore.xml[/][/] rule: [path]{path}[/].")

		# Check for unused ignore rules
		unused_codes: List[str] = []
		for path, codes in ignored_codes.items():
			for code in codes:
				if not code["used"]:
					unused_codes.append(f"{path}, {code['code']}")

		if unused_codes:
			messages.append(LintMessage("m-048", f"Unused [path][link=file://{lint_ignore_path}]se-lint-ignore.xml[/][/] rule.", se.MESSAGE_TYPE_ERROR, lint_ignore_path, unused_codes))

	messages = natsorted(messages, key=lambda x: ((str(x.filename.name) if x.filename else "") + " " + x.code), alg=ns.PATH)

	return messages
