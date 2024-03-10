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
from typing import Dict, List, Set, Union, Optional
import importlib_resources

import cssutils
import lxml.cssselect
from lxml import etree
from PIL import Image, UnidentifiedImageError
import regex
from natsort import natsorted, ns

import se
import se.easy_xml
import se.formatting
import se.images
import se.typography

SE_VARIABLES = [
	"SE_IDENTIFIER",
	"TITLE",
	"TITLE_SORT",
	"SUBJECT_1",
	"SUBJECT_2",
	"LCSH_ID_1",
	"LCSH_ID_2",
	"TAG",
	"DESCRIPTION",
	"LONG_DESCRIPTION",
	"LANG",
	"PG_URL",
	"IA_URL",
	"PRODUCTION_NOTES",
	"EBOOK_WIKI_URL",
	"VCS_IDENTIFIER",
	"AUTHOR",
	"AUTHOR_SORT",
	"AUTHOR_FULL_NAME",
	"AUTHOR_WIKI_URL",
	"AUTHOR_NACOAF_URI",
	"TRANSLATOR",
	"TRANSLATOR_SORT",
	"TRANSLATOR_WIKI_URL",
	"TRANSLATOR_NACOAF_URI",
	"COVER_ARTIST",
	"COVER_ARTIST_SORT",
	"COVER_ARTIST_WIKI_URL",
	"COVER_ARTIST_NACOAF_URI",
	"ILLUSTRATOR",
	"ILLUSTRATOR_SORT",
	"ILLUSTRATOR_WIKI_URL",
	"ILLUSTRATOR_NACOAF_URI",
	"TRANSCRIBER",
	"TRANSCRIBER_SORT",
	"TRANSCRIBER_URL",
	"PRODUCER",
	"PRODUCER_URL",
	"PRODUCER_SORT",
	"CONTRIBUTOR_ID",
	"CONTRIBUTOR_NAME",
	"CONTRIBUTOR_SORT",
	"CONTRIBUTOR_FULL_NAME",
	"CONTRIBUTOR_WIKI_URL",
	"CONTRIBUTOR_NACOAF_URI",
	"CONTRIBUTOR_MARC",
	# colophon-specific
	"YEAR",
	"ORIGINAL_LANGUAGE",
	"TRANSLATION_YEAR",
	"PG_YEAR",
	"TRANSCRIBER_1",
	"TRANSCRIBER_2",
	"PAINTING"
]

# See https://idpf.github.io/epub-vocabs/structure/
EPUB_SEMANTIC_VOCABULARY = ["abstract", "acknowledgments", "afterword", "answer", "answers", "appendix", "aside", "assessment", "assessments", "backlink", "backmatter", "balloon", "biblioentry", "bibliography", "biblioref", "bodymatter", "bridgehead", "case-study", "chapter", "colophon", "concluding-sentence", "conclusion", "contributors", "copyright-page", "cover", "covertitle", "credit", "credits", "dedication", "division", "endnote", "endnotes", "epigraph", "epilogue", "errata", "feedback", "figure", "fill-in-the-blank-problem", "footnote", "footnotes", "foreword", "frontmatter", "fulltitle", "general-problem", "glossary", "glossdef", "glossref", "glossterm", "halftitle", "halftitlepage", "imprimatur", "imprint", "index", "index-editor-note", "index-entry", "index-entry-list", "index-group", "index-headnotes", "index-legend", "index-locator", "index-locator-list", "index-locator-range", "index-term", "index-term-categories", "index-term-category", "index-xref-preferred", "index-xref-related", "introduction", "keyword", "keywords", "label", "landmarks", "learning-objective", "learning-objectives", "learning-outcome", "learning-outcomes", "learning-resource", "learning-resources", "learning-standard", "learning-standards", "list", "list-item", "loa", "loi", "lot", "lov", "match-problem", "multiple-choice-problem", "noteref", "notice", "ordinal", "other-credits", "pagebreak", "page-list", "panel", "panel-group", "part", "practice", "practices", "preamble", "preface", "prologue", "pullquote", "qna", "question", "revision-history", "seriespage", "sound-area", "subtitle", "table", "table-cell", "table-row", "text-area", "tip", "title", "titlepage", "toc", "toc-brief", "topic-sentence", "true-false-problem", "volume"]

# See https://www.daisy.org/z3998/2012/vocab/structure/
Z3998_SEMANTIC_VOCABULARY = ["abbreviations", "acknowledgments", "acronym", "actor", "afterword", "alteration", "annoref", "annotation", "appendix", "article", "aside", "attribution", "author", "award", "backmatter", "bcc", "bibliography", "biographical-note", "bodymatter", "cardinal", "catalogue", "cc", "chapter", "citation", "clarification", "collection", "colophon", "commentary", "commentator", "compound", "concluding-sentence", "conclusion", "continuation", "continuation-of", "contributors", "coordinate", "correction", "covertitle", "currency", "decimal", "decorative", "dedication", "diary", "diary-entry", "discography", "division", "drama", "dramatis-personae", "editor", "editorial-note", "email", "email-message", "epigraph", "epilogue", "errata", "essay", "event", "example", "family-name", "fiction", "figure", "filmography", "footnote", "footnotes", "foreword", "fraction", "from", "frontispiece", "frontmatter", "ftp", "fulltitle", "gallery", "general-editor", "geographic", "given-name", "glossary", "grant-acknowledgment", "grapheme", "halftitle", "halftitle-page", "help", "homograph", "http", "hymn", "illustration", "image-placeholder", "imprimatur", "imprint", "index", "initialism", "introduction", "introductory-note", "ip", "isbn", "keyword", "letter", "loi", "lot", "lyrics", "marginalia", "measure", "mixed", "morpheme", "name-title", "nationality", "non-fiction", "nonresolving-citation", "nonresolving-reference", "note", "noteref", "notice", "orderedlist", "ordinal", "organization", "other-credits", "pagebreak", "page-footer", "page-header", "part", "percentage", "persona", "personal-name", "pgroup", "phone", "phoneme", "photograph", "phrase", "place", "plate", "poem", "portmanteau", "postal", "postal-code", "postscript", "practice", "preamble", "preface", "prefix", "presentation", "primary", "product", "production", "prologue", "promotional-copy", "published-works", "publisher-address", "publisher-note", "publisher-logo", "range", "ratio", "rearnote", "rearnotes", "recipient", "recto", "reference", "republisher", "resolving-reference", "result", "role-description", "roman", "root", "salutation", "scene", "secondary", "section", "sender", "sentence", "sidebar", "signature", "song", "speech", "stage-direction", "stem", "structure", "subchapter", "subject", "subsection", "subtitle", "suffix", "surname", "taxonomy", "tertiary", "text", "textbook", "t-form", "timeline", "title", "title-page", "to", "toc", "topic-sentence", "translator", "translator-note", "truncation", "unorderedlist", "valediction", "verse", "verso", "v-form", "volume", "warning", "weight", "word"]

# See https://standardebooks.org/vocab/1.0
SE_SEMANTIC_VOCABULARY = ["collection", "compass", "compound", "diary", "diary.dateline", "era", "image", "image.color-depth", "image.color-depth.black-on-transparent", "image.style.realistic", "image.color-depth.default-on-transparent", "letter", "letter.dateline", "long-description", "name", "name.person", "name.person.full-name", "name.person.pen-name", "name.vehicle", "name.vehicle.airplane", "name.vehicle.auto", "name.vehicle.train", "name.vessel", "name.vessel.boat", "name.vessel.ship", "name.publication", "name.publication.book", "name.publication.essay", "name.publication.journal", "name.publication.newspaper", "name.publication.magazine", "name.publication.pamphlet", "name.publication.paper", "name.publication.play", "name.publication.poem", "name.publication.short-story", "name.music", "name.music.opera", "name.music.song", "name.visual-art", "name.visual-art.engraving", "name.visual-art.film", "name.visual-art.illustration", "name.visual-art.painting", "name.visual-art.photograph", "name.visual-art.sculpture", "name.visual-art.typeface", "name.broadcast", "name.broadcast.television-show", "name.legal-case", "novel", "novella", "publication-notes", "reading-ease", "reading-ease.flesch", "short-story", "sic", "temperature", "transform", "url", "url.authority", "url.authority.nacoaf", "url.homepage", "url.encyclopedia", "url.encyclopedia.wikipedia", "url.vcs", "url.vcs.github", "word-count"]

SE_GENRES = ["Adventure", "Autobiography", "Biography", "Children’s", "Comedy", "Drama", "Fantasy", "Fiction", "Horror", "Memoir", "Mystery", "Nonfiction", "Philosophy", "Poetry", "Satire", "Science Fiction", "Shorts", "Spirituality", "Tragedy", "Travel"]
IGNORED_CLASSES = ["elision", "eoc", "full-page", "continued", "together"]
BINARY_EXTENSIONS = [".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".png", ".epub", ".xcf", ".otf", ".jp2"]
IGNORED_FILENAMES = ["colophon.xhtml", "titlepage.xhtml", "imprint.xhtml", "uncopyright.xhtml", "toc.xhtml", "loi.xhtml"]
SPECIAL_FILES = ["colophon", "endnotes", "imprint", "loi"]

# These are partly defined in semos://1.0.0/8.10.9.2
INITIALISM_EXCEPTIONS = ["G", # as in `G-Force`
			"1D", "2D", "3D", "4D", # as in `n-dimensional`
			"MS.", "MSS.", # Manuscript(s)
			"MM.",	# Messiuers
			"κ.τ.λ.", # "etc." in Greek, and we don't match Greek chars.
			"TV",
			"AC", "DC" # electrical current
]

"""
POSSIBLE BBCODE TAGS
See the se.print_error function for a comprehensive list of allowed codes.

LIST OF ALL SE LINT MESSAGES

CSS
"c-001", "Don’t use [css]*:first-of-type[/], [css]*:last-of-type[/], [css]*:nth-of-type[/] [css]*:nth-last-of-type[/], or [css]*:only-of-type[/] on [css]*[/]. Instead, specify an element to apply it to."
"c-002", "Unused CSS selectors."
"c-003", "[css]\\[xml|attr][/] selector in CSS, but no XML namespace declared ([css]@namespace xml \"http://www.w3.org/XML/1998/namespace\";[/])."
"c-004", "Don’t specify border colors, so that reading systems can adjust for night mode."
"c-005", f"[css]abbr[/] selector does not need [css]white-space: nowrap;[/] as it inherits it from [path][link=file://{self.path / 'src/epub/css/core.css'}]core.css[/][/]."
"c-006", f"Semantic found, but missing corresponding style in [path][link=file://{local_css_path}]local.css[/][/]."
"c-007", "[css]hyphens[/css] CSS property without [css]-epub-hyphens[/css] copy."
"c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks."
"c-009", "Duplicate CSS selectors. Duplicates are only acceptable if overriding S.E. base styles."
"c-010", "[xhtml]<footer>[/] missing [css]margin-top: 1em; text-align: <value>;[/]. [css]text-align[/] is usually set to [css]right[/]."
"c-011", "Element with [css]text-align: center;[/] but [css]text-indent[/] is [css]1em[/]."
"c-012", "Sectioning element without heading content, and without [css]margin-top: 20vh;[/]."
"c-013", "Element with margin or padding not in increments of [css].5em[/]."
"c-014", "[xhtml]<table>[/] element without explicit margins. Most tables need [css]margin: 1em;[/] or [css]margin: 1em auto 1em auto;[/]."
"c-015", "Element after or containing [val]z3998:salutation[/] does not have [css]text-indent: 0;[/]."
"c-016", "[css]text-align: left;[/] found. Use [css]text-align: initial;[/] instead."
"c-017", "Element with [val]z3998:postscript[/] semantic, but without [css]margin-top: 1em;[/]."
"c-018", "Element with [val]z3998:postscript[/] semantic, but without [css]text-indent: 0;[/]."
"c-019", "Element with [val]z3998:signature[/] semantic, but without [css]font-variant: small-caps;[/] or [css]font-style: italic;[/]."
"c-020", "Multiple [xhtml]<article>[/]s or [xhtml]<section>[/]s in file, but missing [css]break-after: page;[/]."
"c-021", "Element with [css]font-style: italic;[/], but child [xhtml]<i>[/] or [xhtml]<em>[/] does not have [css]font-style: normal;[/]. Hint: Italics within italics are typically set in Roman for contrast; if that’s not the case here, can [xhtml]<i>[/] be removed while still preserving italics and semantic inflection?"
"c-022", "Illegal [css]rem[/] unit. Use [css]em[/] instead."
"c-023", "Illegal unit used to set [css]font-size[/]. Hint: Use [css]em[/] units."
"c-024", "Illegal unit used to set [css]line-height[/]. Hint: [css]line-height[/] is set without any units."
"c-025", "Illegal percent unit used to set [css]height[/] or positioning property. Hint: [css]vh[/] to specify vertical-oriented properties like height or position."
"c-026", "Table that appears to be listing numbers, but without [css]font-variant-numeric: tabular-nums;[/]."

FILESYSTEM
"f-001", "Illegal file or directory."
"f-002", "Missing expected file or directory."
"f-003", f"File does not match [path][link=file://{license_file_path}]{license_file_path}[/][/]."
"f-004", f"File does not match [path][link=file://{core_css_file_path}]{core_css_file_path}[/][/]."
"f-005", f"File does not match [path][link=file://{logo_svg_file_path}]{logo_svg_file_path}[/][/]."
"f-006", f"File does not match [path][link=file://{uncopyright_file_path}]{uncopyright_file_path}[/][/]."
"f-007", "File not listed in [xml]<spine>[/]."
"f-008", f"Filename is not URL-safe. Expected: [path]{url_safe_filename}[/]."
"f-009", "Illegal leading [text]0[/] in filename."
"f-010", "Problem decoding file as utf-8."
"f-011", "JPEG files must end in [path].jpg[/]."
"f-012", "TIFF files must end in [path].tif[/]."
"f-013", "Glossary search key map must be named [path]glossary-search-key-map.xml[/]."
"f-014", f"File does not match [path][link=file://{self.path / 'src/epub/css/se.css'}]{core_css_file_path}[/][/]."
"f-015", "Filename doesn’t match [attr]id[/] attribute of primary [xhtml]<section>[/] or [xhtml]<article>[/]. Hint: [attr]id[/] attributes don’t include the file extension."
"f-016", "Image more than 1.5MB in size."
"f-017", f"[path][link=file://{self.path / 'images/cover.jpg'}]cover.jpg[/][/] must be exactly {se.COVER_WIDTH} × {se.COVER_HEIGHT}."
"f-018", "Image greater than 4,000,000 pixels square in dimension."
"f-019", "[path].png[/] file without transparency. Hint: If an image doesn’t have transparency, it should be saved as a [path].jpg[/]."

METADATA
"m-001", "gutenberg.org URL missing leading [text]www.[/]."
"m-002", "archive.org URL should not have leading [text]www.[/]."
"m-003", "Non-HTTPS URL."
"m-004", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://books.google.com/books?id=<BOOK-ID>[/]."
"m-005", "Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like [url]https://catalog.hathitrust.org/Record/<BOOK-ID>[/]."
"m-006", "Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like [url]https://www.gutenberg.org/ebooks/<BOOK-ID>[/]."
"m-007", "Non-canonical archive.org URL. Internet Archive URLs must look exactly like [url]https://archive.org/details/<BOOK-ID>[/]."
"m-008", "[url]id.loc.gov[/] URI ending with illegal [path].html[/]."
"m-009", f"[xml]<meta property=\"se:url.vcs.github\">[/] value does not match expected: [url]{self.generated_github_repo_url}[/]."
"m-010", "Invalid [xml]refines[/] property."
"m-011", "Subtitle in metadata, but no full/extended title element."
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
"m-026", f"Illegal [url]https://*.m.wikipedia.org[/] URL. Hint: use non-mobile Wikipedia URLs."
"m-027", f"[val]se:short-story[/] semantic inflection found, but no [val]se:subject[/] with the value of [text]Shorts[/]."
"m-028", "Images found in ebook, but no [attr]schema:accessMode[/] property set to [val]visual[/] in metadata."
"m-029", "Images found in ebook, but no [attr]schema:accessibilityFeature[/] property set to [val]alternativeText[/] in metadata."
"m-030", f"[val]introduction[/] semantic inflection found, but no MARC relator [val]aui[/] (Author of introduction, but not the chief author) or [val]win[/] (Writer of introduction)."
"m-031", f"[val]preface[/] semantic inflection found, but no MARC relator [val]wpr[/] (Writer of preface)."
"m-032", f"[val]afterword[/] semantic inflection found, but no MARC relator [val]aft[/] (Author of colophon, afterword, etc.)."
"m-033", f"[val]endnotes[/] semantic inflection found, but no MARC relator [val]ann[/] (Annotator)."
"m-034", f"[val]loi[/] semantic inflection found, but no MARC relator [val]ill[/] (Illustrator)."
"m-035", f"Unexpected S.E. identifier in colophon. Expected: [url]{se_url}[/]."
"m-036", "Variable not replaced with value."
"m-037", f"Transcription/page scan source link not found. Expected: [xhtml]{href}[/]."
"m-038", "[attr]schema:accessMode[/] property set to [val]visual[/] in metadata, but no images in ebook."
"m-039", "[attr]schema:accessibilityFeature[/] property set to [val]alternativeText[/] in metadata, but no images in ebook."
"m-040", "Images found in ebook, but no [attr]role[/] property set to [val]wat[/] in metadata for the writer of the alt text."
"m-041", "Hathi Trust link text must be exactly [text]HathiTrust Digital Library[/]."
"m-042", "[xml]<manifest>[/] element does not match expected structure."
"m-043", f"Non-English Wikipedia URL."
"m-044", f"Possessive [text]’[/] or [text]’s[/] outside of [xhtml]<a>[/] element in long description."
"m-045", f"Heading [text]{heading[0]}[/] found, but not present for that file in the ToC."
"m-046", "Missing or empty [xml]<reason>[/] element."
"m-047", "Ignoring [path]*[/] is too general. Target specific files if possible."
"m-048", f"Unused [path][link=file://{lint_ignore_path}]se-lint-ignore.xml[/][/] rule."
"m-049", "No [path]se-lint-ignore.xml[/] rules. Delete the file if there are no rules."
"m-050", "Non-typogrified character in [xml]<meta property=\"file-as\" refines=\"#title\">[/] element."
"m-051", "Missing expected element in metadata."
"m-052", "[xml]<dc:title>[/] element contains numbers, but no [xml]<meta property=\"dcterms:alternate\" refines="#title"> element in metadata."
"m-053", "[xml]<meta property=\"se:subject\">[/] elements not in alphabetical order."
"m-054", "Standard Ebooks URL with illegal trailing slash."
"m-055", "[xml]dc:description[/] does not end with a period."
"m-056", "Author name present in [xml]<meta property=\"se:long-description\">[/] element, but the first instance of their name is not hyperlinked to their S.E. author page."
"m-057", "[xml]xml:lang[/] attribute in [xml]<meta property=\"se:long-description\">[/] element should be [xml]lang[/]."
"m-058", "[val]se:subject[/] of [text]{implied_tag}[/] found, but [text]{tag}[/] implies [text]{implied_tag}[/]."
"m-059", f"Link to [url]{node.get_attr('href')}[/] found in colophon, but missing matching [xhtml]dc:source[/] element in metadata."
"m-060", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://www.google.com/books/edition/<BOOK-NAME>/<BOOK-ID>[/]."
"m-061", "Link must be preceded by [text]the[/]."
"m-063", "Cover image has not been built."
"m-062", "[xml]<dc:title>[/] missing matching [xml]<meta property=\"file-as\">[/]."
"m-064", "S.E. ebook hyperlinked in long description but not italicized."
"m-065", "Word count in metadata doesn’t match actual word count."
"m-066", "[url]id.loc.gov[/] URI starting with illegal https."
"m-067", "Non-S.E. link in long description."
"m-068", "[xml]<dc:title>[/] missing matching [xml]<meta property=\"title-type\">[/]."
"m-069", "[text]comprised of[/] in metadata. Hint: Is there a better phrase to use here?"
"m-070", "Glossary entries not present in the text:"
"m-071", "DP link must be exactly [text]The Online Distributed Proofreading Team[/]."
"m-072", "DP OLS link must be exactly [text]Distributed Proofreaders Open Library System[/]."
"m-073", "Anonymous contributor values must be exactly [text]Anonymous[/]."
"m-074", "Multiple transcriptions found in metadata, but no link to [text]EBOOK_URL#transcriptions[/]."
"m-075", "Multiple page scans found in metadata, but no link to [text]EBOOK_URL#page-scans[/]."
"m-076", "gutenberg.net.au URL should not have leading [text]www.[/]."
"m-077", "MathML found in ebook, but no [attr]schema:accessibilityFeature[/] properties set to [val]MathML[/] and [val]describedMath[/] in metadata."

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
"s-018", "[xhtml]<img>[/] element with [attr]id[/] attribute. [attr]id[/] attributes go on parent [xhtml]<figure>[/] elements. Hint: Images that are inline (i.e. that do not have parent [xhtml]<figure>[/]s do not have [attr]id[/] attributes."
"s-019", "[xhtml]<h#>[/] element with [attr]id[/] attribute. [xhtml]<h#>[/] elements should be wrapped in [xhtml]<section>[/] elements, which should hold the [attr]id[/] attribute."
"s-020", "Frontmatter found, but no half title page. Half title page is required when frontmatter is present."
"s-021", f"Unexpected value for [xhtml]<title>[/] element. Expected: [text]{title}[/]. (Beware hidden Unicode characters!)"
"s-022", f"The [xhtml]<title>[/] element of [path][link=file://{svg_path}]{image_ref}[/][/] does not match the [attr]alt[/] attribute text in [path][link=file://{filename}]{filename.name}[/][/]."
"s-023", f"Title [text]{title}[/] not correctly titlecased. Expected: [text]{titlecased_title}[/]."
"s-024", "Header elements that are entirely non-English should not be set in italics. Instead, the [xhtml]<h#>[/] element has the [attr]xml:lang[/] attribute."
"s-025", "Titlepage [xhtml]<title>[/] elements must contain exactly: [text]Titlepage[/]."
"s-026", "Invalid Roman numeral."
"s-027", f"{image_ref} missing [xhtml]<title>[/] element."
"s-028", f"[path][link=file://{self.path / 'images/cover.svg'}]cover.svg[/][/] and [path][link=file://{self.path / 'images/titlepage.svg'}]titlepage.svg[/][/] [xhtml]<title>[/] elements don’t match."
"s-029", "Section with [attr]data-parent[/] attribute, but no section having that [attr]id[/] in ebook."
"s-030", "[val]z3998:nonfiction[/] should be [val]z3998:non-fiction[/]."
"s-031", "Duplicate value in [attr]epub:type[/] attribute."
"s-032", "Invalid value for [attr]epub:type[/] attribute."
"s-033", f"File language is [val]{file_language}[/], but [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/] language is [val]{language}[/]."
"s-034", "Semantic used from the z3998 vocabulary, but the same semantic exists in the EPUB vocabulary."
"s-035", "Endnote containing only [xhtml]<cite>[/]."
"s-036", "No [val]frontmatter[/] semantic inflection for what looks like a frontmatter file."
"s-037", "No [val]backmatter[/] semantic inflection for what looks like a backmatter file."
"s-038", "Illegal asterism. Section/scene breaks must be defined by an [xhtml]<hr/>[/] element."
"s-039", "[text]Ibid[/] in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes"
"s-040", f"[attr]#{figure_ref}[/] not found in file [path][link=file://{self.path / 'src/epub/text' / chapter_ref}]{chapter_ref}[/][/]."
"s-041", f"The [xhtml]<figcaption>[/] element of [attr]#{figure_ref}[/] does not match the text in its LoI entry."
"s-042", "[xhtml]<table>[/] element without [xhtml]<tbody>[/] child."
"s-043", "[val]se:short-story[/] semantic on element that is not [xhtml]<article>[/]."
"s-044", "Element with poem or verse semantic, without descendant [xhtml]<p>[/] (stanza) element."
"s-045", "[xhtml]<abbr>[/] element without semantic inflection like [class]z3998:personal-name[/] or [class]z3998:initialism[/]."
"s-046", "[xhtml]<p>[/] element containing only [xhtml]<span>[/] and [xhtml]<br>[/] elements, but its parent doesn’t have the [val]z3998:poem[/], [val]z3998:verse[/], [val]z3998:song[/], [val]z3998:hymn[/], or [val]z3998:lyrics[/] semantic. Multi-line clauses that are not verse don’t require [xhtml]<span>[/]s."
"s-047", "[val]noteref[/] as a direct child of element with poem or verse semantic. [val]noteref[/]s should be in their parent [xhtml]<span>[/]."
"s-048", "[val]se:name[/] semantic on block element. [val]se:name[/] indicates the contents is the name of something."
"s-049", "[xhtml]<header>[/] element whose only child is an [xhtml]<h#>[/] element."
"s-050", "[xhtml]<span>[/] element appears to exist only to apply [attr]epub:type[/]. [attr]epub:type[/] should go on the parent element instead, without a [xhtml]<span>[/] element."
"s-051", "Element with [xhtml]xml:lang=\"unk\"[/] should be [xhtml]xml:lang=\"und\"[/] (undefined)."
"s-052", "[xhtml]<abbr>[/] element with illegal [attr]title[/] attribute."
"s-053", "Colophon line not preceded by [xhtml]<br/>[/]."
"s-054", "[xhtml]<cite>[/] as child of [xhtml]<p>[/] in [xhtml]<blockquote>[/]. [xhtml]<cite>[/] should be the direct child of [xhtml]<blockquote>[/]."
"s-055", "[xhtml]<th>[/] element not in [xhtml]<thead>[/] ancestor. Note: [xhtml]<th>[/] elements used as mid-table headings or horizontal row headings require the [attr]scope[/] attribute."
"s-056", "Last [xhtml]<p>[/] child of endnote missing backlink."
"s-057", "Backlink noteref fragment identifier doesn’t match endnote number."
"s-058", "[attr]z3998:stage-direction[/] semantic only allowed on [xhtml]<i>[/], [xhtml]<abbr>[/], and [xhtml]<p>[/] elements."
"s-059", "Internal link beginning with [val]../text/[/]."
"s-060", "Italics on name that requires quotes instead."
"s-061", "Title and following header content not in a [xhtml]<header>[/] element."
"s-062", "[xhtml]<dt>[/] element in a glossary without exactly one [xhtml]<dfn>[/] child."
"s-063", "[val]z3998:persona[/] semantic on element that is not a [xhtml]<b>[/] or [xhtml]<td>[/]."
"s-064", "Endnote citation not wrapped in [xhtml]<cite>[/]. Em dashes go within [xhtml]<cite>[/] and it is preceded by one space."
"s-065", "[val]fulltitle[/] semantic on element that is not in the half title."
"s-066", "Header element missing [val]label[/] semantic."
"s-067", "Header element with a [val]label[/] semantic child, but without an [val]ordinal[/] semantic child."
"s-068", "Header element missing [val]ordinal[/] semantic."
"s-069", "[xhtml]<body>[/] element missing direct child [xhtml]<section>[/] or [xhtml]<article>[/] element."
"s-070", "[xhtml]<h#>[/] element without semantic inflection."
"s-071", "Sectioning element with more than one heading element."
"s-072", "Element with single [xhtml]<span>[/] child. [xhtml]<span>[/] should be removed and its attributes promoted to the parent element."
"s-073", "Header element that requires [val]label[/] and [val]ordinal[/] semantic children."
"s-074", "[xhtml]<th>[/] element with no text content should be a [xhtml]<td>[/] element instead."
"s-075", "[xhtml]<body>[/] element with direct children that are not [xhtml]<section>[/], [xhtml]<article>[/], or [xhtml]<nav>[/]."
"s-076", "[attr]lang[/] attribute used instead of [attr]xml:lang[/]."
"s-077", "[xhtml]<header>[/] element preceded by non-sectioning element."
"s-078", "[xhtml]<footer>[/] element followed by non-sectioning element."
"s-079", "Element containing only white space."
"s-080", "[xhtml]<td>[/] in drama containing both inline text and a block-level element. All children should either be only text, or only block-level elements."
"s-081", "[xhtml]<p>[/] preceded by [xhtml]<figure>[/], [xhtml]<blockquote>[/xhtml], or [xhtml]<table>[/], but without [val]continued[/] class."
"s-082", "Element containing Latin script for a non-Latin-script language, but its [attr]xml:lang[/] attribute value is missing the [val]-Latn[/] language tag suffix. Hint: For example Russian transliterated into Latin script would be [val]ru-Latn[/]."
"s-083", "[xhtml]<td epub:type=\"z3998:persona\">[/] element with child [xhtml]<p>[/] element."
"s-084", "Poem has incorrect semantics."
"s-085", "[xhtml]<h#>[/] element found in a [xhtml]<section>[/] or a [xhtml]<article>[/] at an unexpected level. Hint: Headings not in the half title page start at [xhtml]<h2>[/]. If this work has parts, should this header be [xhtml]<h3>[/] or higher?"
"s-086", "[text]Op. Cit.[/] or [text]Loc. Cit.[/] in endnote. Hint: [text]Op. Cit.[/] and [text]Loc. Cit.[/] mean [text]the previous reference[/], which usually doesn’t make sense in a popup endnote. Such references should be expanded."
"s-087", "Subtitle in metadata, but no subtitle in the half title page."
"s-088", "Subtitle in half title page, but no subtitle in metadata."
"s-089", "MathML missing [attr]alttext[/] attribute."
"s-090", "Invalid language tag."
"s-091", "[xhtml]<span>[/] not followed by [xhtml]<br/>[/] in poetry."
"s-092", "Anonymous contributor with [val]z3998:*-name[/] semantic."
"s-093", "Nested [xhtml]<abbr>[/] element."
"s-094", "Element has an [attr]xml:lang[/] attribute that incorrectly contains [val]-latn[/] instead of [val]-Latn[/]."
"s-095", "[xhtml]<p>[/] child of [xhtml]<hgroup>[/] in poetry/verse does not have [css]text-align: center;[/]."
"s-096", "[xhtml]h1[/] element in half title page missing the [val]fulltitle[/] semantic."
"s-097", "[xhtml]a[/] element without [attr]href[/] attribute."
"s-098", "[xhtml]<header>[/] element with only one child."
"s-099", "List item in endnotes missing [xhtml]endnote[/] semantic."
"s-100", "Anonymous digital contributor value not exactly [text]An Anonymous Volunteer[/]."
"s-101", "Anonymous primary contributor value not exactly [text]Anonymous[/]."
"s-102", "[attr]lang[/] attribute detected. Hint: Use [attr]xml:lang[/] instead."
"s-103", "Probable missing semantics for a roman I numeral."

TYPOGRAPHY
"t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)"
"t-002", "Comma or period outside of double quote. Generally punctuation goes within single and double quotes."
"t-003", "[text]“[/] missing matching [text]”[/]. Note: When dialog from the same speaker spans multiple [xhtml]<p>[/] elements, it’s correct grammar to omit closing [text]”[/] until the last [xhtml]<p>[/] of dialog."
"t-004", "[text]‘[/] missing matching [text]’[/]."
"t-005", "Dialog without ending comma."
"t-006", "Comma after producer name, but there are only two producers."
"t-007", "Possessive [text]’s[/] within name italics. If the name in italics is doing the possessing, [text]’s[/] goes outside italics."
"t-008", "Repeated punctuation."
"t-009", "Required no-break space not found before time and [text]a.m.[/] or [text]p.m.[/]."
"t-010", "Time set with [text].[/] instead of [text]:[/]."
"t-011", "Missing punctuation before closing quotes."
"t-012", "Illegal white space before noteref."
"t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period."
"t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash."
"t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals."
"t-016", "Initials in [xhtml]<abbr epub:type=\"z3998:*-name\">[/] not separated by spaces."
"t-017", "Ending punctuation inside formatting like bold, small caps, or italics. Ending punctuation is only allowed within formatting if the phrase is an independent clause."
"t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction."
"t-019", "When a complete clause is italicized, ending punctuation except commas must be within containing italics."
"t-020", "Endnote links must be outside of punctuation, including quotation marks."
"t-021", "Measurement not to standard. Numbers are followed by a no-break space and abbreviated units require an [xhtml]<abbr>[/] element. See [path][link=https://standardebooks.org/manual/1.0.0/8-typography#8.8.5]semos://1.0.0/8.8.5[/][/]."
"t-022", "No-break space found in [xhtml]<abbr epub:type=\"z3998:*-name\">[/]. This is redundant."
"t-023", "Comma inside [xhtml]<i>[/] element before closing dialog."
"t-024", "When italicizing language in dialog, italics go inside quotation marks."
"t-025", "Non-typogrified [text]'[/], [text]\"[/] (as [xhtml]&quot;[/]), or [text]--[/] in image [attr]alt[/] attribute."
"t-026", "[attr]alt[/] attribute does not appear to end with punctuation. [attr]alt[/] attributes must be composed of complete sentences ending in appropriate punctuation."
"t-027", "Endnote backlink not preceded by exactly one space."
"t-028", "Possible mis-curled quotation mark."
"t-029", "Period followed by lowercase letter. Hint: Abbreviations require an [xhtml]<abbr>[/] element."
"t-030", "Initialism with spaces or without periods."
"t-031", "[text]A B C[/] must be set as [text]A.B.C.[/] It is not an abbreviation."
"t-032", "Initialism or name followed by period. Hint: Periods go within [xhtml]<abbr>[/]. [xhtml]<abbr>[/]s containing periods that end a clause require the [class]eoc[/] class."
"t-033", "Space after dash."
"t-034", "[xhtml]<cite>[/] element preceded by em-dash. Hint: em-dashes go within [xhtml]<cite>[/] elements."
"t-035", "[xhtml]<cite>[/] element not preceded by space."
"t-036", "Em-dash used to obscure single digit in year. Hint: Use a hyphen instead."
"t-037", "[text]”[/] preceded by space."
"t-038", "[text]“[/] before closing [xhtml]</p>[/]."
"t-039", "Initialism followed by [text]’s[/]. Hint: Plurals of initialisms are not followed by [text]’[/]."
"t-040", "Subtitle with illegal ending period."
"t-041", "Illegal space before punctuation."
"t-043", "Non-English loan word set in italics, when modern typography omits italics. Hint: A word may be correctly italicized when emphasis is desired, if the word is meant to be pronounced with an accent, or if the word is part of non-English speech."
"t-044", "Comma required after leading [text]Or[/] in subtitles."
"t-045", "Element has [val]z3998:persona[/] semantic and is also set in italics."
"t-046", "[text]῾[/] (U+1FFE) detected. Use [text]ʽ[/] (U+02BD) instead."
"t-047", "[text]US[/] should be [text]U.S.[/]"
"t-048", "Chapter opening text in all-caps."
"t-049", "Two-em-dash used for eliding an entire word. Use a three-em-dash instead."
"t-050", "Possessive [text]’s[/] or [text]’[/] outside of element with [val]z3998:persona[/] semantic."
"t-051", "Dialog in [xhtml]<p>[/] that continues to the next [xhtml]<p>[/], but the next [xhtml]<p>[/] does not begin with [text]“[/]."
"t-052", "Stage direction without ending punctuation. Note that ending punctuation is optional in stage direction that is an interjection in a parent clause, and such interjections should begin with a lowercase letter."
"t-053", "Stage direction starting in lowercase letter."
"t-054", "Epigraphs that are entirely non-English should be set in italics, not Roman."
"t-055", "Lone acute accent ([val]´[/]). A more accurate Unicode character like prime for coordinates or measurements, or combining accent or breathing mark for Greek text, is required."
"t-056", "Masculine ordinal indicator ([val]º[/]) used instead of degree symbol ([val]°[/]). Note that the masculine ordinal indicator may be appropriate for ordinal numbers read as Latin, i.e. [val]12º[/] reading [val]duodecimo[/]."
"t-057", "[xhtml]<p>[/] starting with lowercase letter. Hint: [xhtml]<p>[/] that continues text after a [xhtml]<blockquote>[/] requires the [class]continued[/] class; and use [xhtml]<br/>[/] to split one clause over many lines."
"t-058", "Illegal character."
"t-059", "Period at the end of [xhtml]<cite>[/] element before endnote backlink."
"t-060", "Old style Bible citation."
"t-061", "Summary-style bridgehead without ending punctuation."
"t-062", "Uppercased [text]a.m.[/] and [text]p.m.[/]"
"t-063", "Non-English confusable phrase set without italics."
"t-064", "Title not correctly titlecased. Hint: Non-English titles should have an [attr]xml:lang[/] attribute as they have different titlecasing rules."
"t-065", "Header ending in a period."
"t-066", "Regnal ordinal preceded by [text]the[/]."
"t-067", "Plural [val]z3998:grapheme[/], [val]z3998:phoneme[/], or [val]z3998:morpheme[/] formed without apostrophe ([text]’[/])."
"t-068", "Citation not offset with em dash."
"t-069", "[xhtml]<cite>[/] in epigraph starting with an em dash."
"t-070", "[xhtml]<cite>[/] in epigraph ending in a period."
"t-071", "Multiple transcriptions listed, but preceding text is [text]a transcription[/]."
"t-072", "[text]various sources[/] link not preceded by [text]from[/]."
"t-073", "Possible transcription error in Greek."
UNUSED
vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
"t-042", "Possible typo."

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
"x-017", "Duplicate value for [attr]id[/] attribute."
"x-018", "Unused [xhtml]id[/] attribute."
"x-019", "Unexpected value of [attr]id[/] attribute. Expected: [attr]{unexpected_id[1]}[/]."

TYPOS
"y-001", "Possible typo: doubled [text]a/the/and/of/or/as/if[/]."
"y-002”, "Possible typo: punctuation followed directly by a letter, without a space."
"y-003”, "Possible typo: paragraph missing ending punctuation."
"y-004”, "Possible typo: mis-curled quotation mark after dash."
"y-005”, "Possible typo: question mark or exclamation mark followed by period or comma."
"y-006”, "Possible typo: [text]‘[/] without matching [text]’[/]. Hints: [text]’[/] are used for abbreviations;	commas and periods must go inside quotation marks."
"y-007”, "Possible typo: [text]‘[/] not within [text]“[/]. Hints: Should [text]‘[/] be replaced with [text]“[/]? Is there a missing closing quote? Is this a nested quote that should be preceded by [text]“[/]? Are quotes in close proximity correctly closed?"
"y-008”, "Possible typo: dialog interrupted by interjection but with incorrect closing quote."
"y-009”, "Possible typo: dialog begins with lowercase letter."
"y-010”, "Possible typo: comma ending dialogue."
"y-011", "Possible typo: two or more [text]’[/] in a row."
"y-012”, "Possible typo: [text]”[/] directly followed by letter."
"y-013”, "Possible typo: punctuation not within [text]’[/]."
"y-014”, "Possible typo: Unexpected [text].[/] at the end of quotation. Hint: If a dialog tag follows, should this be [text],[/]?"
"y-015”, "Possible typo: mis-curled [text]‘[/] or missing [text]’[/]."
"y-016”, "Possible typo: consecutive periods ([text]..[/])."
"y-017”, "Possible typo: [text]“[/] followed by space."
"y-018”, "Possible typo: [text]‘[/] followed by space."
"y-019”, "Possible typo: [text]”[/] without opening [text]“[/]."
"y-020”, "Possible typo: consecutive comma-period ([text],.[/])."
"y-021”, "Possible typo: Opening [text]‘[/] without preceding [text]“[/]."
"y-022”, "Possible typo: consecutive quotations without intervening text, e.g. [text]“…” “…”[/]."
"y-023”, "Possible typo: two opening quotation marks in a run. Hint: Nested quotes should switch between [text]“[/] and [text]‘[/]"
"y-024”, "Possible typo: dash before [text]the/there/is/and/they/when[/] probably should be em-dash."
"y-025”, "Possible typo: comma without space followed by quotation mark."
"y-026”, "Possible typo: no punctuation before conjunction [text]But/And/For/Nor/Yet/Or[/]."
"y-027”, "Possible typo: Extra [text]’[/] at end of paragraph."
"y-028”, "Possible typo: [xhtml]<abbr>[/] directly preceded or followed by letter."
"y-029", "Possible typo: Italics followed by a letter."
"y-030”, "Possible typo: Lowercase quotation following a period. Check either that the period should be a comma, or that the quotation should start with a capital."
"y-031”, "Possible typo: Dialog tag missing punctuation."
"y-032”, "Possible typo: Italics running into preceding or following characters."
"y-033", "Possible typo: Three-em-dash obscuring an entire word, but not preceded by a space."
"""

class LintMessage:
	"""
	An object representing an output message for the lint function.

	Contains information like message text, severity, and the epub filename that generated the message.
	"""

	def __init__(self, code: str, text: str, message_type=se.MESSAGE_TYPE_WARNING, filename: Optional[Path] = None, submessages: Optional[Union[List[str], Set[str]]] = None):
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

class EbookSection:
	"""
	A convenience class representing a section, its expected <h#> level, and its children EbookSections
	"""

	def __init__(self, section_id: str, depth: int, has_header: bool):
		self.section_id = section_id
		self.children: List[EbookSection] = []
		self.has_header = has_header
		# h# can't go past 6, but we may go deeper in real life like in
		# Wealth of Nations by Adam Smith
		self.depth = depth if depth <= 6 else 6

def _build_section_tree(self) -> List[EbookSection]:
	"""
	Helper function used in self.lint()
	Walk the files in spine order to build a tree of sections and heading levels.

	INPUTS
	self

	OUTPUTS
	section_tree, A list of EbookSections
	"""

	# section_tree is a list of EbookSections.
	# For example, The Woman in White by Wilkie Collins would have a section_tree that looks like this:
	# titlepage (1)
	#  imprint (2)
	#  dedication (2)
	#  preface (2)
	#  halftitlepage (2)
	#  part-1 (2)
	#	 division-1-1 (3)
	#	   chapter-1-1-1 (4)
	#	   chapter-1-1-2 (4)
	#	   chapter-1-1-3 (4)
	#	   chapter-1-1-4 (4)
	section_tree: List[EbookSection] = []

	for filename in self.spine_file_paths:
		dom = self.get_dom(filename)
		for dom_section in dom.xpath("/html/body//*[re:test(name(), '^(section|article|nav)$')][@id]"):
			# Start at h2 by default except for the titlepage, which is always h1
			starting_depth = 1 if regex.findall(r"\btitlepage\b", dom_section.get_attr("epub:type") or "") else 2

			section = _find_ebook_section(dom_section.get_attr("id"), section_tree)

			section_parent_id = dom_section.get_attr("data-parent")

			has_header = bool(dom_section.xpath("./*[re:test(name(), '^h[1-6]$')]"))
			if not has_header:
				has_header = bool(dom_section.xpath(".//*[not(re:test(name(), '^(section|article|nav)$'))]//*[re:test(name(), '^h[1-6]$')]"))

			if not section_parent_id:
				# We don't have a data-parent, but do we have a direct parent section in the same file as this section?
				direct_parent = dom_section.xpath("./ancestor::*[re:test(name(), '^(section|article|nav)$')][@id][1]")

				if direct_parent:
					section_parent_id = direct_parent[0].get_attr("id")

			# If we don't have the section in our list yet, and it has a parent, append it to the parent
			if not section and section_parent_id:
				parent = _find_ebook_section(section_parent_id, section_tree)
				if parent:
					# Only increment the depth if the parent has a header. If it doesn't then we don't want to increment,
					# because we will end up skipping an h# level (like h2 -> h4 instead of h2 -> h3)
					parent.children.append(EbookSection(dom_section.get_attr("id"), parent.depth + 1 if parent.has_header else parent.depth, has_header))

			# If we don't have it in our list yet, and it has no parent, append it to the top
			elif not section:
				section_tree.append(EbookSection(dom_section.get_attr("id"), starting_depth, has_header))

	return section_tree

def _find_ebook_section(section_id: str, sections: List[EbookSection]) -> Union[EbookSection, None]:
	"""
	Find an ebook section in a tree of sections.

	INPUTS
	section_id: The name of the section to be found
	sections: A list of EbookSections

	OUTPUTS
	The entry from sections, if any, that contains section_id
 	"""

	for section in sections:
		if section.section_id == section_id:
			return section

		target_section = _find_ebook_section(section_id, section.children)

		if target_section:
			return target_section

	return None

def _lint_metadata_checks(self) -> list:
	"""
	Process main metadata checks

	INPUTS
	self

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []
	metadata_xml = self.metadata_dom.to_string()
	missing_metadata_elements = []

	# Check for non-English Wikipedia URLs
	nodes = self.metadata_dom.xpath("/package/metadata/*[re:test(., 'https://(?!en)[a-z]{2,}\\.wikipedia\\.org')]")
	if nodes:
		messages.append(LintMessage("m-043", "Non-English Wikipedia URL.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in nodes]))

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
				if author_last_name.lower() in regex.sub(r"https://standardebooks\.org/ebooks/[^/]+?/", "", long_description.lower()) and not regex.search(fr"<a href=\"https://standardebooks\.org/ebooks/.+?\">.*?{author_last_name}.*?</a>", long_description, flags=regex.IGNORECASE):
					messages.append(LintMessage("m-056", "Author name present in [xml]<meta property=\"se:long-description\">[/] element, but the first instance of their name is not hyperlinked to their S.E. author page.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# Did we mention an SE book in the long description, but without italics?
		# Only match if the title appears to contain an uppercase letter. This prevents matches on a non-title link like `<a href>short stories</a>`
		matches = regex.search(r"""(?<!<i>)<a href="https://standardebooks\.org/ebooks/[^"]+?/[^"]+?">(?!<i>)([\p{Letter}\s]+)""", long_description)
		if matches and regex.search(r"[\p{Uppercase_Letter}]", matches[1]):
			messages.append(LintMessage("m-064", "S.E. ebook hyperlinked in long description but not italicized.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		if regex.search(r"""<a href="https?://(?!standardebooks\.org)""", long_description):
			messages.append(LintMessage("m-067", "Non-S.E. link in long description.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# xml:lang is correct for the rest of the publication, but should be lang in the long desc
		if "xml:lang" in long_description:
			messages.append(LintMessage("m-057", "[xml]xml:lang[/] attribute in [xml]<meta property=\"se:long-description\">[/] element should be [xml]lang[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# US -> U.S.
		matches = regex.findall(r"\bUS\b", long_description)
		if matches:
			messages.append(LintMessage("t-047", "[text]US[/] should be [text]U.S.[/]", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

		# Make sure long-description is escaped HTML
		if not regex.search(r"^\s*<p>", long_description) and long_description.strip() != "LONG_DESCRIPTION":
			messages.append(LintMessage("m-016", "Long description must be escaped HTML.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
		else:
			# Check for malformed long description HTML
			try:
				etree.parse(io.StringIO(f"<?xml version=\"1.0\"?><html xmlns=\"http://www.w3.org/1999/xhtml\">{long_description}</html>"))
			except lxml.etree.XMLSyntaxError as ex:
				messages.append(LintMessage("m-015", f"Metadata long description is not valid XHTML. LXML says: {ex}", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# Check for apostrophes outside links in long description
		matches = regex.findall(r"</a>’s", long_description) + regex.findall(r"s</a>’", long_description)
		if matches:
			messages.append(LintMessage("m-044", "Possessive [text]’[/] or [text]’s[/] outside of [xhtml]<a>[/] element in long description.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

		# Check for HTML entities in long-description, but allow &amp;amp;
		matches = regex.findall(r"&[a-z0-9]+?;", long_description.replace("&amp;", ""))
		if matches:
			messages.append(LintMessage("m-018", "HTML entities found. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

	except Exception:
		if self.is_se_ebook:
			missing_metadata_elements.append("""<meta id="long-description" property="se:long-description" refines="#description">""")

	missing_metadata_vars = []
	for node in self.metadata_dom.xpath("/package/metadata/*/text()"):
		for var in SE_VARIABLES:
			if regex.search(fr"\b{var}\b", node):
				missing_metadata_vars.append(var)
				# Quit the loop early to save some time
				break

	if missing_metadata_vars:
		messages.append(LintMessage("m-036", "Variable not replaced with value.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, missing_metadata_vars))

	# Check if there are non-typogrified quotes or em-dashes in the title.
	try:
		title = self.metadata_dom.xpath("/package/metadata/dc:title")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", title)
		if matches:
			messages.append(LintMessage("m-012", "Non-typogrified character in [xml]<dc:title>[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

		# Do we need an dcterms:alternate meta element?
		# Match spelled-out numbers with a word joiner, so for ex. we don't print "eight" if we matched "eighty"
		matches = regex.findall(r"(?:[0-9]+|\bone\b|\btwo\b|\bthree\b|\bfour\b|\bfive\b|\bsix\b|\bseven\b|\beight\b|\bnine\b|\bten\b|\beleven\b|\btwelve\b|\bthirteen\b|\bfourteen\b|\bfifteen\b|\bsixteen\b|\bseventeen\b|\beighteen\b|\bnineteen\b|\btwenty\b|\bthirty\b|\bforty\b|\bfifty\b|\bsixty\b|\bseventy\b|\beighty|\bninety)", title, flags=regex.IGNORECASE)
		if matches and not self.metadata_dom.xpath("/package/metadata/meta[@property='dcterms:alternate']"):
			messages.append(LintMessage("m-052", "[xml]<dc:title>[/] element contains numbers, but no [xml]<meta property=\"dcterms:alternate\" refines=\"#title\"> element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))
	except Exception:
		missing_metadata_elements.append("<dc:title>")

	try:
		file_as = self.metadata_dom.xpath("/package/metadata/meta[@property='file-as' and @refines='#title']")[0].text
		matches = regex.findall(r".(?:['\"]|\-\-|\s-\s).", file_as)
		if matches:
			messages.append(LintMessage("m-050", "Non-typogrified character in [xml]<meta property=\"file-as\" refines=\"#title\">[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))
	except Exception:
		missing_metadata_elements.append("<meta property=\"file-as\" refines=\"#title\">")

	try:
		description = self.metadata_dom.xpath("/package/metadata/dc:description")[0].text
		matches = regex.findall(r"(?:['\"]|\-\-|\s-\s)", description)
		if matches:
			messages.append(LintMessage("m-013", "Non-typogrified character in [xml]<dc:description>[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))
	except Exception:
		missing_metadata_elements.append("<dc:description>")

	# Check for illegal Wikipedia URLs
	nodes = self.metadata_dom.xpath("/package/metadata/*[contains(., '.m.wikipedia.org') or @*[contains(., '.m.wikipedia.org')]]")
	if nodes:
		messages.append(LintMessage("m-026", "Illegal [url]https://*.m.wikipedia.org[/] URL. Hint: use non-mobile Wikipedia URLs.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in nodes]))

	# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
	# We can't use xpath's built-in regex because it doesn't support Unicode classes
	for node in self.metadata_dom.xpath("/package/metadata/*"):
		if node.text and regex.search(r"[\p{Letter}]+”[,\.](?! …)", node.text):
			messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation goes within single and double quotes.", se.MESSAGE_TYPE_WARNING, self.metadata_file_path))
			break

	# Check that the word count is correct, if it's currently set
	word_count = self.metadata_dom.xpath("/package/metadata/meta[@property='se:word-count']/text()", True)
	if self.is_se_ebook:
		if word_count is None:
			missing_metadata_elements.append("""<meta property="se:word-count">""")
		elif word_count != "WORD_COUNT" and int(word_count) != self.get_word_count():
			messages.append(LintMessage("m-065", "Word count in metadata doesn’t match actual word count.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check if we have a subtitle but no fulltitle
	if self.metadata_dom.xpath("/package/metadata[./meta[@property='title-type' and text()='subtitle'] and not(./meta[@property='title-type' and text()='extended'])]"):
		messages.append(LintMessage("m-011", "Subtitle in metadata, but no full/extended title element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for tags that imply other tags
	implied_tags = {"Fiction": ["Science Fiction", "Drama", "Fantasy"]}
	for implied_tag, tags in implied_tags.items():
		if self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:subject' and text()={se.easy_xml.escape_xpath(implied_tag)}]"):
			for tag in tags:
				if self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:subject' and text()={se.easy_xml.escape_xpath(tag)}]"):
					messages.append(LintMessage("m-058", f"[val]se:subject[/] of [text]{implied_tag}[/] found, but [text]{tag}[/] implies [text]{implied_tag}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, matches))

	# Check for 'comprised of'
	if self.metadata_dom.xpath("/package/metadata/*[re:test(., '[Cc]omprised of')]"):
		messages.append(LintMessage("m-069", "[text]comprised of[/] in metadata. Hint: Is there a better phrase to use here?", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for illegal em-dashes in <dc:subject>
	nodes = self.metadata_dom.xpath("/package/metadata/dc:subject[contains(text(), '—')]")
	if nodes:
		messages.append(LintMessage("m-019", "Illegal em-dash in [xml]<dc:subject>[/] element; use [text]--[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.text for node in nodes]))

	# Check for incorrect 'anonymous' strings in metadata
	nodes = self.metadata_dom.xpath("/package/metadata/dc:contributor[re:test(., 'anonymous', 'i') and text() != 'Anonymous'] | /package/metadata/meta[@property='file-as' and re:test(., 'anonymous', 'i') and text() != 'Anonymous']")
	if nodes:
		messages.append(LintMessage("m-073", "Anonymous contributor values must be exactly [text]Anonymous[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in nodes]))

	# Check for metadata elements
	nodes = self.metadata_dom.xpath("/package/metadata/*[not(name()='link') and not(normalize-space(.)) and not(./*)]")
	if nodes:
		messages.append(LintMessage("m-022", "Empty element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in nodes]))

	# Check for illegal VCS URLs
	nodes = self.metadata_dom.xpath(f"/package/metadata/meta[@property='se:url.vcs.github' and not(text()='{self.generated_github_repo_url}')]")
	if nodes:
		messages.append(LintMessage("m-009", f"[xml]<meta property=\"se:url.vcs.github\">[/] value does not match expected: [url]{self.generated_github_repo_url}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check for illegal se:subject tags
	illegal_subjects = []
	nodes = self.metadata_dom.xpath("/package/metadata/meta[@property='se:subject']/text()")
	if nodes:
		for node in nodes:
			if node not in SE_GENRES and node != "TAG":
				illegal_subjects.append(node)

		if illegal_subjects:
			messages.append(LintMessage("m-020", "Illegal value for [xml]<meta property=\"se:subject\">[/] element.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, illegal_subjects))

		if sorted(nodes) != nodes:
			messages.append(LintMessage("m-053", "[xml]<meta property=\"se:subject\">[/] elements not in alphabetical order.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	elif self.is_se_ebook:
		messages.append(LintMessage("m-021", "No [xml]<meta property=\"se:subject\">[/] element found.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check that each <dc:title> has a file-as and title-type, if applicable
	titles_missing_file_as = []
	titles_missing_title_type = []
	titles = self.metadata_dom.xpath("/package/metadata/dc:title")
	for node in titles:
		if not self.metadata_dom.xpath(f"/package/metadata/meta[@property='file-as' and @refines='#{node.get_attr('id')}']"):
			titles_missing_file_as.append(node)

		# Only check for title-type if there is more than one <dc:title>
		if len(titles) > 1 and not self.metadata_dom.xpath(f"/package/metadata/meta[@property='title-type' and @refines='#{node.get_attr('id')}']"):
			titles_missing_title_type.append(node)

	if titles_missing_file_as:
		messages.append(LintMessage("m-062", "[xml]<dc:title>[/] missing matching [xml]<meta property=\"file-as\">[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in titles_missing_file_as]))

	if titles_missing_title_type:
		messages.append(LintMessage("m-068", "[xml]<dc:title>[/] missing matching [xml]<meta property=\"title-type\">[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in titles_missing_title_type]))

	# Check for CDATA tags
	if "<![CDATA[" in metadata_xml:
		messages.append(LintMessage("m-017", "[xml]<!\\[CDATA\\[[/] found. Run [bash]se clean[/] to canonicalize [xml]<!\\[CDATA\\[[/] sections.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Check that our provided identifier matches the generated identifier
	if self.is_se_ebook:
		try:
			identifier = self.metadata_dom.xpath("/package/metadata/dc:identifier")[0].text
			if identifier != self.generated_identifier:
				messages.append(LintMessage("m-023", f"[xml]<dc:identifier>[/] does not match expected: [text]{self.generated_identifier}[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
		except Exception:
			missing_metadata_elements.append("<dc:identifier>")

	# Check if se:name.person.full-name matches their titlepage name
	duplicate_names = []
	invalid_refines = []
	nodes = self.metadata_dom.xpath("/package/metadata/meta[@property='se:name.person.full-name']")
	for node in nodes:
		try:
			refines = node.get_attr("refines").replace("#", "")
			try:
				name = self.metadata_dom.xpath(f"/package/metadata/*[@id={se.easy_xml.escape_xpath(refines)}]")[0].text
				if name == node.text:
					duplicate_names.append(name)
			except Exception:
				invalid_refines.append(refines)
		except Exception:
			invalid_refines.append("<meta property=\"se:name.person.full-name\">")

	if duplicate_names:
		messages.append(LintMessage("m-024", "[xml]<meta property=\"se:name.person.full-name\">[/] property identical to regular name. If the two are identical the full name [xml]<meta>[/] element must be removed.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, duplicate_names))

	if invalid_refines:
		messages.append(LintMessage("m-010", "Invalid [xml]refines[/] property.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, invalid_refines))

	if self.metadata_dom.xpath("/package/metadata/*[contains(., 'https://id.loc.gov/')]"):
		messages.append(LintMessage("m-066", "[url]id.loc.gov[/] URI starting with illegal https.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	if self.metadata_dom.xpath("/package/metadata/*[re:test(., 'id\\.loc\\.gov/authorities/names/[^\\.]+\\.html')]"):
		messages.append(LintMessage("m-008", "[url]id.loc.gov[/] URI ending with illegal [path].html[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	if self.metadata_dom.xpath("/package/metadata/dc:description[text()!='DESCRIPTION' and re:test(., '[^\\.”]$')]"):
		messages.append(LintMessage("m-055", "[xml]dc:description[/] does not end with a period.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	# Does the manifest match the generated manifest?
	try:
		manifest = self.metadata_dom.xpath("/package/manifest")[0]
		if manifest.to_string().replace("\t", "") != self.generate_manifest().to_string().replace("\t", ""):
			messages.append(LintMessage("m-042", "[xml]<manifest>[/] element does not match expected structure.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))
	except Exception:
		missing_metadata_elements.append("<manifest>")

	if missing_metadata_elements:
		messages.append(LintMessage("m-051", "Missing expected element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, missing_metadata_elements))

	# Check for common typos in description
	for node in self.metadata_dom.xpath("/package/metadata/dc:description") + self.metadata_dom.xpath("/package/metadata/meta[@property='se:long-description']"):
		matches = regex.findall(r"(?<!’)\b(and and|the the|if if|of of|or or|as as)\b(?!-)", node.text, flags=regex.IGNORECASE)
		matches = matches + regex.findall(r"\ba a\b(?!-)", node.text)
		if matches:
			messages.append(LintMessage("y-001", "Possible typo: doubled [text]a/the/and/of/or/as/if[/].", se.MESSAGE_TYPE_WARNING, self.metadata_file_path, matches))

	nodes = self.metadata_dom.xpath("/package/metadata//*[re:test(., '[,;][a-z]', 'i')]")
	if nodes:
		messages.append(LintMessage("y-002", "Possible typo: punctuation followed directly by a letter, without a space.", se.MESSAGE_TYPE_WARNING, self.metadata_file_path, [node.to_string() for node in nodes]))

	return messages

def _get_malformed_urls(dom: se.easy_xml.EasyXmlTree, filename: Path) -> list:
	"""
	Helper function used in self.lint()
	Get a list of URLs in the epub that don't match SE standards.

	INPUTS
	dom: A dom tree to check
	filename: The filename being processed

	OUTPUTS
	A list of LintMessage objects.
	"""

	messages = []

	# Check for non-https URLs
	search_regex = r"(?<!www\.)gutenberg\.org"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-001", "gutenberg.org URL missing leading [text]www.[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"www\.archive\.org"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-002", "archive.org URL should not have leading [text]www.[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"www\.gutenberg\.net\.au"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-076", "gutenberg.net.au URL should not have leading [text]www.[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"http://(gutenberg\.org|gutenberg\.net\.au|gutenberg\.ca|www\.fadedpage\.com|archive\.org|pgdp\.net|catalog\.hathitrust\.org|en\.wikipedia\.org|standardebooks\.org)"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-003", "Non-HTTPS URL.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"https?://books\.google\.com/books\?id=.+?[&#]"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-004", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://books.google.com/books?id=<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"https?://www\.google\.com/books/edition/[^/]+?/[^/?#]+/?[&#?]"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-060", "Non-canonical Google Books URL. Google Books URLs must look exactly like [url]https://www.google.com/books/edition/<BOOK-NAME>/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"https?://(babel\.hathitrust\.org|hdl\.handle\.net)"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-005", "Non-canonical HathiTrust URL. HathiTrust URLs must look exactly like [url]https://catalog.hathitrust.org/Record/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"https?://.*?gutenberg\.org/(files|cache)"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-006", "Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like [url]https://www.gutenberg.org/ebooks/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"^https?://.*?archive\.org/(stream|details/.+?/page.+)"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-007", "Non-canonical archive.org URL. Internet Archive URLs must look exactly like [url]https://archive.org/details/<BOOK-ID>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	search_regex = r"https?://standardebooks\.org[^\s]*/$"
	nodes = dom.xpath(f"/package/metadata/*[re:test(., '{search_regex}')] | /html/body//a[re:test(@href, '{search_regex}')]")
	if nodes:
		messages.append(LintMessage("m-054", "Standard Ebooks URL with illegal trailing slash.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	return messages

def _get_selectors_and_rules (self) -> tuple:
	"""
	Helper function used in self.lint()
	Construct a set of CSS selectors and rules in local.css

	INPUTS
	None

	OUTPUTS
	2-tuple (local_css_rules, duplicate_selectors) to be used by the lint function
	"""

	def _recursive_helper(rules: cssutils.css.cssstylesheet.CSSStyleSheet, local_css_rules: dict, duplicate_selectors: list, single_selectors: list, top_level: bool):
		"""
		Because of the possibilty of nested @supports and @media at-rules, we
		need to use recursion to get to rules and selectors within at-rules.
		This function is the helper for _get_selectors_and_rules and does the
		actual work.

		INPUTS
		rules: A CSSStyleSheet with the rules
		local_css_rules: A dictionary where key = selector and value = rules
		duplicate_selectors: Selectors which are counted as duplicates and will be warned about
		single_selectors: Not multiple selectors separated by comma
		top_level: Boolean set to True on first level of recursion and False thereafter

		OUTPUTS
		2-tuple (local_css_rules, duplicate_selectors) to be used by the lint function
		"""
		for rule in rules:
			# i.e. @supports or @media
			if isinstance(rule, cssutils.css.CSSMediaRule):
				# Recurisive call to rules within CSSMediaRule.
				new_rules = _recursive_helper(rule.cssRules, local_css_rules, duplicate_selectors, single_selectors, False)

				# Then update local_css_rules. The duplicate and single selector lists aren't updated
				# because anything within CSSMediaRules isn't counted as a duplicate
				local_css_rules.update(new_rules[0])

			# Recursive end condition
			if isinstance(rule, cssutils.css.CSSStyleRule):
				for selector in rule.selectorList:
					# Check for duplicate selectors.
					# We consider a selector a duplicate if it's a TOP LEVEL selector (i.e. we don't check within @supports)
					# and ALSO if it is a SINGLE selector (i.e. not multiple selectors separated by ,)
					# For example abbr{} abbr{} would be a duplicate, but not abbr{} abbr,p{}
					if "," not in rule.selectorText:
						if top_level:
							if selector.selectorText in single_selectors:
								duplicate_selectors.append(selector.selectorText)
							else:
								single_selectors.append(selector.selectorText)

					if selector.selectorText not in local_css_rules:
						local_css_rules[selector.selectorText] = ""

					local_css_rules[selector.selectorText] += rule.style.cssText + ";"

		return (local_css_rules, duplicate_selectors)

	local_css_rules: Dict[str, str] = {} # A dict where key = selector and value = rules
	duplicate_selectors: List[str] = []
	single_selectors: List[str] = []

	# cssutils doesn't understand @supports, but it *does* understand @media, so do a replacement here for the purposes of parsing
	all_rules = cssutils.parseString(self.local_css.replace("@supports", "@media"), validate=False)

	# Initial recursive call
	_recursive_helper(all_rules, local_css_rules, duplicate_selectors, single_selectors, True)

	return (local_css_rules, duplicate_selectors)

def files_not_in_spine(self) -> set:
	"""
	Check the spine against the actual files.

	INPUTS
	None

	OUTPUTS
	Set of files not in the spine (typically an empty set)
	"""

	xhtml_files = set(self.content_path.glob("**/*.xhtml"))
	spine_files = set(self.spine_file_paths + [self.toc_path])
	return xhtml_files.difference(spine_files)

def _lint_css_checks(self, local_css_path: Path, abbr_with_whitespace: list) -> list:
	"""
	Process main CSS checks

	INPUTS
	self
	local_css: Dictionary of local CSS flags
	local_css_path: Path to local.css file
	local_css_rules: Dictionary of the local CSS rules

	OUTPUTS
	A list of LintMessage objects
	"""
	messages = []

	# lxml has not implemented the following in cssselect: *:first-of-type, *:last-of-type, *:nth-of-type, *:nth-last-of-type, *:only-of-type
	# BUT ONLY WHEN USED ON *. This includes for example: `section [epub|type~="test"]:first-of-type` (note the `*` is implicit)
	# Therefore we can't simplify them in build or test against them.
	matches = regex.findall(r"(?:^| )[^a-z\s][^\s]+?:(?:first-of-type|last-of-type|nth-of-type|nth-last-of-type|only-of-type)", self.local_css, flags=regex.MULTILINE)
	if matches:
		messages.append(LintMessage("c-001", "Don’t use [css]*:first-of-type[/], [css]*:last-of-type[/], [css]*:nth-of-type[/] [css]*:nth-last-of-type[/], or [css]*:only-of-type[/] on [css]*[/]. Instead, specify an element to apply it to.", se.MESSAGE_TYPE_ERROR, local_css_path, matches))

	# If we select on the xml namespace, make sure we define the namespace in the CSS, otherwise the selector won't work
	# We do this using a regex and not with cssutils, because cssutils will barf in this particular case and not even record the selector.
	matches = regex.findall(r"\[\s*xml\s*\|", self.local_css)
	if matches and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in self.local_css:
		messages.append(LintMessage("c-003", "[css]\\[xml|attr][/] selector in CSS, but no XML namespace declared ([css]@namespace xml \"http://www.w3.org/XML/1998/namespace\";[/]).", se.MESSAGE_TYPE_ERROR, local_css_path))

	if abbr_with_whitespace:
		messages.append(LintMessage("c-005", f"[css]abbr[/] selector does not need [css]white-space: nowrap;[/] as it inherits it from [path][link=file://{self.path / 'src/epub/css/core.css'}]core.css[/][/].", se.MESSAGE_TYPE_ERROR, local_css_path, abbr_with_whitespace))

	if regex.search(r"\s+hyphens:.+?;(?!\s+-epub-hyphens)", self.local_css):
		messages.append(LintMessage("c-007", "[css]hyphens[/css] CSS property without [css]-epub-hyphens[/css] copy.", se.MESSAGE_TYPE_ERROR, local_css_path))

	matches = regex.findall(r"text-align:\s*left\s*;", self.local_css)
	if matches:
		messages.append(LintMessage("c-016", "[css]text-align: left;[/] found. Use [css]text-align: initial;[/] instead.", se.MESSAGE_TYPE_ERROR, local_css_path))

	matches = regex.findall(r"[0-9\.]\s?rem;", self.local_css)
	if matches:
		messages.append(LintMessage("c-022", "Illegal [css]rem[/] unit. Use [css]em[/] instead.", se.MESSAGE_TYPE_ERROR, local_css_path))

	matches = regex.findall(r"font-size\s*:\s*[0-9\.]+(?![0-9\.]|em|ex)", self.local_css)
	if matches:
		messages.append(LintMessage("c-023", "Illegal unit used to set [css]font-size[/]. Hint: Use [css]em[/] units.", se.MESSAGE_TYPE_ERROR, local_css_path))

	matches = regex.findall(r"line-height\s*:\s*[0-9\.]+(?!;|[0-9\.]+)", self.local_css)
	if matches:
		messages.append(LintMessage("c-024", "Illegal unit used to set [css]line-height[/]. Hint: [css]line-height[/] is set without any units.", se.MESSAGE_TYPE_ERROR, local_css_path))

	matches = regex.findall(r"(height|\stop|\sbottom)\s*:\s*[0-9\.]+%", self.local_css)
	if matches:
		messages.append(LintMessage("c-025", "Illegal percent unit used to set [css]height[/] or positioning property. Hint: [css]vh[/] to specify vertical-oriented properties like height or position.", se.MESSAGE_TYPE_ERROR, local_css_path))

	return messages

def _update_missing_styles(filename: Path, dom: se.easy_xml.EasyXmlTree, local_css: dict) -> list:
	"""
	Identify any missing CSS styles in the file being checked

	INPUTS
	filename: the name of the file being checked
	dom: The dom of the file being checked
	local_css: Dictionary containing several flags concerning the local CSS

	OUTPUTS
	List of styles used in this file but missing from local CSS
	"""

	missing_styles: List[str] = []

	if not local_css["has_elision_style"]:
		missing_styles += [node.to_tag_string() for node in dom.xpath("/html/body//span[contains(@class, 'elision')]")]

	# Check to see if we included poetry or verse without the appropriate styling
	if filename.name not in IGNORED_FILENAMES:
		nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')][./p/span]")
		for node in nodes:
			if "z3998:poem" in node.get_attr("epub:type") and not local_css["has_poem_style"]:
				missing_styles.append(node.to_tag_string())

			if "z3998:verse" in node.get_attr("epub:type") and not local_css["has_verse_style"]:
				missing_styles.append(node.to_tag_string())

			if "z3998:song" in node.get_attr("epub:type") and not local_css["has_song_style"]:
				missing_styles.append(node.to_tag_string())

			if "z3998:hymn" in node.get_attr("epub:type") and not local_css["has_hymn_style"]:
				missing_styles.append(node.to_tag_string())

			if "z3998:lyrics" in node.get_attr("epub:type") and not local_css["has_lyrics_style"]:
				missing_styles.append(node.to_tag_string())

		# Check frontmatter for missing styling
		nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'epigraph') and not(.//h2)]")
		for node in nodes:
			if not local_css["has_epigraph_style"]:
				missing_styles.append(node.to_tag_string())

		# Check for missing dedication styling, but not if the dedication is in a <header> as those are typically unstyled
		nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'dedication') and not(re:test(@epub:type, 'z3998:(poem|verse|hymn|song)')) and not(./ancestor::header) and not(.//h2) and not(count(.//p) > 3)]")
		for node in nodes:
			if not local_css["has_dedication_style"]:
				missing_styles.append(node.to_tag_string())

	return missing_styles

def _lint_image_checks(self, filename: Path) -> list:
	"""
	Process image checks

	INPUTS
	self
	filename: The name of the file being processed

	OUTPUTS
	A list of LintMessage objects.
	"""
	messages = []

	if filename.suffix == ".jpeg":
		messages.append(LintMessage("f-011", "JPEG files must end in [path].jpg[/].", se.MESSAGE_TYPE_ERROR, filename))
	elif filename.suffix == ".tiff":
		messages.append(LintMessage("f-012", "TIFF files must end in [path].tif[/].", se.MESSAGE_TYPE_ERROR, filename))

	# Run some general tests on images, but skip the cover source since it's an exception to all of these rules
	if "cover.source" not in filename.name:
		try:
			image = Image.open(filename)
		except UnidentifiedImageError as ex:
			raise se.InvalidFileException(f"Couldn’t identify image type of [path][link=file://{filename}]{filename.name}[/][/].") from ex

		# Check the source cover image
		if self.path / "images" / "cover.jpg" == filename:
			if image.size != (se.COVER_WIDTH, se.COVER_HEIGHT):
				messages.append(LintMessage("f-017", f"[path][link=file://{self.path / 'images/cover.jpg'}]cover.jpg[/][/] must be exactly {se.COVER_WIDTH} × {se.COVER_HEIGHT}.", se.MESSAGE_TYPE_ERROR, filename))

		# Run some tests on distributable images in ./src/epub/images/
		# Once we reach Python 3.9 we can use path.is_relative_to() instead of this string comparison
		if str(filename).startswith(str(self.content_path / "images")):
			if os.path.getsize(filename) > 1500000: # 1.5MB
				messages.append(LintMessage("f-016", "Image more than 1.5MB in size.", se.MESSAGE_TYPE_ERROR, filename))

			# Make sure distributable images have reasonable dimensions
			# We check SVGs later on in a separate check
			if image.size[0] * image.size[1] > 4000000:
				messages.append(LintMessage("f-018", "Image greater than 4,000,000 pixels square in dimension.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.suffix == ".png" and not se.images.has_transparency(image):
				messages.append(LintMessage("f-019", "[path].png[/] file without transparency. Hint: If an image doesn’t have transparency, it should be saved as a [path].jpg[/].", se.MESSAGE_TYPE_ERROR, filename))

	return messages

def _lint_svg_checks(self, filename: Path, file_contents: str, svg_dom: se.easy_xml.EasyXmlTree, root: str) -> list:
	"""
	Perform several checks on svg files

	INPUTS
	filename: The name of the svg file being checked
	file_contents: The contents of the svg file being checked
	svg_dom: The dom of the svg file being checked
	self
	root: The top-level directory

	OUTPUTS
	A list of LintMessage objects.
	"""

	messages = []

	if f"{os.sep}src{os.sep}images{os.sep}" not in root:
		if self.cover_path and filename.name == self.cover_path.name:
			# Check that cover is in all caps
			nodes = svg_dom.xpath("//text[re:test(., '[a-z]')]")
			if nodes:
				messages.append(LintMessage("s-002", "Lowercase letters in cover. Cover text must be all uppercase.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		# Check that titlepage is in all caps
		if filename.name == "titlepage.svg":
			nodes = svg_dom.xpath("//text[re:test(., '[a-z]') and not(text()='translated by' or text()='illustrated by' or text()='and')]")
			if nodes:
				messages.append(LintMessage("s-003", "Lowercase letters in titlepage. Titlepage text must be all uppercase except [text]translated by[/] and [text]illustrated by[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	if self.cover_path and filename.name == self.cover_path.name:
		# Ensure the producer has built the cover.
		# The default cover image is a white background which when encoded to base64 begins with 299 characters and then has a long string of `A`s
		if svg_dom.xpath("//image[re:test(@xlink:href, '^.{299}A{50,}')]"):
			messages.append(LintMessage("m-063", "Cover image has not been built.", se.MESSAGE_TYPE_ERROR, filename))

	# Make images have reasonable dimensions
	viewbox = svg_dom.xpath("/svg/@viewBox", True)
	if viewbox:
		svg_dimensions = viewbox.split()
		try:
			if float(svg_dimensions[2]) * float(svg_dimensions[3]) > 4000000:
				messages.append(LintMessage("f-018", "Image greater than 4,000,000 pixels square in dimension.", se.MESSAGE_TYPE_ERROR, filename))
		except Exception as ex:
			raise se.InvalidFileException(f"Couldn’t parse SVG [xhtml]viewBox[/] attribute in [path][link=file://{filename.resolve()}]{filename}[/][/].") from ex

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

	# Check for fill: #000 which should simply be removed
	nodes = svg_dom.xpath("//*[contains(@fill, '#000') or contains(translate(@style, ' ', ''), 'fill:#000')]")
	if nodes:
		messages.append(LintMessage("x-004", "Illegal [xml]style=\"fill: #000\"[/] or [xml]fill=\"#000\"[/].", se.MESSAGE_TYPE_ERROR, filename))

	# Check for illegal height or width on root <svg> element
	if filename.name != "logo.svg": # Do as I say, not as I do...
		if svg_dom.xpath("/svg[@height or @width]"):
			messages.append(LintMessage("x-005", "Illegal [xml]height[/] or [xml]width[/] attribute on root [xml]<svg>[/] element. Size SVGs using the [xml]viewBox[/] attribute only.", se.MESSAGE_TYPE_ERROR, filename))

	match = regex.search(r"viewbox", file_contents, flags=regex.IGNORECASE)
	if match and match[0] != "viewBox":
		messages.append(LintMessage("x-006", f"[xml]{match}[/] found instead of [xml]viewBox[/]. [xml]viewBox[/] must be correctly capitalized.", se.MESSAGE_TYPE_ERROR, filename))

	return messages

def _lint_special_file_checks(self, filename: Path, dom: se.easy_xml.EasyXmlTree, file_contents: str, ebook_flags: dict, special_file: str) -> list:
	"""
	Process error checks in “special” .xhtml files

	INPUTS
	filename: The name of the file being checked
	dom: The dom of the file being checked
	file_contents: The contents of the file being checked
	ebook_flags: A dictionary containing ebook information
	special_file: A string identifying the type of special file being checked
	self

	OUTPUTS
	A list of LintMessage objects.
	"""

	messages = []
	source_links = self.metadata_dom.xpath("/package/metadata/dc:source/text()")

	if special_file in ("colophon", "imprint"):
		if len(source_links) <= 2:
			# Check that links back to sources are represented correctly
			nodes = dom.xpath("/html/body//a[@href='https://www.pgdp.net' and text()!='The Online Distributed Proofreading Team']")
			if nodes:
				messages.append(LintMessage("m-071", "DP link must be exactly [text]The Online Distributed Proofreading Team[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

			nodes = dom.xpath("/html/body//a[re:test(@href, '^https://www.pgdp.org/ols/') and text()!='Distributed Proofreaders Open Library System']")
			if nodes:
				messages.append(LintMessage("m-072", "DP OLS link must be exactly [text]Distributed Proofreaders Open Library System[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

			nodes = dom.xpath("/html/body//a[re:test(@href, '^https://[^\"]*?hathitrust.org') and re:test(text(), '[Hh]athi') and not(text()='HathiTrust Digital Library')]")
			if nodes:
				messages.append(LintMessage("m-041", "Hathi Trust link text must be exactly [text]HathiTrust Digital Library[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		nodes = dom.xpath("/html/body//p[re:test(., '\\ba transcription\\b') and ./a[contains(@href, '#transcriptions')]]")
		if nodes:
			messages.append(LintMessage("t-071", "Multiple transcriptions listed, but preceding text is [text]a transcription[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	if special_file == "colophon":
		# Check for illegal Wikipedia URLs
		nodes = dom.xpath("/html/body//a[contains(@href, '.m.wikipedia.org')]")
		if nodes:
			messages.append(LintMessage("m-026", "Illegal [url]https://*.m.wikipedia.org[/] URL. Hint: use non-mobile Wikipedia URLs.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		# Check for non-English Wikipedia URLs
		nodes = dom.xpath("/html/body//a[re:test(@href, 'https://(?!en)[a-z]{2,}\\.wikipedia\\.org')]")
		if nodes:
			messages.append(LintMessage("m-043", "Non-English Wikipedia URL.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, [node.to_string() for node in nodes]))

		# Check for wrong grammar filled in from template
		nodes = dom.xpath("/html/body//a[starts-with(@href, 'https://books.google.com/') or starts-with(@href, 'https://www.google.com/books/')][(preceding-sibling::text()[normalize-space(.)][1])[re:test(., '\\bthe$')]]")
		if nodes:
			messages.append(LintMessage("s-016", "Incorrect [text]the[/] before Google Books link.", se.MESSAGE_TYPE_ERROR, filename, ["the<br/>\n" + node.to_string() for node in nodes]))

		se_url = self.generated_identifier.replace("url:", "")
		if not dom.xpath(f"/html/body//a[@href='{se_url}' and text()='{se_url.replace('https://', '')}']"):
			messages.append(LintMessage("m-035", f"Unexpected S.E. identifier in colophon. Expected: [url]{se_url}[/].", se.MESSAGE_TYPE_ERROR, filename))

		if self.metadata_dom.xpath("/package/metadata/meta[@property='role' and text()='trl']") and "translated from" not in file_contents:
			messages.append(LintMessage("m-025", "Translator found in metadata, but no [text]translated from LANG[/] block in colophon.", se.MESSAGE_TYPE_ERROR, filename))

		if ebook_flags["has_multiple_transcriptions"] and not dom.xpath("/html/body//a[contains(@href, '#transcriptions')]"):
			messages.append(LintMessage("m-074", "Multiple transcriptions found in metadata, but no link to [text]EBOOK_URL#transcriptions[/].", se.MESSAGE_TYPE_ERROR, filename))

		if ebook_flags["has_multiple_page_scans"] and not dom.xpath("/html/body//a[contains(@href, '#page-scans')]"):
			messages.append(LintMessage("m-075", "Multiple page scans found in metadata, but no link to [text]EBOOK_URL#page-scans[/].", se.MESSAGE_TYPE_ERROR, filename))

		# Check that the formula changed from the default if we added 'various sources'
		if ebook_flags["has_multiple_transcriptions"] or ebook_flags["has_multiple_page_scans"]:
			nodes = dom.xpath("/html/body//a[text() = 'various sources' and not(re:test(preceding-sibling::br[1]/preceding-sibling::node()[1], '(digital scans|transcriptions) from\\s*$'))]")
			if nodes:
				messages.append(LintMessage("t-072", "[text]various sources[/] link not preceded by [text]from[/].", se.MESSAGE_TYPE_ERROR, filename))

		# Check if we forgot to fill any variable slots
		missing_colophon_vars = [var for var in SE_VARIABLES if regex.search(fr"\b{var}\b", file_contents)]
		if missing_colophon_vars:
			messages.append(LintMessage("m-036", "Variable not replaced with value.", se.MESSAGE_TYPE_ERROR, filename, missing_colophon_vars))

		# Check that we have <br/>s at the end of lines
		# First, check for b or a elements that are preceded by a newline but not by a br
		nodes = [node.to_string() for node in dom.xpath("/html/body/section/p/*[name()='b' or name()='a'][(preceding-sibling::node()[1])[contains(., '\n')]][not((preceding-sibling::node()[2])[self::br]) or (normalize-space(preceding-sibling::node()[1]) and re:test(preceding-sibling::node()[1], '\\n\\s*$')) ]")]
		# Next, check for text nodes that contain newlines but are not preceded by brs
		nodes = nodes + [node.strip() for node in dom.xpath("/html/body/section/p/text()[contains(., '\n') and normalize-space(.)][(preceding-sibling::node()[1])[not(self::br)]]")]
		if nodes:
			messages.append(LintMessage("s-053", "Colophon line not preceded by [xhtml]<br/>[/].", se.MESSAGE_TYPE_ERROR, filename, nodes))

		# Is there a comma after a producer name, if there's only two producers?
		nodes = dom.xpath("/html/body/section/p/*[name()='b' or name()='a'][(following-sibling::node()[1])[normalize-space(.)=', and']][(preceding-sibling::*[1])[name()='br']]")
		if nodes:
			messages.append(LintMessage("t-006", "Comma after producer name, but there are only two producers.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		nodes = dom.xpath("/html/body//b[re:test(., 'anonymous', 'i') and re:test(@epub:type, 'z3998:.*?name')]")
		if nodes:
			messages.append(LintMessage("s-092", "Anonymous contributor with [val]z3998:*-name[/] semantic.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		# Check for anonymous volunteers misrepresented in the colophon. Note that we only match SE producers and transcribers, because
		# a cover art artist can also be anonymous but they're not volunteers.
		nodes = dom.xpath("/html/body//b[re:test(., 'anonymous', 'i') and text() != 'An Anonymous Volunteer' and (preceding-sibling::a[@href='https://standardebooks.org'])]")
		if nodes:
			messages.append(LintMessage("s-100", "Anonymous digital contributor value not exactly [text]An Anonymous Volunteer[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		# Check for primary contributors misrepresented in the colophon. these differ from ebook production volunteers.
		nodes = dom.xpath("/html/body//b[re:test(., 'anonymous', 'i') and text() != 'Anonymous' and (preceding-sibling::node()[contains(., 'The cover page')] or preceding-sibling::i[contains(@epub:type, 'se:name.publication')])]")
		if nodes:
			messages.append(LintMessage("s-101", "Anonymous primary contributor value not exactly [text]Anonymous[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

		# Is there a page scan link in the colophon, but missing in the metadata?
		for node in dom.xpath("/html/body//a[re:test(@href, '(gutenberg\\.org/ebooks/[0-9]+|hathitrust\\.org|/archive\\.org|books\\.google\\.com|www\\.google\\.com/books/)')]"):
			if not self.metadata_dom.xpath(f"/package/metadata/dc:source[contains(text(), {se.easy_xml.escape_xpath(node.get_attr('href'))})]"):
				messages.append(LintMessage("m-059", f"Link to [url]{node.get_attr('href')}[/] found in colophon, but missing matching [xhtml]dc:source[/] element in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		# Are the sources represented correctly?
		# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
		# We can't merge this with the imprint check because imprint doesn't have `<br/>` between `the`
		if not ebook_flags["has_multiple_transcriptions"] and not ebook_flags["has_other_sources"]:
			for link in source_links:
				if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: [xhtml]<a href=\"{link}\">Project Gutenberg</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

		if not ebook_flags["has_multiple_page_scans"] and not ebook_flags["has_other_sources"]:
			for link in source_links:
				if "hathitrust.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: [xhtml]the<br/> <a href=\"{link}\">HathiTrust Digital Library</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

				if "archive.org" in link and f"the<br/>\n\t\t\t<a href=\"{link}\">Internet Archive</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: [xhtml]the<br/> <a href=\"{link}\">Internet Archive</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

				if ("books.google.com" in link or "www.google.com/books/" in link) and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: [xhtml]<a href=\"{link}\">Google Books</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

	# If we're in the imprint, are the sources represented correctly?
	# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
	elif special_file == "imprint":
		# Check for wrong grammar filled in from template
		nodes = dom.xpath("/html/body//a[starts-with(@href, 'https://books.google.com/') or starts-with(@href, 'https://www.google.com/books/')][(preceding-sibling::node()[1])[re:test(., 'the\\s+$')]]")
		if nodes:
			messages.append(LintMessage("s-016", "Incorrect [text]the[/] before Google Books link.", se.MESSAGE_TYPE_ERROR, filename, ["the " + node.to_string() for node in nodes]))

		# Check if we forgot to fill any variable slots
		missing_imprint_vars = [var for var in SE_VARIABLES if regex.search(fr"\b{var}\b", file_contents)]
		if missing_imprint_vars:
			messages.append(LintMessage("m-036", "Variable not replaced with value.", se.MESSAGE_TYPE_ERROR, filename, missing_imprint_vars))

		if ebook_flags["has_multiple_transcriptions"] and not dom.xpath("/html/body//a[contains(@href, '#transcriptions')]"):
			messages.append(LintMessage("m-074", "Multiple transcriptions found in metadata, but no link to [text]EBOOK_URL#transcriptions[/].", se.MESSAGE_TYPE_ERROR, filename))

		if ebook_flags["has_multiple_page_scans"] and not dom.xpath("/html/body//a[contains(@href, '#page-scans')]"):
			messages.append(LintMessage("m-075", "Multiple page scans found in metadata, but no link to [text]EBOOK_URL#page-scans[/].", se.MESSAGE_TYPE_ERROR, filename))

		# Check that the formula changed from the default if we added 'various sources'
		if ebook_flags["has_multiple_transcriptions"] or ebook_flags["has_multiple_page_scans"]:
			nodes = dom.xpath("/html/body//a[text() = 'various sources' and not(re:test(preceding-sibling::node()[1], '(digital scans|transcriptions) from\\s*$'))]")
			if nodes:
				messages.append(LintMessage("t-072", "[text]various sources[/] link not preceded by [text]from[/].", se.MESSAGE_TYPE_ERROR, filename))

		# Check for correctly named links. We can't merge this with the colophon check because the colophon breaks `the` with `<br/>`
		if not ebook_flags["has_multiple_transcriptions"] and not ebook_flags["has_other_sources"]:
			for link in source_links:
				if "gutenberg.org" in link and f"<a href=\"{link}\">Project Gutenberg</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: [xhtml]<a href=\"{link}\">Project Gutenberg</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

		if not ebook_flags["has_multiple_page_scans"] and not ebook_flags["has_other_sources"]:
			for link in source_links:
				if "hathitrust.org" in link and f"the <a href=\"{link}\">HathiTrust Digital Library</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: the [xhtml]<a href=\"{link}\">HathiTrust Digital Library</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

				if "archive.org" in link and f"the <a href=\"{link}\">Internet Archive</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: the [xhtml]<a href=\"{link}\">Internet Archive</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

				if ("books.google.com" in link or "www.google.com/books/" in link) and f"<a href=\"{link}\">Google Books</a>" not in file_contents:
					messages.append(LintMessage("m-037", f"Transcription/page scan source link not found. Expected: [xhtml]<a href=\"{link}\">Google Books</a>[/].", se.MESSAGE_TYPE_ERROR, filename))

	# Endnote checks
	elif special_file == "endnotes":
		# Do we have to replace Ibid.? Only match Ibid. if the endnote does not appear to cite any names.
		nodes = dom.xpath("/html/body//li[re:test(@epub:type, '\\bendnote\\b')]//abbr[re:test(., '\\b[Ii]bid\\b') and not(ancestor::li[1]//*[contains(@epub:type, 'se:name')])]")
		if nodes:
			messages.append(LintMessage("s-039", "[text]Ibid[/] in endnotes. “Ibid” means “The previous reference” which is meaningless with popup endnotes, and must be replaced by the actual thing [text]Ibid[/] refers to, unless it refers to text within the same endnote.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

		# Check that endnotes have their backlink in the last <p> element child of the <li>. This also highlights backlinks that are totally missing.
		nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')][./p[last()][not(a[contains(@epub:type, 'backlink')])] or not(./p[last()])]")
		if nodes:
			messages.append(LintMessage("s-056", "Last [xhtml]<p>[/] child of endnote missing backlink.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

		# Make sure the backlink points to the same note number as the parent endnote ID
		nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')]//a[contains(@epub:type, 'backlink')][not(re:match(@href, '\\-[0-9]+$')=re:match(ancestor::li/@id, '\\-[0-9]+$'))]")
		if nodes:
			messages.append(LintMessage("s-057", "Backlink noteref fragment identifier doesn’t match endnote number.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

		# Check that citations at the end of endnotes are in a <cite> element. If not typogrify will run the last space together with the em dash.
		# This tries to catch that, but limits the match to 20 chars so that we don't accidentally match a whole sentence that happens to be at the end of an endnote.
		nodes = dom.xpath(f"/html/body//li[contains(@epub:type, 'endnote')]/p[last()][re:test(., '\\.”?{se.WORD_JOINER}?—[A-Z].{{0,20}}\\s*↩$')]")
		if nodes:
			messages.append(LintMessage("s-064", "Endnote citation not wrapped in [xhtml]<cite>[/]. Em dashes go within [xhtml]<cite>[/] and it is preceded by one space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

		# Did we forget the endnote semantic on li elements?
		nodes = dom.xpath("/html/body/section/ol/li[not(re:test(@epub:type, '\\bendnote\\b'))]")
		if nodes:
			messages.append(LintMessage("s-099", "List item in endnotes missing [xhtml]endnote[/] semantic.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

		# Match backlink elements whose preceding node doesn't end with ' ', and is also not all whitespace
		nodes = dom.xpath("/html/body//a[@epub:type='backlink'][(preceding-sibling::node()[1])[not(re:test(., ' $')) and not(normalize-space(.)='')]]")
		if nodes:
			messages.append(LintMessage("t-027", "Endnote backlink not preceded by exactly one space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check LoI descriptions to see if they match associated figcaptions
	elif special_file == "loi":
		for node in dom.xpath("/html/body/nav[contains(@epub:type, 'loi')]//li//a"):
			figure_ref = node.get_attr("href").split("#")[1]
			chapter_ref = regex.findall(r"(.*?)#.*", node.get_attr("href"))[0]
			figcaption_text = ""
			loi_text = node.inner_text()
			file_dom = self.get_dom(self.content_path / "text" / chapter_ref)

			try:
				figure = file_dom.xpath(f"//*[@id={se.easy_xml.escape_xpath(figure_ref)}]")[0]
			except Exception:
				messages.append(LintMessage("s-040", f"[attr]#{figure_ref}[/] not found in file [path][link=file://{self.path / 'src/epub/text' / chapter_ref}]{chapter_ref}[/][/].", se.MESSAGE_TYPE_ERROR, filename))
				continue

			for child in figure.xpath("./*"):
				if child.tag == "img":
					figure_img_alt = child.get_attr("alt")

				if child.tag == "figcaption":
					figcaption_text = child.inner_text()

					# Replace tabs and newlines with a single space to better match figcaptions that contain <br/>
					figcaption_text = regex.sub(r"(\n|\t)", " ", figcaption_text)
					figcaption_text = regex.sub(r"[ ]+", " ", figcaption_text)

			if (figcaption_text != "" and loi_text != "" and figcaption_text != loi_text) and (figure_img_alt != "" and loi_text != "" and figure_img_alt != loi_text):
				messages.append(LintMessage("s-041", f"The [xhtml]<figcaption>[/] element of [attr]#{figure_ref}[/] does not match the text in its LoI entry.", se.MESSAGE_TYPE_WARNING, self.path / "src/epub/text" / chapter_ref))

	return messages

def _lint_xhtml_css_checks(filename: Path, dom: se.easy_xml.EasyXmlTree, local_css_path: Path) -> list:
	"""
	Process CSS checks on an .xhtml file

	INPUTS
	filename: The name of the file being checked
	dom: The dom tree of the file being checked
	local_css_path: The path to the local CSS file

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []

	# Do we have any elements that have specified border color?
	# `transparent` and `none` are allowed values for border-color
	if dom.xpath("/html/body//*[attribute::*[re:test(local-name(), 'data-css-border.+?-color') and text() != 'transparent' and text != 'none']]"):
		messages.append(LintMessage("c-004", "Don’t specify border colors, so that reading systems can adjust for night mode.", se.MESSAGE_TYPE_WARNING, local_css_path))

	# Check that footers have the expected styling
	# Footers may sometimes be aligned with text-align: center as well as text-align: right
	# We also ignore text-align on any footers whose only child is a postscript, which is typically left-aligned
	nodes = dom.xpath("/html/body//footer[not(@data-css-margin-top='1em') or (not(@data-css-text-align) and not(./*[contains(@epub:type, 'z3998:postscript') and not(following-sibling::*) and not(preceding-sibling::*) ]))]")
	if nodes:
		messages.append(LintMessage("c-010", "[xhtml]<footer>[/] missing [css]margin-top: 1em; text-align: <value>;[/]. [css]text-align[/] is usually set to [css]right[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for elements that have `text-align: center` but also `text-indent: 1em`
	nodes = dom.xpath("/html/body//*[@data-css-text-align='center' and @data-css-text-indent='1em']")
	if nodes:
		messages.append(LintMessage("c-011", "Element with [css]text-align: center;[/] but [css]text-indent[/] is [css]1em[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for sections that don't have header elements, and that do not have margin-top: 8em.
	# This tries to find the first <section> or <article> whose first child is <p>, and that doesn't
	# have any ancestor <section>s or <articles>s with heading content, and that doesn't have the correct top margin.
	# Ignore the titlepage, loi, and dedications as they typically have unique styling.
	nodes = dom.xpath("/html/body//*[name()='section' or name()='article'][1][./p[1][not(preceding-sibling::*)] and not(re:test(@epub:type, '(titlepage|loi|dedication)')) and not(ancestor::*/*[re:test(name(), '^(h[1-6]|header|hgroup)$')]) and not(@data-css-margin-top='20vh')]")
	if nodes:
		messages.append(LintMessage("c-012", "Sectioning element without heading content, and without [css]margin-top: 20vh;[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for padding and margin not in .5 increments, except for table headers/cells which usually need .25em increments
	nodes = dom.xpath("/html/body//*[not(re:test(name(), '^(h[1-6]|td|th)$'))][attribute::*[re:test(local-name(), 'data-css-(margin|padding)')][re:test(., '^[0-9]*\\.[^5]')]]")
	if nodes:
		messages.append(LintMessage("c-013", "Element with margin or padding not in increments of [css].5em[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <table> without set margins. We ignore tables that are for drama structuring, and tables that are ancestors of <blockquote> because <blockquote> has its own margin.
	# We also ignore tables whose preceding sibling sets a bottom margin that is not 0.
	nodes = dom.xpath("/html/body//table[not(./ancestor-or-self::*[contains(@epub:type, 'z3998:drama')]) and not(./ancestor::blockquote) and not(./preceding-sibling::*[1][@data-css-margin-bottom != '0']) and (not(@data-css-margin-top) or not(@data-css-margin-right) or not(@data-css-margin-bottom) or not(@data-css-margin-left))]")
	if nodes:
		messages.append(LintMessage("c-014", "[xhtml]<table>[/] element without explicit margins. Most tables need [css]margin: 1em;[/] or [css]margin: 1em auto 1em auto;[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for elements that follow salutations, but that don't have text-indent: 0;
	# We have to check both <p> elems that are salutations, and also <p> elems that have a first-child inline element that is a salutation, and that does not have following siblings that are senders/valedictions, as that might indicate a letter in a prose context
	nodes = dom.xpath("/html/body//*[(contains(@epub:type, 'z3998:salutation') or ./preceding-sibling::*[1][contains(@epub:type, 'z3998:salutation') or (name() != 'blockquote' and count(./node()[normalize-space(.)]) = 1 and ./*[contains(@epub:type, 'z3998:salutation')])] or ./*[1][contains(@epub:type, 'z3998:salutation') and not((./following-sibling::node()[1][self::text()]))]) and @data-css-text-indent != '0']")
	if nodes:
		messages.append(LintMessage("c-015", "Element after or containing [val]z3998:salutation[/] does not have [css]text-indent: 0;[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for block-level postscripts that don't have margin-top: 1em. Exclude postscripts that are the first child of blockquote or footer, since blockquotes/footers gives the desired margin.
	nodes = dom.xpath("/html/body//*[(name() = 'div' or name() = 'p') and contains(@epub:type, 'z3998:postscript') and not((./parent::blockquote or ./parent::footer) and count(./preceding-sibling::*) = 0) and @data-css-margin-top != '1em']")
	if nodes:
		messages.append(LintMessage("c-017", "Element with [val]z3998:postscript[/] semantic, but without [css]margin-top: 1em;[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <p> postscripts that don't have text-indent: 0.
	nodes = dom.xpath("/html/body//p[contains(@epub:type, 'z3998:postscript') and (not(@data-css-text-align) or @data-css-text-align = 'initial' or @data-css-text-align = 'left') and @data-css-text-indent != '0']")
	if nodes:
		messages.append(LintMessage("c-018", "Element with [val]z3998:postscript[/] semantic, but without [css]text-indent: 0;[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for signature semantic without small caps
	# Ignore signatures that are only capital letters
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:signature') and not(@data-css-font-variant = 'small-caps') and not(@data-css-font-style = 'italic') and not(re:test(., '^[A-Z\\.\\s]+$'))]")
	if nodes:
		messages.append(LintMessage("c-019", "Element with [val]z3998:signature[/] semantic, but without [css]font-variant: small-caps;[/] or [css]font-style: italic;[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <article>s or <section>s that occur more than once in a file, without page break CSS
	# Exclude the last element because we don't care if it breaks after the last one.
	nodes = dom.xpath("/html/body[count(./article) > 1 or count(./section) > 1]/*[(name() = 'article' or name() = 'section') and (not(@data-css-break-after) or @data-css-break-after != 'page') and not(position() = last())]")
	if nodes:
		messages.append(LintMessage("c-020", "Multiple [xhtml]<article>[/]s or [xhtml]<section>[/]s in file, but missing [css]break-after: page;[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	# Check for elements that are set in italics, and whose italic children don't have font-style: normal.
	nodes = dom.xpath("/html/body//*[@data-css-font-style='italic' and ./*[(name()='i' or name()='em') and @data-css-font-style='italic']]")
	if nodes:
		messages.append(LintMessage("c-021", "Element with [css]font-style: italic;[/], but child [xhtml]<i>[/] or [xhtml]<em>[/] does not have [css]font-style: normal;[/]. Hint: Italics within italics are typically set in Roman for contrast; if that’s not the case here, can [xhtml]<i>[/] be removed while still preserving italics and semantic inflection?", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for tables that appear to be summing/listing numbers, but that are missing font-variant-numeric styling
	nodes = dom.xpath("/html/body//table[count(.//td[not(following-sibling::*) and re:test(., '^[0-9]+$') and not(@data-css-font-variant-numeric='tabular-nums')]) >= 2]")
	if nodes:
		messages.append(LintMessage("c-026", "Table that appears to be listing numbers, but without [css]font-variant-numeric: tabular-nums;[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	return messages

def _lint_xhtml_metadata_checks(self, filename: Path, dom: se.easy_xml.EasyXmlTree) -> list:
	"""
	Process metadata checks on an .xhtml file

	INPUTS
	filename: The name of the file being checked
	dom: The dom of the file being checked
	self

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []

	# Check for missing MARC relators
	# Don't check the landmarks as that may introduce duplicate errors
	# Only check for top-level elements, to avoid intros in short stories or poems in compilation.
	if not dom.xpath("/html/body//nav[contains(@epub:type, 'landmarks')]"):
		if dom.xpath("/html/body/*[contains(@epub:type, 'introduction') and not(@data-parent)]") and not self.metadata_dom.xpath("/package/metadata/meta[(@property='role') and (text()='aui' or text()='win')]"):
			messages.append(LintMessage("m-030", "[val]introduction[/] semantic inflection found, but no MARC relator [val]aui[/] (Author of introduction, but not the chief author) or [val]win[/] (Writer of introduction).", se.MESSAGE_TYPE_WARNING, filename))

		if dom.xpath("/html/body/*[contains(@epub:type, 'preface') and not(@data-parent)]") and not self.metadata_dom.xpath("/package/metadata/meta[(@property='role') and text()='wpr']"):
			messages.append(LintMessage("m-031", "[val]preface[/] semantic inflection found, but no MARC relator [val]wpr[/] (Writer of preface).", se.MESSAGE_TYPE_WARNING, filename))

		if dom.xpath("/html/body/*[contains(@epub:type, 'afterword') and not(@data-parent)]") and not self.metadata_dom.xpath("/package/metadata/meta[(@property='role') and text()='aft']"):
			messages.append(LintMessage("m-032", "[val]afterword[/] semantic inflection found, but no MARC relator [val]aft[/] (Author of colophon, afterword, etc.).", se.MESSAGE_TYPE_WARNING, filename))

		if dom.xpath("/html/body/*[contains(@epub:type, 'endnotes') and not(@data-parent)]") and not self.metadata_dom.xpath("/package/metadata/meta[(@property='role') and text()='ann']"):
			messages.append(LintMessage("m-033", "[val]endnotes[/] semantic inflection found, but no MARC relator [val]ann[/] (Annotator).", se.MESSAGE_TYPE_WARNING, filename))

		if dom.xpath("/html/body/*[contains(@epub:type, 'loi') and not(@data-parent)]") and not self.metadata_dom.xpath("/package/metadata/meta[(@property='role') and text()='ill']"):
			messages.append(LintMessage("m-034", "[val]loi[/] semantic inflection found, but no MARC relator [val]ill[/] (Illustrator).", se.MESSAGE_TYPE_WARNING, filename))

	# Check that `Internet Archive` and `HathiTrust` are preceded by `the`. They might have an immediate preceding text node that ends in `the`, or they
	# might be preceded by a white space node, then a <br/>, then a text node ending in `the`.
	nodes = dom.xpath("/html/body//a[(re:test(text(), '[Hh]athi') and re:test(@href, '^https://[^\"]*?hathitrust.org')) or (re:test(text(), 'Internet Archive') and re:test(@href, 'https://[^\"]*?archive.org'))][(preceding-sibling::node()[2][not(self::br)] and preceding-sibling::node()[1][not(re:test(., '\\sthe $'))]) or (preceding-sibling::node()[2][self::br] and preceding-sibling::node()[3][not(re:test(., '\\sthe$'))]) ]")
	if nodes:
		messages.append(LintMessage("m-061", "Link must be preceded by [text]the[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	return messages

def _lint_xhtml_syntax_checks(self, filename: Path, dom: se.easy_xml.EasyXmlTree, file_contents: str, ebook_flags: dict, language: str, section_tree: List[EbookSection]) -> list:
	"""
	Process syntax checks on an .xhtml file

	INPUTS
	filename: The name of the file being checked
	dom: The dom tree of the file being checked
	file_contents: The contents of the file being checked
	ebook_flags: A dictionary containing several flags about an ebook
	language: The language identified in the metadata

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []

	# This block is useful for pretty-printing section_tree should we need to debug it in the future
	# def dump(item, char):
	#	print(f"{char} {item.section_id} ({item.depth}) {item.has_header}")
	#	for child in item.children:
	#		dump(child, f"	{char}")
	# for section in section_tree:
	#	dump(section, "")
	# exit()

	# Check for numeric entities
	matches = regex.findall(r"&#[0-9]+?;", file_contents)
	if matches:
		messages.append(LintMessage("s-001", "Illegal numeric entity (like [xhtml]&#913;[/]).", se.MESSAGE_TYPE_ERROR, filename))

	# Check nested <blockquote> elements, but only if it's the first child of another <blockquote>
	nodes = dom.xpath("/html/body//blockquote/*[1][name()='blockquote']")
	if nodes:
		messages.append(LintMessage("s-005", "Nested [xhtml]<blockquote>[/] element.", se.MESSAGE_TYPE_WARNING, filename))

	# Check to see if we've marked something as poetry or verse, but didn't include a first <span>
	# This xpath selects the p elements, whose parents are poem/verse, and whose first child is not a span
	nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')]/p[not(./*[name()='span' and position()=1])]")
	if nodes:
		matches = []
		for node in nodes:
			# Get the first line of the poem, if it's a text node, so that we can include it in the error messages.
			# If it's not a text node then just ignore it and add the error anyway.
			first_line = node.xpath("./descendant-or-self::text()[normalize-space(.)]", True)
			if first_line:
				match = first_line.strip()
				if match: # Make sure we don't append an empty string
					matches.append(match)

		messages.append(LintMessage("s-006", "Poem or verse [xhtml]<p>[/] (stanza) without [xhtml]<span>[/] (line) element.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for elements that don't have a direct block child
	# Allow white space and comments before the first child
	# Ignore children of the ToC and landmarks as they do not require p children
	nodes = dom.xpath("/html/body//*[(name()='blockquote' or name()='dd' or name()='header' or name()='li' or name()='footer') and not(./ancestor::*[contains(@epub:type, 'toc') or contains(@epub:type, 'landmarks')]) and (node()[normalize-space(.) and not(self::comment())])[1][not(name()='p' or name()='blockquote' or name()='div' or name()='table' or name()='header' or name()='ul' or name()='ol' or name() = 'section' or name()='footer' or name()='hgroup' or re:test(name(), '^h[0-6]'))]]")
	if nodes:
		messages.append(LintMessage("s-007", "Element requires at least one block-level child.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for block-level tags that end with <br/>
	nodes = dom.xpath("/html/body//*[self::p or self::blockquote or self::table or self::ol or self::ul or self::section or self::article][br[last()][not(following-sibling::text()[normalize-space()])][not(following-sibling::*)]]")
	if nodes:
		messages.append(LintMessage("s-008", "[xhtml]<br/>[/] element found before closing tag of block-level element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for hgroup elements with only one child
	nodes = dom.xpath("/html/body//hgroup[count(*)=1]")
	if nodes:
		messages.append(LintMessage("s-009", "[xhtml]<hgroup>[/] element with only one child.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for empty elements. Elements are empty if they have no children and no non-whitespace text
	# Use name() to check for MathML elements, because if the MathML namespace is not declared in a given file and we search by the m: namespace then this xpath will fail entirely.
	nodes = dom.xpath("/html/body//*[not(self::br) and not(self::hr) and not(self::img) and not(self::td) and not(self::th) and not(self::link) and not(self::col) and not(self::colgroup) and not(local-name()='none') and not(local-name()='mspace') and not(local-name()='mprescripts')][not(./*)][not(normalize-space())][not(./ancestor::*[local-name()='annotation-xml'])]")
	if nodes:
		messages.append(LintMessage("s-010", "Empty element. Use [xhtml]<hr/>[/] for thematic breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <section> and <article> without ID attribute
	# Ignore items within <blockquote> as that is a new sectioning root and we don't need to address
	# sectioning elements in quotations.
	nodes = dom.xpath("/html/body//*[self::section or self::article][not(@id)][not(ancestor::blockquote)]")
	if nodes:
		messages.append(LintMessage("s-011", "Element without [attr]id[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for <pre> tags
	if dom.xpath("/html/body//pre"):
		messages.append(LintMessage("s-013", "Illegal [xhtml]<pre>[/] element.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for <br/> after block-level elements
	nodes = dom.xpath("/html/body//*[self::p or self::blockquote or self::table or self::ol or self::ul or self::section or self::article][following-sibling::br]")
	if nodes:
		messages.append(LintMessage("s-014", "[xhtml]<br/>[/] after block-level element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for <hr> tags before the end of a section, which is a common PG artifact
	if dom.xpath("/html/body//hr[count(following-sibling::*)=0]"):
		messages.append(LintMessage("s-012", "Illegal [xhtml]<hr/>[/] as last child.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for hgroup elements with a subtitle but no title
	nodes = dom.xpath("/html/body//hgroup[./*[contains(@epub:type, 'subtitle')] and not(./*[contains(concat(' ', @epub:type, ' '), ' title ')])]")
	if nodes:
		messages.append(LintMessage("s-015", "Element has [val]subtitle[/] semantic, but without a sibling having a [val]title[/] semantic.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for deprecated MathML elements
	# Note we dont select directly on element name, because we want to ignore any namespaces that may (or may not) be defined
	nodes = dom.xpath("/html/body//*[local-name()='mfenced']")
	if nodes:
		messages.append(LintMessage("s-017", "[xhtml]<m:mfenced>[/] is deprecated in the MathML spec. Use [xhtml]<m:mrow><m:mo fence=\"true\">(</m:mo>...<m:mo fence=\"true\">)</m:mo></m:mrow>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for <figure> tags without id attributes
	nodes = dom.xpath("/html/body//img[@id]")
	if nodes:
		messages.append(LintMessage("s-018", "[xhtml]<img>[/] element with [attr]id[/] attribute. [attr]id[/] attributes go on parent [xhtml]<figure>[/] elements. Hint: Images that are inline (i.e. that do not have parent [xhtml]<figure>[/]s do not have [attr]id[/] attributes.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for IDs on <h#> tags
	nodes = dom.xpath("/html/body//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6][@id]")
	if nodes:
		messages.append(LintMessage("s-019", "[xhtml]<h#>[/] element with [attr]id[/] attribute. [xhtml]<h#>[/] elements should be wrapped in [xhtml]<section>[/] elements, which should hold the [attr]id[/] attribute.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	# Check for legal cases that aren't italicized
	# We can't use this because v. appears as short for "volume", and we may also have sporting events without italics.
	#nodes = dom.xpath("/html/body//abbr[text()='v.' or text()='versus'][not(parent::i)]")
	#if nodes:
	#	messages.append(LintMessage("t-xxx", "Legal case without parent [xhtml]<i>[/].", se.MESSAGE_TYPE_WARNING, filename, {f"{node.to_string()}." for node in nodes}))

	# Only do this check if there's one <h#> or one <hgroup> tag. If there's more than one, then the xhtml file probably requires an overarching title
	# We merge two xpaths here because <h#>/<hgroup> can be either a direct child of <section>, or it could be nested in <header>
	if len(dom.xpath("/html/body/*[name()='section' or name()='article']/*[re:test(name(), '^h[1-6]$') or name()='hgroup'] | /html/body/*[name()='section' or name()='article']/header/*[re:test(name(), '^h[1-6]$') or name()='hgroup']"))==1:
		title = se.formatting.generate_title(dom)

		if not dom.xpath(f"/html/head/title[text()={se.easy_xml.escape_xpath(title.replace('&amp;', '&'))}]"):
			messages.append(LintMessage("s-021", f"Unexpected value for [xhtml]<title>[/] element. Expected: [text]{title}[/]. (Beware hidden Unicode characters!)", se.MESSAGE_TYPE_ERROR, filename))

	# Check to see if <h#> tags are correctly titlecased
	# Ignore <h#> tags with an `xml:lang` attribute, as other languages have different titlecasing rules
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$') or (name() = 'p' and parent::hgroup)][not(contains(@epub:type, 'z3998:roman')) and not(@xml:lang)]")
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

	# Check for header elements that are entirely non-English
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][./i[@xml:lang][count(preceding-sibling::node()[normalize-space(.)]) + count(following-sibling::node()[normalize-space(.)])=0]]")
	if nodes:
		messages.append(LintMessage("s-024", "Header elements that are entirely non-English should not be set in italics. Instead, the [xhtml]<h#>[/] element has the [attr]xml:lang[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for z3998:roman elements with invalid values. Roman numerals can occasionally end in `j` as an alias for ending `i`. See _The Worm Ouroboros_.
	# We also allow the numeral to end in a digit, because that might be an endnote. For example `<h2 epub:type="ordinal z3998:roman">II<a href="..." epub:type="noteref">3</a></h2>`
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:roman') and not(re:test(normalize-space(.), '^[ivxlcdmIVXLCDM]+j?[0-9]*?$'))]")
	if nodes:
		messages.append(LintMessage("s-026", "Invalid Roman numeral.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <h#> elements that are higher or lower than their expected level based on how deep they are in <section>s
	# or <article>s. Exclude <nav> in the ToC.
	# Get all h# elements not preceded by other h# elements (this includes the 1st item of an hgroup but not the next items)
	# Exclude the ToC and landmarks
	invalid_headers = []
	invalid_parent_ids = []
	for heading in dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$') and not(./preceding-sibling::*[re:test(name(), '^h[1-6]$')]) and not(./ancestor::*[re:test(@epub:type, '\\b(toc|landmarks)\\b')])]"):
		# Get the IDs of the direct parent section
		parent_section = heading.xpath("./ancestor::*[@id and re:test(name(), '^(section|article|nav)$')][1]")

		if parent_section:
			section = _find_ebook_section(parent_section[0].get_attr("id"), section_tree)

			if not section:
				# We can accidentally raise s-029 if the file isn't in the spine. This is technically correct, but s-029 is a
				# misleading message in that case, and f-007 will also be raised, which is the correct message.
				if filename in self.spine_file_paths:
					invalid_parent_ids.append(parent_section[0].to_tag_string())
			else:
				if str(section.depth) != heading.tag[1:2]:
					invalid_headers.append(heading.to_string())

	if invalid_parent_ids:
		messages.append(LintMessage("s-029", "Section with [attr]data-parent[/] attribute, but no section having that [attr]id[/] in ebook.", se.MESSAGE_TYPE_ERROR, filename, invalid_parent_ids))
	if invalid_headers:
		messages.append(LintMessage("s-085", "[xhtml]<h#>[/] element found in a [xhtml]<section>[/] or a [xhtml]<article>[/] at an unexpected level. Hint: Headings not in the title page start at [xhtml]<h2>[/]. If this work has parts, should this header be [xhtml]<h3>[/] or higher?", se.MESSAGE_TYPE_ERROR, filename, invalid_headers))

	# Check for a common typo
	if "z3998:nonfiction" in file_contents:
		messages.append(LintMessage("s-030", "[val]z3998:nonfiction[/] should be [val]z3998:non-fiction[/].", se.MESSAGE_TYPE_ERROR, filename))

	# Run some checks on epub:type values
	incorrect_attrs = set()
	unnecessary_z3998_attrs = set()
	duplicate_attrs = []

	for node in dom.xpath("//*[@epub:type]"):
		attrs = set()

		for val in regex.split(r"\s+", node.get_attr("epub:type")):
			if val in attrs:
				duplicate_attrs.append(node.to_tag_string())
			else:
				attrs.add(val)

			if val.startswith("z3998:"):
				bare_val = val.replace("z3998:", "")
				if bare_val not in Z3998_SEMANTIC_VOCABULARY:
					incorrect_attrs.add(val)

				elif bare_val in EPUB_SEMANTIC_VOCABULARY:
					unnecessary_z3998_attrs.add((val, bare_val))

			elif val.startswith("se:"):
				bare_val = val.replace("se:", "")
				if bare_val not in SE_SEMANTIC_VOCABULARY:
					incorrect_attrs.add(val)

			else:
				# Regular epub vocabulary
				if val not in EPUB_SEMANTIC_VOCABULARY:
					incorrect_attrs.add(val)

	if duplicate_attrs:
		messages.append(LintMessage("s-031", "Duplicate value in [attr]epub:type[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, duplicate_attrs))
	if incorrect_attrs:
		messages.append(LintMessage("s-032", "Invalid value for [attr]epub:type[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, incorrect_attrs))
	if unnecessary_z3998_attrs:
		messages.append(LintMessage("s-034", "Semantic used from the z3998 vocabulary, but the same semantic exists in the EPUB vocabulary.", se.MESSAGE_TYPE_ERROR, filename, [attr for (attr, bare_attr) in unnecessary_z3998_attrs]))

	# Check if language tags in individual files match the language in the metadata file
	if filename.name not in IGNORED_FILENAMES:
		file_language = dom.xpath("/html/@xml:lang", True)
		if language != file_language:
			messages.append(LintMessage("s-033", f"File language is [val]{file_language}[/], but [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/] language is [val]{language}[/].", se.MESSAGE_TYPE_WARNING, filename))

	# Check for endnotes
	nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')]/p[not(preceding-sibling::*)]/cite[not(preceding-sibling::node()[normalize-space(.)]) and (following-sibling::node()[normalize-space(.)])[1][contains(@epub:type, 'backlink')]]")
	if nodes:
		messages.append(LintMessage("s-035", "Endnote containing only [xhtml]<cite>[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for wrong semantics in frontmatter/backmatter
	if dom.xpath("/html/body/section[not(@data-parent) and re:test(@epub:type, '\\b(dedication|introduction|preface|foreword|preamble|titlepage|halftitlepage|imprint|epigraph|acknowledgements)\\b') and not(ancestor-or-self::*[contains(@epub:type, 'frontmatter')])]"):
		messages.append(LintMessage("s-036", "No [val]frontmatter[/] semantic inflection for what looks like a frontmatter file.", se.MESSAGE_TYPE_WARNING, filename))

	if dom.xpath("/html/body/section[not(@data-parent) and re:test(@epub:type, '\\b(endnotes|loi|afterword|appendix|colophon|copyright\\-page|lot)\\b') and not(ancestor-or-self::*[contains(@epub:type, 'backmatter')])]"):
		messages.append(LintMessage("s-037", "No [val]backmatter[/] semantic inflection for what looks like a backmatter file.", se.MESSAGE_TYPE_WARNING, filename))

	# Check for leftover asterisms. Asterisms are sequences of any of these chars: * . • -⁠ —
	nodes = dom.xpath("/html/body//*[self::p or self::div][re:test(., '^\\s*[\\*\\.•\\-⁠—]\\s*([\\*\\.•\\-⁠—]\\s*)+$')]")
	if nodes:
		messages.append(LintMessage("s-038", "Illegal asterism. Section/scene breaks must be defined by an [xhtml]<hr/>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <table> element without a <tbody> child
	if dom.xpath("/html/body//table[not(tbody)]"):
		messages.append(LintMessage("s-042", "[xhtml]<table>[/] element without [xhtml]<tbody>[/] child.", se.MESSAGE_TYPE_ERROR, filename))

	# Check that short stories are on an <article> element
	nodes = dom.xpath("/html/body/section[contains(@epub:type, 'se:short-story') or contains(@epub:type, 'se:novella')]")
	if nodes:
		messages.append(LintMessage("s-043", "[val]se:short-story[/] semantic on element that is not [xhtml]<article>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for poetry/verse without a descendent <p> element.
	# Skip the ToC landmarks because it may have poem/verse semantic children.
	nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')][not(descendant::p)][not(ancestor::nav[contains(@epub:type, 'landmarks')])]")
	if nodes:
		messages.append(LintMessage("s-044", "Element with poem or verse semantic, without descendant [xhtml]<p>[/] (stanza) element.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	# Check for <abbr> elements that have two or more letters/periods, that don't have a semantic epub:type
	# SS. is the French abbreviation for "Saints"
	nodes = dom.xpath("/html/body//abbr[not(@epub:type)][text() != 'U.S.' and text() != 'SS.'][re:test(., '([A-Z]\\.?){2,}')]")
	filtered_nodes = []
	for node in nodes:
		add_node = True

		if node.text in INITIALISM_EXCEPTIONS:
			add_node = False
		elif node.get_attr("class"):
			for attr_value in node.get_attr("class").split():
				if attr_value in IGNORED_CLASSES:
					add_node = False
					break
		elif node.text in ("A.M.", "P.M.") and node.xpath("./preceding-sibling::node()[re:test(., '[0-9]\\s$')]"):
			# Ignore instances of capitalized times, usually in titles. For example:
			# `From 10:20 <abbr>P.M.</abbr> to 10:47 <abbr>P.M.</abbr>` in a chapter title.
			# We have to test for a preceding number because `<abbr>P.M.</abbr>` in other contexts may mean `Prime Minister`
			add_node = False

		if add_node:
			filtered_nodes.append(node)

	if filtered_nodes:
		messages.append(LintMessage("s-045", "[xhtml]<abbr>[/] element without semantic inflection like [class]z3998:personal-name[/] or [class]z3998:initialism[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in filtered_nodes]))

	# Check for <p> elems that has some element children, which are only <span> and <br> children, but the parent doesn't have poem/verse semantics.
	# Ignore spans that have a class, but not if the class is an i# class (for poetry indentation)
	nodes = dom.xpath("/html/body//p[not(./text()[normalize-space(.)])][*][not(ancestor::*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')])][not(*[not(self::span) and not(self::br)])][ (not(span[@epub:type]) and not(span[@class]) ) or span[re:test(@class, '\\bi[0-9]\\b')]]")
	if nodes:
		messages.append(LintMessage("s-046", "[xhtml]<p>[/] element containing only [xhtml]<span>[/] and [xhtml]<br>[/] elements, but its parent doesn’t have the [val]z3998:poem[/], [val]z3998:verse[/], [val]z3998:song[/], [val]z3998:hymn[/], or [val]z3998:lyrics[/] semantic. Multi-line clauses that are not verse don’t require [xhtml]<span>[/]s.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# For this series of selections, we select spans that are direct children of p, because sometimes a line of poetry may have a nested span.
	nodes = dom.xpath("/html/body/*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')]/descendant-or-self::*/p/span/following-sibling::*[contains(@epub:type, 'noteref') and name()='a' and position()=1]")
	if nodes:
		messages.append(LintMessage("s-047", "[val]noteref[/] as a direct child of element with poem or verse semantic. [val]noteref[/]s should be in their parent [xhtml]<span>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for incorrectly applied se:name semantic
	nodes = dom.xpath("/html/body//*[self::p or self::blockquote][contains(@epub:type, 'se:name.')]")
	if nodes:
		messages.append(LintMessage("s-048", "[val]se:name[/] semantic on block element. [val]se:name[/] indicates the contents is the name of something.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	# Check for <header> elements with only h# child nodes
	nodes = dom.xpath("/html/body//header[./*[re:test(name(), 'h[1-6]') and (count(preceding-sibling::*) + count(following-sibling::*)=0)]]")
	if nodes:
		messages.append(LintMessage("s-049", "[xhtml]<header>[/] element whose only child is an [xhtml]<h#>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <span>s that only exist to apply epub:type
	nodes = dom.xpath("/html/body//*[span[@epub:type][count(preceding-sibling::node()[normalize-space(.)]) + count(following-sibling::node()[normalize-space(.)])=0]]")
	if nodes:
		messages.append(LintMessage("s-050", "[xhtml]<span>[/] element appears to exist only to apply [attr]epub:type[/]. [attr]epub:type[/] should go on the parent element instead, without a [xhtml]<span>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for language tags misusing the unk lang code
	nodes = dom.xpath("//*[@xml:lang='unk']")
	if nodes:
		messages.append(LintMessage("s-051", "Element with [xhtml]xml:lang=\"unk\"[/] should be [xhtml]xml:lang=\"und\"[/] (undefined).", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for title attrs on abbr elements
	nodes = dom.xpath("/html/body//abbr[@title]")
	if nodes:
		messages.append(LintMessage("s-052", "[xhtml]<abbr>[/] element with illegal [attr]title[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	nodes = dom.xpath("/html/body//blockquote//p[parent::*[name()='footer'] or parent::*[name()='blockquote']]//cite") # Sometimes the <p> may be in a <footer>
	if nodes:
		messages.append(LintMessage("s-054", "[xhtml]<cite>[/] as child of [xhtml]<p>[/] in [xhtml]<blockquote>[/]. [xhtml]<cite>[/] should be the direct child of [xhtml]<blockquote>[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <th> element without a <thead> ancestor. However, <th scope="...">	and <th/> are allowed, for use in tables with headers in the middle of tables (url:https://standardebooks.org/ebooks/dorothy-day/the-eleventh-virgin) and vertical table headers
	# (https://standardebooks.org/ebooks/charles-babbage/passages-from-the-life-of-a-philosopher)
	if dom.xpath("/html/body//table//th[not(ancestor::thead)][not(@scope)][not(count(node())=0)]"):
		messages.append(LintMessage("s-055", "[xhtml]<th>[/] element not in [xhtml]<thead>[/] ancestor. Note: [xhtml]<th>[/] elements used as mid-table headings or horizontal row headings require the [attr]scope[/] attribute.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for z3998:stage-direction on elements that are not <i>
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'z3998:stage-direction') and name() !='i' and name() !='abbr' and name() !='p']")
	if nodes:
		messages.append(LintMessage("s-058", "[attr]z3998:stage-direction[/] semantic only allowed on [xhtml]<i>[/], [xhtml]<abbr>[/], and [xhtml]<p>[/] elements.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check that internal links don't begin with ../
	nodes = dom.xpath("/html/body//a[re:test(@href, '^\\.\\./text/')]")
	if nodes:
		messages.append(LintMessage("s-059", "Internal link beginning with [val]../text/[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for italics on things that shouldn't be italics
	nodes = dom.xpath("/html/body//i[contains(@epub:type, 'se:name.music.song') or contains(@epub:type, 'se:name.publication.short-story') or contains(@epub:type, 'se:name.publication.essay')]")
	if nodes:
		messages.append(LintMessage("s-060", "Italics on name that requires quotes instead.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for h# tags followed by header content, that are not children of <header>.
	# Only match if there is a following <p>, because we could have the case where there's an epigraph after a division title.
	nodes = dom.xpath("/html/body//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6][following-sibling::*[contains(@epub:type, 'epigraph') or contains(@epub:type, 'bridgehead')]][following-sibling::p][not(parent::header)]")
	if nodes:
		messages.append(LintMessage("s-061", "Title and following header content not in a [xhtml]<header>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <dt> elements without exactly one <dfn> child, but only in glossaries
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'glossary')]//dt[not(count(./dfn)=1)]")
	if nodes:
		messages.append(LintMessage("s-062", "[xhtml]<dt>[/] element in a glossary without exactly one [xhtml]<dfn>[/] child.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check that `z3998:persona` is only on <b> or <td>. We use the contact() xpath function so we don't catch `z3998:personal-name`
	nodes = dom.xpath("/html/body//*[contains(concat(' ', @epub:type, ' '), ' z3998:persona ') and not(self::b or self::td)]")
	if nodes:
		messages.append(LintMessage("s-063", "[val]z3998:persona[/] semantic on element that is not a [xhtml]<b>[/] or [xhtml]<td>[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for fulltitle semantic on a header not in the half title
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'fulltitle') and name()!='h2' and name()!='hgroup' and not(ancestor::*[contains(@epub:type, 'halftitlepage')])]")
	if nodes:
		messages.append(LintMessage("s-065", "[val]fulltitle[/] semantic on element that is not in the half title.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for header elements that have a label, but are missing the label semantic
	# Find h# nodes whose first child is a text node matching a label type, and where that text node's next sibling is a semantic roman numeral
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][./node()[1][self::text() and not(./*) and re:test(normalize-space(.), '^(Part|Book|Volume|Section|Act|Scene)$') and following-sibling::*[1][contains(@epub:type, 'z3998:roman')]]]")
	if nodes:
		messages.append(LintMessage("s-066", "Header element missing [val]label[/] semantic.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for header elements that have a label semantic, but are missing an ordinal sibling
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][./span[contains(@epub:type, 'label')]][not(./span[contains(@epub:type, 'ordinal')])]")
	if nodes:
		messages.append(LintMessage("s-067", "Header element with a [val]label[/] semantic child, but without an [val]ordinal[/] semantic child.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for header elements with a roman semantic but without an ordinal semantic
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][contains(@epub:type, 'z3998:roman') and not(contains(@epub:type, 'ordinal'))]")
	if nodes:
		messages.append(LintMessage("s-068", "Header element missing [val]ordinal[/] semantic.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for body element without child section or article. Ignore the ToC because it has a unique structure
	nodes = dom.xpath("/html/body[not(./*[name()='section' or name()='article' or (name()='nav' and re:test(@epub:type, '\\b(toc|loi)\\b'))])]")
	if nodes:
		messages.append(LintMessage("s-069", "[xhtml]<body>[/] element missing direct child [xhtml]<section>[/] or [xhtml]<article>[/] element.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for h# without semantics; h# that have child elements (which likely have the correct semantics) are OK
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][not(@epub:type)][not(./*[not(name()='a' and contains(@epub:type, 'noteref'))])]")
	if nodes:
		messages.append(LintMessage("s-070", "[xhtml]<h#>[/] element without semantic inflection.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for sectioning elements with more than one heading element
	nodes = dom.xpath("/html/body//*[name()='article' or name()='section'][count(./*[name()='header' or name()='hgroup' or re:test(name(), '^h[1-6]$')]) > 1]")
	if nodes:
		messages.append(LintMessage("s-071", "Sectioning element with more than one heading element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for some elements that only have a <span> child (including text inline to the parent).
	# But, exclude such elements that are <p> elements that have poetry-type parents.
	nodes = dom.xpath("/html/body//*[name() !='p' and not(ancestor-or-self::*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn|lyrics)')])][./span[count(preceding-sibling::node()[normalize-space(.)]) + count(following-sibling::node()[normalize-space(.)])=0]]")
	if nodes:
		messages.append(LintMessage("s-072", "Element with single [xhtml]<span>[/] child. [xhtml]<span>[/] should be removed and its attributes promoted to the parent element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for header elements that are missing both label and ordinal semantics
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$')][not(./*) and re:test(normalize-space(.), '^(Part|Book|Volume|Section|Act|Scene)\\s+[ixvIXVmcd]+$')]")
	if nodes:
		messages.append(LintMessage("s-073", "Header element that requires [val]label[/] and [val]ordinal[/] semantic children.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for table headers that don't have content, which is an accessibility issue.
	# Note that @aria-label and @title should (apparently) not be used for table headers
	nodes = dom.xpath("/html/body//th[not(text())]")
	if nodes:
		messages.append(LintMessage("s-074", "[xhtml]<th>[/] element with no text content should be a [xhtml]<td>[/] element instead.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for incorrect children of <body>
	nodes = dom.xpath("/html/body/*[name() != 'section' and name() != 'article' and name() != 'nav']")
	if nodes:
		messages.append(LintMessage("s-075", "[xhtml]<body>[/] element with direct child that is not [xhtml]<section>[/], [xhtml]<article>[/], or [xhtml]<nav>[/].", se.MESSAGE_TYPE_ERROR, filename))

	# Check for lang="" instead of xml:lang=""
	nodes = dom.xpath("/html/body//*[@lang]")
	if nodes:
		messages.append(LintMessage("s-076", "[attr]lang[/] attribute used instead of [attr]xml:lang[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for <header> preceded by non-sectioning elements
	nodes = dom.xpath("/html/body//header[./preceding-sibling::*[not(re:test(name(), '^(section|div|article)$'))]]")
	if nodes:
		messages.append(LintMessage("s-077", "[xhtml]<header>[/] element preceded by non-sectioning element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <footer> followed by non-sectioning elements
	nodes = dom.xpath("/html/body//footer[./following-sibling::*[not(re:test(name(), '^(section|div|article)$'))]]")
	if nodes:
		messages.append(LintMessage("s-078", "[xhtml]<footer>[/] element followed by non-sectioning element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for elements with no children and only white space contents
	nodes = dom.xpath("/html/body//*[not(./*) and re:test(., '^\\s+$')]")
	if nodes:
		messages.append(LintMessage("s-079", "Element containing only white space.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for a play <td> that contains both inline text and block-level elements.
	# Note that we check any child of <html> because often <body> has the drama semantic.
	nodes = dom.xpath("/html//*[contains(@epub:type, 'z3998:drama')]//td[./text()[normalize-space(.)] and ./*[name() = 'p' or name() = 'blockquote' or name() = 'div']]")
	if nodes:
		messages.append(LintMessage("s-080", "[xhtml]<td>[/] in drama containing both inline text and a block-level element. All children should either be only text, or only block-level elements.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <p> tags that follow figure, blockquote, or table, and start with a lowercase letter, but that don't have the `continued` class. Exclude matches whose first child is <cite>, so we don't match things like <p><cite>—Editor</cite>
	nodes = dom.xpath("/html/body//p[preceding-sibling::*[1][name() = 'figure' or name() = 'blockquote' or name() = 'table'] and re:test(., '^([a-z]|—|…)') and not(contains(@class, 'continued')) and not(./*[1][self::cite])]")
	if nodes:
		messages.append(LintMessage("s-081", "[xhtml]<p>[/] preceded by [xhtml]<figure>[/], [xhtml]<blockquote>[/xhtml], or [xhtml]<table>[/], but without [val]continued[/] class.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for language tags transliterated into Latin script but missing `-Latn` suffix
	nodes = dom.xpath("/html/body//*[re:test(@xml:lang, '^(he|ru|el|zh|bn|hi|sa|uk|yi|grc)$') and re:test(., '[a-zA-Z]')]")
	if nodes:
		messages.append(LintMessage("s-082", "Element containing Latin script for a non-Latin-script language, but its [attr]xml:lang[/] attribute value is missing the [val]-Latn[/] language tag suffix. Hint: For example Russian transliterated into Latin script would be [val]ru-Latn[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for persona <td>s that have child <p> elements
	nodes = dom.xpath("/html/body//td[contains(@epub:type, 'z3998:persona') and ./p]")
	if nodes:
		messages.append(LintMessage("s-083", "[xhtml]<td epub:type=\"z3998:persona\">[/] element with child [xhtml]<p>[/] element.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for incorrect semantics on some common publications
	nodes = dom.xpath("/html/body//i[@epub:type='se:name.publication.book' and re:test(., '^(The )?(Iliad|Odyssey|Aeneid|Metamorphoses|Beowulf|Divine Comedy|Paradise Lost)$')]")
	if nodes:
		messages.append(LintMessage("s-084", "Poem has incorrect semantics.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for `Op. Cit.` in endnotes. `Op. Cit.` means "the previous reference" which doesn't make sense
	# in popup endnotes. But, if the endnote has a book reference, then allow it as it might be referring to that.
	nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote') and (re:test(., '(Loc\\.|Op\\.) Cit\\.', 'i') or re:test(., '\\bl\\.c\\.\\b', 'i')) and not(.//*[contains(@epub:type, 'se:name.publication')])]")
	if nodes:
		messages.append(LintMessage("s-086", "[text]Op. Cit.[/] or [text]Loc. Cit.[/] in endnote. Hint: [text]Op. Cit.[/] and [text]Loc. Cit.[/] mean [text]the previous reference[/], which usually doesn’t make sense in a popup endnote. Such references should be expanded.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	# Check for half title pages missing subtitles
	if ebook_flags["has_subtitle"]:
		# Make sure we exclude <a> because that appears in the ToC landmarks
		nodes = dom.xpath("/html/body//*[name()!='a' and contains(@epub:type, 'halftitlepage') and not(.//*[contains(@epub:type, 'subtitle')])]")
		if nodes:
			messages.append(LintMessage("s-087", "Subtitle in metadata, but no subtitle in the half title page.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	else:
		# Make sure we exclude <a> because that appears in the ToC landmarks
		nodes = dom.xpath("/html/body//*[name()!='a' and contains(@epub:type, 'halftitlepage') and .//*[contains(@epub:type, 'subtitle')]]")
		if nodes:
			messages.append(LintMessage("s-088", "Subtitle in half title page, but no subtitle in metadata.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for MathML without alttext
	nodes = dom.xpath("/html/body//m:math[not(@alttext)]")
	if nodes:
		messages.append(LintMessage("s-089", "MathML missing [attr]alttext[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for MathML, and no MathML / describedMath accessibilityFeature
	nodes = dom.xpath("/html/body//m:math")
	if nodes and len(self.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'describedMath']")) == 0:
		messages.append(LintMessage("m-077", "MathML found in ebook, but no [attr]schema:accessibilityFeature[/] properties set to [val]MathML[/] and [val]describedMath[/] in metadata.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for common errors in language tags
	# `gr` is often used instead of `el`, `sp` instead of `es`, and `ge` instead of `de` (`ge` is the Georgian geographic region subtag but not a language subtag itself)
	nodes = dom.xpath("//*[re:test(@xml:lang, '^(gr|sp|ge)$')]")
	if nodes:
		messages.append(LintMessage("s-090", "Invalid language tag.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for <span> in poetry not followed by <br/>. Ignore spans that are roman as they might be present in poem headers, or spans with xml:lang.
	nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn)')]//p/span[not(@epub:type='z3998:roman') and not(@xml:lang) and following-sibling::*[1][name()='span']]")
	if nodes:
		messages.append(LintMessage("s-091", "[xhtml]<span>[/] not followed by [xhtml]<br/>[/] in poetry.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for nested `<abbr>` elements
	nodes = dom.xpath("/html/body//abbr[./abbr]")
	if nodes:
		messages.append(LintMessage("s-093", "Nested [xhtml]<abbr>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for language tags transliterated into Latin script with incorrect `-latn` suffix (lowercase l)
	nodes = dom.xpath("/html/body//*[re:test(@xml:lang, '-latn')]")
	if nodes:
		messages.append(LintMessage("s-094", "Element has an [attr]xml:lang[/] attribute that incorrectly contains [val]-latn[/] instead of [val]-Latn[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for poetry/verse that has an hgroup but which does not have the correct text alignment
	nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:(hymn|poem|song|verse)')]//hgroup/p[@data-css-text-align != 'center']")
	if nodes:
		messages.append(LintMessage("s-095", "[xhtml]<p>[/] child of [xhtml]<hgroup>[/] in poetry/verse does not have [css]text-align: center;[/].", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check that half titles without subtitles have the fulltitle semantic
	nodes = dom.xpath("/html/body//*[name()!='a' and contains(@epub:type, 'halftitlepage')]/*[re:test(name(), '^h[1-6]$') and not(contains(@epub:type, 'fulltitle'))]")
	if nodes:
		messages.append(LintMessage("s-096", "Heading element in half title page missing the [val]fulltitle[/] semantic.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for missing href attributes, sometimes a leftover from PG transcriptions
	nodes = dom.xpath("/html/body//a[not(@href)]")
	if nodes:
		messages.append(LintMessage("s-097", "[xhtml]a[/] element without [attr]href[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <headers>s with only one child
	nodes = dom.xpath("/html/body/*[name() = 'section' or name() = 'article']/header[./*[not(name() = 'p') and not(preceding-sibling::* or following-sibling::*)]]")
	if nodes:
		messages.append(LintMessage("s-098", "[xhtml]<header>[/] element with only one child.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for @lang attributes
	nodes = dom.xpath("//*[@lang]")
	if nodes:
		messages.append(LintMessage("s-102", "[attr]lang[/] attribute detected. Hint: Use [attr]xml:lang[/] instead.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for common missing roman semantics for “I”
	regent_regex = r"(?:Charles|Edward|George|Henry|James|William) I\b"
	matches = regex.findall(fr"King {regent_regex}", file_contents) + regex.findall(fr"{regent_regex}’s", file_contents)
	if matches:
		messages.append(LintMessage("s-103", "Probable missing semantics for a roman I numeral.", se.MESSAGE_TYPE_WARNING, filename, matches))

	return messages

def _lint_xhtml_typography_checks(filename: Path, dom: se.easy_xml.EasyXmlTree, file_contents: str, special_file: Optional[str], ebook_flags: dict, missing_files: list, self) -> tuple:
	"""
	Process typography checks on an .xhtml file

	INPUTS
	filename: The name of the file being checked
	dom: The dom tree of the file being checked
	file_contents: The contents of the file being checked
	special_file: A string containing the type of special file the current file is, if any
	ebook_flags: A dictionary containing several flags about an ebook
	missing_files: A list of missing files
	self

	OUTPUTS
	tuple
	"""

	messages = []

	# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
	matches = regex.findall(fr"[\p{{Letter}}]+”[,\.](?!{se.WORD_JOINER} {se.WORD_JOINER}…)", file_contents)
	if matches:
		messages.append(LintMessage("t-002", "Comma or period outside of double quote. Generally punctuation goes within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for ldquo not correctly closed
	# Ignore closing paragraphs, line breaks, and closing cells in case ldquo means "ditto mark"
	matches = regex.findall(r"“[^‘”]+?“", file_contents)
	matches = [match for match in matches if "</p" not in match and "<br/>" not in match and "</td>" not in match]
	# xpath to check for opening quote in p, without a next child p that starts with an opening quote or an opening bracket (for editorial insertions within paragraphs of quotation); or that consists of only an ellipses (like an elided part of a longer quotation)
	# Matching <p>s can't have a poem/verse ancestor as formatting is often special for those.
	matches = matches + [regex.findall(r"“[^”]+</p>", node.to_string())[0] for node in dom.xpath("/html/body//p[re:test(., '“[^‘”]+$')][not(ancestor::*[re:test(@epub:type, 'z3998:(verse|poem|song|hymn|lyrics)')])][(following-sibling::*[1])[name()='p'][not(re:test(normalize-space(.), '^[“\\[]') or re:test(normalize-space(.), '^…$'))]]")]

	# Additionally, match short <p> tags (< 100 chars) that lack closing quote, and whose direct siblings do have closing quotes (to exclude runs of same-speaker dialog), and that is not within a blockquote, verse, or letter
	matches = matches + [regex.findall(r"“[^”]+</p>", node.to_string())[0] for node in dom.xpath("/html/body//p[re:test(., '“[^‘”]+$') and not(re:test(., '[…:]$')) and string-length(normalize-space(.)) <=100][(following-sibling::*[1])[not(re:test(., '“[^”]+$'))] and (preceding-sibling::*[1])[not(re:test(., '“[^”]+$'))]][not(ancestor::*[re:test(@epub:type, 'z3998:(verse|poem|song|hymn|lyrics)')]) and not(ancestor::blockquote) and not (ancestor::*[contains(@epub:type, 'z3998:letter')])][(following-sibling::*[1])[name()='p'][re:test(normalize-space(.), '^[“\\[]') and not(contains(., 'continued'))]]")]
	if matches:
		messages.append(LintMessage("t-003", "[text]“[/] missing matching [text]”[/]. Note: When dialog from the same speaker spans multiple [xhtml]<p>[/] elements, it’s correct grammar to omit closing [text]”[/] until the last [xhtml]<p>[/] of dialog.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for lsquo not correctly closed
	matches = regex.findall(r"‘[^“’]+?‘", file_contents)
	matches = [match for match in matches if "</p" not in match and "<br/>" not in match]
	if matches:
		messages.append(LintMessage("t-004", "[text]‘[/] missing matching [text]’[/].", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for closing dialog without comma
	matches = regex.findall(r"[\p{Lowercase_Letter}]+?” [\p{Letter}]+? said", file_contents)
	if matches:
		messages.append(LintMessage("t-005", "Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for possessive 's within name italics, but not in ignored files like the colophon which we know have no possessives
	# Allow some known exceptions like `Harper's`, etc.
	if filename.name not in IGNORED_FILENAMES:
		nodes = dom.xpath("/html/body//i[contains(@epub:type, 'se:name.') and re:test(., '’s$') and not(contains(@epub:type, 'se:name.publication.') and re:test(., '(Pearson’s|Harper’s|Blackwood’s|Fraser’s|Baedeker’s)$'))]")
		if nodes:
			messages.append(LintMessage("t-007", "Possessive [text]’s[/] within name italics. If the name in italics is doing the possessing, [text]’s[/] goes outside italics.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for repeated punctuation, but first remove `&amp;` so we don't match `&amp;,`
	# Remove tds with repeated ” as they are probably ditto marks
	matches = regex.findall(r"[,;]{2,}.{0,20}", file_contents.replace("&amp;", "")) + regex.findall(r"(?:“\s*“|”\s*”|’ ’|‘\s*‘).{0,20}", regex.sub(r"<td>[”\s]+?(<a .+?epub:type=\"noteref\">.+?</a>)?</td>", "", file_contents)) +	 regex.findall(r"[\p{Letter}][,\.:;]\s[,\.:;]\s?[\p{Letter}<].{0,20}", file_contents, flags=regex.IGNORECASE)
	if matches:
		messages.append(LintMessage("t-008", "Repeated punctuation.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for nbsp before times
	nodes = dom.xpath(f"/html/body//text()[re:test(., '[0-9][^{se.NO_BREAK_SPACE}]?$')][(following-sibling::abbr[1])[re:test(., '^[ap]\\.m\\.$')]]")
	if nodes:
		messages.append(LintMessage("t-009", "Required no-break space not found before time and [text]a.m.[/] or [text]p.m.[/].", se.MESSAGE_TYPE_WARNING, filename, [node[-10:] + "<abbr" for node in nodes]))

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

	# Check for missing punctuation before closing quotes
	# Exclude signatures in footers as those are commonly quoted without ending punctuation
	nodes = dom.xpath("/html/body//p[not( (parent::header or parent::hgroup or (parent::footer and contains(@epub:type, 'z3998:signature'))) and position()=last())][re:test(., '[a-z]+[”’]$')]")
	if nodes:
		messages.append(LintMessage("t-011", "Missing punctuation before closing quotes.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string()[-30:] for node in nodes]))

	# Check for whitespace before noteref
	# Do this early because we remove noterefs from headers later
	# Allow noterefs that do not have preceding text/elements (for example a "see note X" ref that is the only child in a <td>)
	nodes = dom.xpath("/html/body//a[contains(@epub:type, 'noteref') and preceding-sibling::node()[normalize-space(.)] and re:test(preceding-sibling::node()[1], '\\s+$')]")
	if nodes:
		messages.append(LintMessage("t-012", "Illegal white space before noteref.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for period following Roman numeral, which is an old-timey style we must fix
	# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
	nodes = dom.xpath("/html/body//node()[name()='span' and contains(@epub:type, 'z3998:roman') and not(position()=1)][(following-sibling::node()[1])[re:test(., '^\\.\\s*[a-z]')]]")
	if nodes:
		messages.append(LintMessage("t-013", "Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() + "." for node in nodes]))

	# Check for two em dashes in a row
	nodes = dom.xpath(f"/html/body//*[re:test(text(), '—{se.WORD_JOINER}*—+')]")
	if nodes:
		messages.append(LintMessage("t-014", "Two or more em-dashes in a row found. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for money not separated by commas
	nodes = dom.xpath("/html/body//*[re:test(text(), '[£\\$][0-9]{4,}')]")
	if nodes:
		messages.append(LintMessage("t-015", "Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <abbr epub:type="z3998:*-name"> that does not contain spaces
	nodes = dom.xpath("/html/body//abbr[re:test(@epub:type, '\\bz3998:[^\\s\"]+name\\b') and re:test(., '[A-Z]\\.[A-Z]\\.')]")
	if nodes:
		messages.append(LintMessage("t-016", "Initials in [xhtml]<abbr epub:type=\"z3998:*-name\">[/] not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	if special_file != "colophon":
		# This file is not the colophon.
		# Check for ending punctuation inside italics that have semantics.
		# Ignore the colophon because paintings might have punctuation in their names

		# This xpath matches b or i elements with epub:type="se:name...", that are not stage direction, whose last text node ends in punctuation.
		# Note that we check that the last node is a text node, because we may have <abbr> as the last node
		matches = [node.to_string() for node in dom.xpath("(//b | //i)[contains(@epub:type, 'se:name') and not(contains(@epub:type, 'z3998:stage-direction'))][(text()[last()])[re:test(., '[\\.,!\\?;:]$')]]")]

		# Match b or i elements that are not stage directions, and that end in a comma followed by a lowercase letter
		matches = matches + [node.to_string() for node in dom.xpath("(//b | //i)[not(contains(@epub:type, 'z3998:stage-direction'))][(text()[last()])[re:test(., ',$')] and following-sibling::node()[re:test(., '^\\s*[a-z]')] ]")]

		# ...and also check for ending punctuation inside em tags, if it looks like a *part* of a clause
		# instead of a whole clause. If the <em> is preceded by an em dash or quotes, or if there's punctuation
		# and a space before it, then it's presumed to be a whole clause.
		matches = matches + [match.strip() for match in regex.findall(r"(?<!.[—“‘>]|[!\.\?…;:]\s)<em>(?:\w+?\s*)+[\.,\!\?;]</em>", file_contents) if match.islower()]

		if matches:
			messages.append(LintMessage("t-017", "Ending punctuation inside formatting like bold, small caps, or italics. Ending punctuation is only allowed within formatting if the phrase is an independent clause.", se.MESSAGE_TYPE_WARNING, filename, list(set(matches))))

	# Check for stage direction that ends in ?! but also has a trailing period
	nodes = dom.xpath("/html/body//i[contains(@epub:type, 'z3998:stage-direction') and re:test(., '\\.$') and not((./node()[last()])[name() = 'abbr']) and (following-sibling::node()[1])[re:test(., '^[\\.,:;!?]')]]")
	if nodes:
		messages.append(LintMessage("t-018", "Stage direction ending in period next to other punctuation. Remove trailing periods in stage direction.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

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

	# Check for punctuation after endnotes
	nodes = dom.xpath(f"/html/body//a[contains(@epub:type, 'noteref')][(following-sibling::node()[1])[re:test(., '^[^\\s<–\\]\\)—{se.WORD_JOINER}a-zA-Z0-9]')]]")
	if nodes:
		messages.append(LintMessage("t-020", "Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename, [node.to_tag_string() for node in nodes]))

	# Check for correct typography around measurements like 2 ft.
	# But first remove href and id attrs because URLs and IDs may contain strings that look like measurements
	# Note that while we check m,min (minutes) and h,hr (hours) we don't check s (seconds) because we get too many false positives on years, like `the 1540s`
	matches = regex.findall(fr"\b[1-9][0-9]*[{se.NO_BREAK_SPACE}\-]?(?:[mck]?[mgl]|ft|in|min?|h|sec|hr)\.?\b", regex.sub(r"(href|id)=\"[^\"]*?\"", "", file_contents))
	# Exclude number ordinals, they're not measurements
	matches = [match for match in matches if not regex.search(r"(st|nd|rd|th)", match)]
	if matches:
		messages.append(LintMessage("t-021", "Measurement not to standard. Numbers are followed by a no-break space and abbreviated units require an [xhtml]<abbr>[/] element. See [path][link=https://standardebooks.org/manual/1.0.0/8-typography#8.8.5]semos://1.0.0/8.8.5[/][/].", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for nbsp within <abbr epub:type="z3998:*-name">, which is redundant
	nodes = dom.xpath(f"/html/body//abbr[re:test(@epub:type, '\\bz3998:[^\\s\"]+name\\b') and contains(text(), '{se.NO_BREAK_SPACE}')]")
	if nodes:
		messages.append(LintMessage("t-022", "No-break space found in [xhtml]<abbr epub:type=\"z3998:*-name\">[/]. This is redundant.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for trailing commas inside <i> tags at the close of dialog
	# More sophisticated version of: \b[^\s]+?,</i>”
	nodes = dom.xpath("/html/body//i[re:test(., ',$')][(following-sibling::node()[1])[starts-with(., '”')]]")
	if nodes:
		messages.append(LintMessage("t-023", "Comma inside [xhtml]<i>[/] element before closing dialog.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() + "”" for node in nodes]))

	# Check for quotation marks in italicized dialog
	nodes = dom.xpath("/html/body//i[@xml:lang][starts-with(., '“') or re:test(., '”$')]")
	if nodes:
		messages.append(LintMessage("t-024", "When italicizing language in dialog, italics go inside quotation marks.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check alt attributes on images, except for the logo
	nodes = dom.xpath("/html/body//img[not(re:test(@src, '/(logo|titlepage)\\.(svg|png)$'))]")
	img_no_alt = []
	img_alt_not_typogrified = []
	img_alt_lacking_punctuation = []
	for node in nodes:
		if "titlepage.svg" not in node.get_attr("src"):
			ebook_flags["has_images"] = True # Save for a later check

		alt = node.get_attr("alt")

		if alt:
			# Check for non-typogrified img alt attributes
			if regex.search(r"""('|"|--|\s-\s|&quot;)""", alt):
				img_alt_not_typogrified.append(node.to_tag_string())

			# Check alt attributes not ending in punctuation
			if filename.name not in IGNORED_FILENAMES and not regex.search(r"""[\.\!\?]”?$""", alt):
				img_alt_lacking_punctuation.append(node.to_tag_string())

			# Check that alt attributes match SVG titles
			img_src = node.lxml_element.get("src")
			if img_src and img_src.endswith("svg"):
				title_text = ""
				image_ref = img_src.split("/").pop()
				try:
					svg_path = self.content_path / "images" / image_ref
					svg_dom = self.get_dom(svg_path)
					try:
						title_text = svg_dom.xpath("/svg/title")[0].text
					except Exception:
						messages.append(LintMessage("s-027", f"{image_ref} missing [xhtml]<title>[/] element.", se.MESSAGE_TYPE_ERROR, svg_path))

					if title_text != "" and alt != "" and title_text != alt:
						messages.append(LintMessage("s-022", f"The [xhtml]<title>[/] element of [path][link=file://{svg_path}]{image_ref}[/][/] does not match the [attr]alt[/] attribute text in [path][link=file://{filename}]{filename.name}[/][/].", se.MESSAGE_TYPE_ERROR, filename))

				except FileNotFoundError:
					missing_files.append(str(Path("images") / image_ref))

		else:
			img_no_alt.append(node.to_tag_string())

	if img_alt_not_typogrified:
		messages.append(LintMessage("t-025", "Non-typogrified [text]'[/], [text]\"[/] (as [xhtml]&quot;[/]), or [text]--[/] in image [attr]alt[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, img_alt_not_typogrified))
	if img_alt_lacking_punctuation:
		messages.append(LintMessage("t-026", "[attr]alt[/] attribute does not appear to end with punctuation. [attr]alt[/] attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename, img_alt_lacking_punctuation))
	if img_no_alt:
		messages.append(LintMessage("s-004", "[xhtml]img[/] element missing [attr]alt[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, img_no_alt))

	# Check for low-hanging misquoted fruit
	matches = regex.findall(r"[\p{Letter}]+[“‘]", file_contents) + regex.findall(r"[^>]+</(?:em|i|b|span)>‘[\p{Lowercase_Letter}]+", file_contents)
	if matches:
		messages.append(LintMessage("t-028", "Possible mis-curled quotation mark.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check for periods followed by lowercase.
	temp_xhtml = regex.sub(r"<title[^>]*?>.+?</title>", "", file_contents) # Remove <title> because it might contain something like <title>Chapter 2: The Antechamber of M. de Tréville</title>
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

	# Check for initialisms without periods
	nodes = [node.to_string() for node in dom.xpath("/html/body//abbr[contains(@epub:type, 'z3998:initialism') and not(re:test(., '^[0-9]*([a-zA-Z]\\.)+[0-9]*$'))]") if node.text not in INITIALISM_EXCEPTIONS]
	if nodes:
		messages.append(LintMessage("t-030", "Initialism with spaces or without periods.", se.MESSAGE_TYPE_WARNING, filename, set(nodes)))

	nodes = dom.xpath("/html/body//*[re:test(text(), '\\bA\\s*B\\s*C\\s*\\b')]")
	if nodes:
		messages.append(LintMessage("t-031", "[text]A B C[/] must be set as [text]A.B.C.[/] It is not an abbreviation.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for abbreviations followed by periods
	# But we exclude some SI units, which don't take periods; abbreviations ending in numbers for example in stage directions; abbreviations like `r^o` (recto) that contain <sup>; and some Imperial abbreviations that are multi-word
	nodes = dom.xpath("/html/body//abbr[(contains(@epub:type, 'z3998:initialism') or re:test(@epub:type, 'z3998:[^\\s]+?name') or not(@epub:type))][not(re:test(., '[cmk][mgl]')) and not(re:test(., '[0-9]$')) and not(./sup) and not(re:test(@class, '\\b(era|temperature|compound)\\b')) and not(re:test(text(), '^(mpg|mph|hp|TV)$'))][following-sibling::text()[1][starts-with(self::text(), '.')]]")
	if nodes:
		messages.append(LintMessage("t-032", "Initialism or name followed by period. Hint: Periods go within [xhtml]<abbr>[/]. [xhtml]<abbr>[/]s containing periods that end a clause require the [class]eoc[/] class.", se.MESSAGE_TYPE_WARNING, filename, [f"{node.to_string()}." for node in nodes]))

	# Check for space after dash
	nodes = dom.xpath("/html/body//*[name()='p' or name()='span' or name='em' or name='i' or name='b' or name='strong'][not(self::comment())][re:test(., '[a-zA-Z]-\\s(?!(and|or|nor|to|und|…)\\b)')]")
	if nodes:
		messages.append(LintMessage("t-033", "Space after dash.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for <cite> preceded by em dash
	nodes = dom.xpath("/html/body//cite[(preceding-sibling::node()[1])[re:test(., '—$')]]")
	if nodes:
		messages.append(LintMessage("t-034", "[xhtml]<cite>[/] element preceded by em-dash. Hint: em-dashes go within [xhtml]<cite>[/] elements.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <cite> without preceding space in text node. (preceding ( or [ are also OK)
	nodes = dom.xpath("/html/body//cite[(preceding-sibling::node()[1])[not(re:test(., '[\\[\\(\\s]$'))]]")
	if nodes:
		messages.append(LintMessage("t-035", "[xhtml]<cite>[/] element not preceded by space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for partially obscured years in which the last year is an em dash
	nodes = dom.xpath("/html/body//p[re:test(.,	 '1\\d{2}⁠—[^“’A-Za-z<]')]")
	if nodes:
		messages.append(LintMessage("t-036", "Em-dash used to obscure single digit in year. Hint: Use a hyphen instead.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for rdquo preceded by space (but not preceded by a rsquo, which might indicate a nested quotation)
	nodes = dom.xpath("/html/body//p[re:test(., '[^’]\\s”')]")
	if nodes:
		messages.append(LintMessage("t-037", "[text]”[/] preceded by space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check obviously miscurled quotation marks
	nodes = dom.xpath("/html/body//p[re:test(., '“$')]")
	if nodes:
		messages.append(LintMessage("t-038", "[text]“[/] before closing [xhtml]</p>[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for some known initialisms with incorrect possessive apostrophes
	nodes = dom.xpath("/html/body//abbr[text()='I.O.U.'][(following-sibling::node()[1])[starts-with(., '’s')]]")
	if nodes:
		messages.append(LintMessage("t-039", "Initialism followed by [text]’s[/]. Hint: Plurals of initialisms are not followed by [text]’[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() + "’s" for node in nodes]))

	# Check if a subtitle ends in a text node with a terminal period; or if it ends in an <i> node containing a terminal period.
	nodes = dom.xpath("/html/body//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6]/*[contains(@epub:type, 'subtitle')][(./text())[last()][re:test(., '\\.$')] or (./i)[last()][re:test(., '\\.$')]]")
	if nodes:
		messages.append(LintMessage("t-040", "Subtitle with illegal ending period.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	matches = regex.findall(r"[^…]\s[!?;:,].{0,10}", file_contents) # If we don't include preceding chars, the regex is 6x faster
	if matches:
		messages.append(LintMessage("t-041", "Illegal space before punctuation.", se.MESSAGE_TYPE_ERROR, filename, matches))

	# Check for a list of some common English loan words that used to be italicized as foreign, but are no longer
	nodes = dom.xpath("/html/body//*[@data-css-font-style='italic' and re:test(., '^(fianc[eé]+|divorc[eé]+|menu|recherch[eé]|tour-de-force|outr[eé]|d[ée]but(ante)?|apropos|[eé]lite|prot[ée]g[ée]+|chef|salon|r[eé]gime|contretemps|[eé]clat|aides?|entr[ée]+|t[eê]te-[aà]-t[eê]tes?|blas[eé]|bourgeoisie)$')]")
	if nodes:
		messages.append(LintMessage("t-043", "Non-English loan word set in italics, when modern typography omits italics. Hint: A word may be correctly italicized when emphasis is desired, if the word is meant to be pronounced with an accent, or if the word is part of non-English speech.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for comma after leading Or in subtitles
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'subtitle') and re:test(text(), '^Or\\s')]")
	if nodes:
		messages.append(LintMessage("t-044", "Comma required after leading [text]Or[/] in subtitles.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for personas that are italicized. Use re:test instead of contains to avoid catching z3998:personal-name
	nodes = dom.xpath("/html/body//*[re:test(@epub:type, 'z3998:persona\\b') and @data-css-font-style = 'italic']")
	if nodes:
		messages.append(LintMessage("t-045", "Element has [val]z3998:persona[/] semantic and is also set in italics.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	if "῾" in file_contents:
		messages.append(LintMessage("t-046", "[text]῾[/] (U+1FFE) detected. Use [text]ʽ[/] (U+02BD) instead.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for all-caps first paragraphs in sections/articles
	# Note that we don't check for small-caps CSS, because there are lots of legitimate cases for that,
	# and it would generate too many false positives.
	# If we did want to do that, this xpath after the last re:test would help: or ./*[not(preceding-sibling::node()[normalize-space(.)]) and @data-css-font-variant='small-caps' and following-sibling::node()[1][self::text()]]
	nodes = dom.xpath("/html/body//*[(name() = 'section' or name() = 'article') and not(contains(@epub:type, 'dedication') or contains(@epub:type, 'z3998:letter'))]/p[1][re:test(normalize-space(.), '^[“’]?(?:[A-Z’]+\\s){2,}')]")
	if nodes:
		messages.append(LintMessage("t-048", "Chapter opening text in all-caps.", se.MESSAGE_TYPE_ERROR, filename, [node.to_string() for node in nodes]))

	# Check for two-em-dashes used for elision instead of three-em-dashes
	matches = regex.findall(fr"[^{se.WORD_JOINER}\p{{Letter}}”]⸺[^“{se.WORD_JOINER}\p{{Letter}}].*", file_contents, flags=regex.MULTILINE)
	if matches:
		messages.append(LintMessage("t-049", "Two-em-dash used for eliding an entire word. Use a three-em-dash instead.", se.MESSAGE_TYPE_WARNING, filename, matches))

	# Check that possessives appear within persona blocks
	nodes = dom.xpath("/html/body//b[contains(@epub:type, 'z3998:persona') and ./following-sibling::node()[1][re:test(., '^’s?')]]")
	if nodes:
		messages.append(LintMessage("t-050", "Possessive [text]’s[/] or [text]’[/] outside of element with [val]z3998:persona[/] semantic.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for quotations that carry to the next paragraph, but the next paragraph has no opening quotation mark
	# Exclude p in blockquote because often that has different formatting
	nodes = dom.xpath("/html/body//p[re:test(., '“[^”]+$') and not(./ancestor::blockquote) and not(./ancestor::*[re:test(@epub:type, 'z3998:(verse|hymn|song|poem)')]) and ./following-sibling::*[1][name() = 'p' and re:test(normalize-space(), '^[^“]')]]")
	if nodes:
		messages.append(LintMessage("t-051", "Dialog in [xhtml]<p>[/] that continues to the next [xhtml]<p>[/], but the next [xhtml]<p>[/] does not begin with [text]“[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for stage direction without ending punctuation. We only want to consider stage direction that is not an interjection in a parent clause.
	# We match if the stage direction ends in lowercase, and if there's no following node, or if there's a following node that doesn't begin in lowercase or an em dash or semicolon (which suggests an interjection).
	nodes = dom.xpath(f"/html/body//i[@epub:type='z3998:stage-direction' and re:test(., '[a-z]$') and re:test(., '^[A-Z]') and (not(./following-sibling::node()[normalize-space(.)]) or ./following-sibling::node()[1][re:test(normalize-space(.), '^[^{se.WORD_JOINER}—;a-z]')])]")
	if nodes:
		messages.append(LintMessage("t-052", "Stage direction without ending punctuation. Note that ending punctuation is optional in stage direction that is an interjection in a parent clause, and such interjections should begin with a lowercase letter.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for stage direction starting in lowercase.	We only want to consider stage direction that is not an interjection in a parent clause.
	# We match if the stage direction starts with a lowercase, and if there's no preceding node, or if there is a preceding node and it doesn't end in a lowercase letter or a small subset of conjoining punctuation.
	nodes = dom.xpath("/html/body//i[@epub:type='z3998:stage-direction' and re:test(., '^[a-z]') and (not(./preceding-sibling::node()[normalize-space(.)]) or ./preceding-sibling::node()[1][re:test(normalize-space(.), '[^a-z:—,;…]$')])]")
	if nodes:
		messages.append(LintMessage("t-053", "Stage direction starting in lowercase letter.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Epigraphs that are entirely non-English should still be in italics, not Roman
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'epigraph') or contains(@epub:type, 'bridgehead')]//p[./i[@xml:lang and @data-css-font-style='normal' and ( (./preceding-sibling::node()='“' and ./following-sibling::node()='”') or not(./preceding-sibling::node()[normalize-space(.)] or ./following-sibling::node()[normalize-space(.)]) ) ]]")
	if nodes:
		messages.append(LintMessage("t-054", "Epigraphs that are entirely non-English should be set in italics, not Roman.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for lone acute accents, which should always be combined or swapped for a more accurate Unicode char
	if "´" in file_contents:
		messages.append(LintMessage("t-055", "Lone acute accent ([val]´[/]). A more accurate Unicode character like prime for coordinates or measurements, or combining accent or breathing mark for Greek text, is required.", se.MESSAGE_TYPE_ERROR, filename))

	# Check for degree confusable
	nodes = dom.xpath("/html/body//*[re:test(text(), '[0-9]+º')]")
	if nodes:
		messages.append(LintMessage("t-056", "Masculine ordinal indicator ([val]º[/]) used instead of degree symbol ([val]°[/]). Note that the masculine ordinal indicator may be appropriate for ordinal numbers read as Latin, i.e. [val]12º[/] reading [val]duodecimo[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <p> starting in lowercase
	# Exclude <p> starting in constructs like `(a)` or `a.` as they may be numbered lists
	nodes = dom.xpath("/html/body//p[not(ancestor::blockquote or ancestor::figure or ancestor::ol[not(ancestor::section[contains(@epub:type, 'endnotes')])] or ancestor::ul or ancestor::table or ancestor::hgroup or preceding-sibling::*[1][name() = 'hr']) and not(contains(@class, 'continued') or re:test(@epub:type, 'z3998:(signature|valediction)')) and not(./*[1][name() = 'math' or name() = 'var' or contains(@epub:type, 'z3998:grapheme')]) and re:test(., '^[^A-Za-z0-9]?[a-z]') and not(re:test(., '^\\([a-z0-9]\\.?\\)\\.?')) and not(re:test(., '^[a-z0-9]\\.\\s'))]")

	# We have to additionally filter using the regex library, because often a sentence may begin with an uppercase ACCENTED letter,
	# and xpath's limited regex library doesn't support Unicode classes
	nodes = [node for node in nodes if regex.match(r"^[^\p{Letter}0-9]?[\p{Lowercase_Letter}]", node.inner_text())]

	if nodes:
		messages.append(LintMessage("t-057", "[xhtml]<p>[/] starting with lowercase letter. Hint: [xhtml]<p>[/] that continues text after a [xhtml]<blockquote>[/] requires the [class]continued[/] class; and use [xhtml]<br/>[/] to split one clause over many lines.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for illegal characters
	matches = regex.findall(fr"({se.UNICODE_BOM}|{se.SHY_HYPHEN})", file_contents)
	if matches:
		# Get the keys of a dict in order to create a list without duplicates
		messages.append(LintMessage("t-058", "Illegal character.", se.MESSAGE_TYPE_ERROR, filename, list({match.encode("unicode_escape").decode().replace("\\u", "U+").upper():None for match in matches}.keys())))

	# Check for period in cite in endnotes
	nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')]//cite[not((./node()[last()])[name() = 'abbr']) and ./following-sibling::*[1][contains(@epub:type, 'backlink')] and re:test(., '^—') and ( (re:test(., '\\.$') and ./following-sibling::node()[re:test(., '^\\s*$')]) or ./following-sibling::node()[re:test(., '^\\.\\s*$')])]")
	if nodes:
		messages.append(LintMessage("t-059", "Period at the end of [xhtml]<cite>[/] element before endnote backlink.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for Bible verses in old-style notation
	nodes = dom.xpath("/html/body//*[(name()='p' or name()='cite' or re:test(name(), '^h[1-6]$')) and .//node()[re:test(., '(Genesis|Gen\\.|Exodus|Ex\\.|Leviticus|Lev\\.|Numbers|Num\\.|Deuteronomy|Deut\\.|Joshua|Josh\\.|Judges|Ruth|Kings|Chronicles|Chron\\.|Ezra|Nehemiah|Neh\\.|Esther|Esth\\.|Job|Psalm|Psalms|Ps\\.|Proverbs|Prov\\.|Ecclesiastes|Ecc\\.|Eccl\\.|Solomon|Sol\\.|Isaiah|Is\\.|Isa\\.|Jeremiah|Jer\\.|Lamentations|Lam\\.|Ezekiel|Ez\\.|Ezek\\.|Daniel|Dan\\.|Hosea|Hos\\.|Joel|Amos|Obadiah|Obad\\.|Jonah|Jon\\.|Micah|Mic\\.|Nahum|Nah\\.|Habakkuk|Hab\\.|Zephaniah|Zeph\\.|Haggai|Hag\\.|Zechariah|Zech\\.|Malachi|Mal\\.|Tobit|Judith|Sirach|Baruch|Maccabees|Esdras|Manasses|Matthew|Matt\\.|Mark|Luke|John|Acts|Romans|Rom\\.|Corinthians|Cor\\.|Corinth\\.|Galatians|Gal\\.|Ephesians|Eph\\.|Philippians|Phil\\.|Philipp\\.|Colossians|Col\\.|Coloss\\.|Thessalonians|Thes\\.|Thess\\.|Timothy|Tim\\.|Titus|Tit\\.|Philemon|Phil\\.|Hebrews|Heb\\.|James|Jas\\.|Peter|Pet\\.|Jude|Revelation|Revelations|Rev\\.)\\s*$') and following-sibling::node()[normalize-space(.)][1][contains(@epub:type, 'z3998:roman') and following-sibling::node()[1][re:test(., '^\\s*[\\.,]?\\s+[0-9]')]]]]")
	if nodes:
		messages.append(LintMessage("t-060", "Old style Bible citation.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for summary-style bridgeheads not ending in punctuation
	# Decide if it's a summary-style bridgehead if it contains two or more em dashes. We use Python regex because
	# xpath can't count the number of occurances of a string.
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'bridgehead') and re:test(., '[^\\.\\!\\?”]”?$')]")
	nodes = [node for node in nodes if len(regex.findall(r"—", node.to_string())) >= 2]
	if nodes:
		messages.append(LintMessage("t-061", "Summary-style bridgehead without ending punctuation.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for uppercased am/pm, except for if they have an epub:type, or when uppercased in titles, or in the nav document
	if not dom.xpath("//nav[contains(@epub:type, 'toc')]"):
		nodes = dom.xpath("/html/body//abbr[re:test(., '^[AP]\\.M\\.$') and not(@epub:type) and not(./ancestor::*[contains(@epub:type, 'title')])]")
		if nodes:
			messages.append(LintMessage("t-062", "Uppercased [text]a.m.[/] and [text]p.m.[/]", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for some Latinisms that need italics according to the manual. We check ancestor-or-self in case the phrase is set in Roman because it's nested in a parent italic.
	# Exclude toto followed by ’ since Toto can be a name.
	# Exclude <h#> whose entire contents is a matched Latinism as we do not italicize those.
	# Ignore the ToC because we have different rules there
	nodes = dom.xpath("/html/body//text()[re:test(., '\\b(a (priori|posteriori|fortiori)|(?<!reductio )ad (hominem|absurdum|nauseam|infinitum|interim|valem)|in (extremis|loco|situ|vitro|absentia|camera|statu quo)|in toto[^’]|more suo|par excellence)\\b', 'i') and not(ancestor-or-self::*[@data-css-font-style='italic']) and not(parent::*[re:test(name(), '^h[1-6]$') and @xml:lang]) and not(ancestor::hgroup) and not(ancestor::nav[contains(@epub:type, 'toc')]) ]")
	if nodes:
		messages.append(LintMessage("t-063", "Non-English confusable phrase set without italics.", se.MESSAGE_TYPE_WARNING, filename, nodes))

	# Check that all names are correctly titlecased. Ignore titles with xml:lang since non-English languages have different titlecasing rules,
	# and ignore titles that have children elements, because se.titlecase() can't handle XML-like titles right now.
	# Ignore titles longer than 150 chars, as long titles are likely old-timey super-long titles that should be mostly sentence-cased
	incorrectly_cased_titles = []
	for node in dom.xpath("/html/body//*[contains(@epub:type, 'se:name') and not(contains(@epub:type, 'se:name.legal-case')) and not(@xml:lang) and not(./*) and string-length(.) <= 150]"):
		# Replace any space that is not a hair space with a regular space. This is because in inline titles, we may correctly
		# have nbsp for example after `St.`, but titlecase will remove that nbsp.
		if se.formatting.titlecase(node.inner_text()) != regex.sub(fr"[^\S{se.HAIR_SPACE}]+", " ", node.inner_text()):
			incorrectly_cased_titles.append(node.to_string())

	if incorrectly_cased_titles:
		messages.append(LintMessage("t-064", "Title not correctly titlecased. Hint: Non-English titles should have an [attr]xml:lang[/] attribute as they have different titlecasing rules.", se.MESSAGE_TYPE_WARNING, filename, incorrectly_cased_titles))

	# Check for headers ending in periods
	# Allow periods at the end of headers that both start and end with double quotes; but headers that only end in double quotes probably don't need periods
	nodes = dom.xpath("/html/body//*[re:test(name(), '^h[1-6]$') and not(contains(@epub:type, 'z3998:initialism')) and not((./node()[last()])[name() = 'abbr']) and (re:test(., '\\.$') or re:test(., '^[^“].+\\.”$'))]")
	if nodes:
		messages.append(LintMessage("t-065", "Header ending in a period.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for royal names whose roman numeral is preceded by `the`
	nodes = dom.xpath("/html/body//span[contains(@epub:type, 'z3998:roman') and ./preceding-sibling::node()[1][re:test(., '[A-Z]\\w+ the $')]]/parent::*")
	if nodes:
		messages.append(LintMessage("t-066", "Regnal ordinal preceded by [text]the[/].", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for plural graphemes without apostrophes
	nodes = dom.xpath("/html/body//i[re:test(@epub:type, 'z3998:(grapheme|phoneme|morpheme)') and ./following-sibling::node()[1][starts-with(., 's')]]")
	if nodes:
		messages.append(LintMessage("t-067", "Plural [val]z3998:grapheme[/], [val]z3998:phoneme[/], or [val]z3998:morpheme[/] formed without apostrophe ([text]’[/]).", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Find citations not offset by em dashes. We're only interested in <cite>s in endnotes that are directly followed by the backlink;
	# ignore <cite>s starting with `Cf.` which means `Compare` and was often used to mean `see`
	nodes = dom.xpath("/html/body//li[contains(@epub:type, 'endnote')]/p[last()]/cite[following-sibling::node()[normalize-space(.)][1][name() = 'a' and contains(@epub:type, 'backlink')] and re:test(., '^[^—]') and not(re:test(., '^(Cf\\.|\\()'))]")
	if nodes:
		messages.append(LintMessage("t-068", "Citation not offset with em dash.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <cite> in <header>s that start with a leading em dash
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'epigraph')]//cite[re:test(., '^—')]")
	if nodes:
		messages.append(LintMessage("t-069", "[xhtml]<cite>[/] in epigraph starting with an em dash.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for <cite> in <header>s that end with a period. Try to exclude <abbr>s that are last children
	nodes = dom.xpath("/html/body//*[contains(@epub:type, 'epigraph')]//cite[re:test(., '\\.$') and not( (./node()[last()])[./descendant-or-self::abbr]) ]")
	if nodes:
		messages.append(LintMessage("t-070", "[xhtml]<cite>[/] in epigraph ending in a period.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# If we have Greek text, try to normalize it
	for node in dom.xpath("/html/body//*[@xml:lang='grc' or @xml:lang='el']"):
		node_text = node.inner_text()
		expected_text = se.typography.normalize_greek(node_text)
		if node_text != expected_text:
			messages.append(LintMessage("t-073", f"Possible transcription error in Greek. Found: [text]{node_text}[/], but expected [text]{expected_text}[/text]. Hint: Use [bash]se unicode-names[/] to see differences in Unicode characters.", se.MESSAGE_TYPE_WARNING, filename))

	return (messages, missing_files)

def _lint_xhtml_xhtml_checks(filename: Path, dom: se.easy_xml.EasyXmlTree, file_contents: str) -> list:
	"""
	Process XHTML checks on an .xhtml file

	INPUTS
	filename: The name of the file being checked
	dom: The dom tree of the file being checked
	file_contents: The contents of the file being checked

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []

	# Check for uppercase letters in IDs or classes
	nodes = dom.xpath("//*[re:test(@id, '[A-Z]') or re:test(@class, '[A-Z]') or re:test(@epub:type, '[A-Z]')]")
	if nodes:
		messages.append(LintMessage("x-002", "Uppercase in attribute value. Attribute values must be all lowercase.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	nodes = dom.xpath("//*[re:test(@id, '^[0-9]+')]")
	if nodes:
		messages.append(LintMessage("x-007", "[attr]id[/] attributes starting with a number are illegal XHTML.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for double greater-than at the end of a tag
	matches = regex.findall(r"(>>|>&gt;)", file_contents)
	if matches:
		messages.append(LintMessage("x-008", "Elements should end with a single [text]>[/].", se.MESSAGE_TYPE_WARNING, filename))

	# Check for leading 0 in IDs (note: not the same as checking for IDs that start with an integer)
	# We only check for *leading* 0s in numbers; this allows IDs like `wind-force-0` in the Worst Journey in the World glossary.
	nodes = dom.xpath("//*[re:test(@id, '-0[0-9]')]")
	if nodes:
		messages.append(LintMessage("x-009", "Illegal leading 0 in [attr]id[/] attribute.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for HTML tags in <title> tags
	nodes = dom.xpath("/html/head/title/*")
	if nodes:
		messages.append(LintMessage("x-010", "Illegal element in [xhtml]<title>[/] element.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for underscores in attributes, but not if the attribute is href (links often have underscores) or MathMl alttext, which can have underscores as part of math notation
	nodes = dom.xpath("//@*[contains(., '_') and name() !='href' and name() !='alttext']/..")
	if nodes:
		messages.append(LintMessage("x-011", "Illegal underscore in attribute. Use dashes instead of underscores.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for style attributes
	nodes = dom.xpath("/html/body//*[@style]")
	if nodes:
		messages.append(LintMessage("x-012", "Illegal [attr]style[/] attribute. Don’t use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for illegal elements in <head>
	nodes = dom.xpath("/html/head/*[not(self::title) and not(self::link[@rel='stylesheet'])]")
	if nodes:
		messages.append(LintMessage("x-015", "Illegal element in [xhtml]<head>[/]. Only [xhtml]<title>[/] and [xhtml]<link rel=\"stylesheet\">[/] are allowed.", se.MESSAGE_TYPE_ERROR, filename, [f"<{node.tag}>" for node in nodes]))

	# Check for xml:lang attribute starting in uppercase
	nodes = dom.xpath("//*[re:test(@xml:lang, '^[A-Z]')]")
	if nodes:
		messages.append(LintMessage("x-016", "[attr]xml:lang[/] attribute with value starting in uppercase letter.", se.MESSAGE_TYPE_ERROR, filename, [node.to_tag_string() for node in nodes]))

	# Check for ID attributes of numbered paragraphs (like `p-44`) that are used as refs in endnotes.
	# Make sure their number is actually their correct sequence number in the text.
	for unexpected_id in se.formatting.find_unexpected_ids(dom):
		messages.append(LintMessage("x-019", f"Unexpected value of [attr]id[/] attribute. Expected: [attr]{unexpected_id[1]}[/].", se.MESSAGE_TYPE_ERROR, filename, [unexpected_id[0].to_tag_string()]))

	return messages

def _lint_xhtml_typo_checks(filename: Path, dom: se.easy_xml.EasyXmlTree, file_contents: str, special_file: Optional[str]) -> list:
	"""
	Process typo checks on an .xhtml file

	INPUTS
	filename: The name of the file being checked
	dom: The dom tree of the file being checked
	file_contents: The contents of the file being checked
	special_file: A string containing the type of special file the current file is, if any

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []
	typos: List[str] = []

	if special_file != "titlepage":
		# Don't check the titlepage because it has a standard format and may raise false positives
		typos = regex.findall(r"(?<!’)\b(and and|the the|if if|of of|or or|as as)\b(?!-)", file_contents, flags=regex.IGNORECASE)
		typos = typos + regex.findall(r"\ba a\b(?!-)", file_contents)

		if typos:
			messages.append(LintMessage("y-001", "Possible typo: doubled [text]a/the/and/of/or/as/if[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for basic typo, but exclude MathML and endnotes. Some endnotes (like in Ten Days that Shook the World) may start with letters.
	dom_copy = deepcopy(dom)
	for node in dom_copy.xpath("//a[contains(@epub:type, 'noteref')]") + dom_copy.xpath("//*[namespace-uri() = 'http://www.w3.org/1998/Math/MathML']"):
		node.remove()

	typos = [node.to_string() for node in dom_copy.xpath("/html/body//p[re:match(., '[a-z][;,][a-z]', 'i')]")]
	if typos:
		messages.append(LintMessage("y-002", "Possible typo: punctuation followed directly by a letter, without a space.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for paragraphs ending in lowercase letters, excluding a number of instances where that might be valid.
	typos = [node.to_string() for node in dom.xpath("//p[re:test(., '[a-z]$') and not(@epub:type or @class) and not(following-sibling::*[1]/node()[1][contains(@epub:type, 'z3998:roman')] or following-sibling::*[1][re:test(., '^([0-9]|first|second|third|fourth|fifth|sixth|seventh|eight|ninth|tenth)', 'i')]) and not(following-sibling::*[1][name() = 'blockquote' or name() = 'figure' or name() = 'table' or name() = 'footer' or name() = 'ul' or name() = 'ol'] or ancestor::*[name() = 'blockquote' or name() = 'footer' or name() = 'header' or name() = 'table' or name() = 'li' or name() = 'figure' or name() = 'hgroup' or re:test(@epub:type, '(z3998:drama|dedication|halftitlepage)')])]")]
	if typos:
		messages.append(LintMessage("y-003", "Possible typo: paragraph missing ending punctuation.", se.MESSAGE_TYPE_WARNING, filename, typos))

	typos = [node.to_string() for node in dom.xpath("//p[re:test(., '-[‘“]')]")]
	if typos:
		messages.append(LintMessage("y-004", "Possible typo: mis-curled quotation mark after dash.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for commas or periods following exclamation or question marks. Exclude the colophon because we may have painting names with punctuation.
	if special_file != "colophon":
		typos = [node.to_string() for node in dom.xpath("//p[re:test(., '[!?][\\.,]([^”’]|$)')]")]
		if typos:
			messages.append(LintMessage("y-005", "Possible typo: question mark or exclamation mark followed by period or comma.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for opening lsquo in quote that doesn't appear to have a matching rsquo, ignoring contractions/edlided words as false matches.
	typos = dom.xpath("re:match(//*, '“[^‘”]*‘[^“]+?”', 'g')/text()[not(re:test(., '’[^A-Za-z]'))]")
	if typos:
		messages.append(LintMessage("y-006", "Possible typo: [text]‘[/] without matching [text]’[/]. Hint: [text]’[/] are used for abbreviations.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Try to find top-level lsquo; for example, <p>“Bah!” he said to the ‘minister.’</p>
	# We can't do this on xpath because we can't iterate over the output of re:replace().
	# A fully-featured solution would parse quotes to find balanced pairs. This quick-n-dirty
	# solution takes the raw XHTML string, strips any seemingly-valid balanced pairs using regex,
	# then searches for unmatched `‘`. If found, it returns the dom node of the match; we can't return
	# the actual string match because we stripped surrounding text.

	# Start by merging all <p> into single lines, including poetry, but exclude blockquotes as they have special quoting rules
	temp_xhtml = ""
	dom_copy = deepcopy(dom)
	node_number = 0
	# Add IDs to the dom so we can find the paragraphs after we run our regex
	# Exclude paragraphs in blockquotes, which may have special quoting rules, and "continued" paragraphs, which may be continued dialog without an “
	for node in dom_copy.xpath("/html/body//p[not(ancestor::blockquote) and not(contains(@class, 'continued'))]"):
		node.set_attr("id", "lint-" + str(node_number))
		temp_xhtml = temp_xhtml + f"<p id=\"lint-{node_number}\">" + regex.sub(r"[\s\n]+", " ", node.inner_text(), flags=regex.DOTALL) + "\n"
		node_number = node_number + 1

	replacement_count = 1
	while replacement_count > 0:
		# Remove all regular quotes. Run this in a loop because we may need to remove triple-nested quotes.
		(temp_xhtml, replacement_count) = regex.subn(r"“[^“]+?”", " ", temp_xhtml) # Remove all regular quotes

	# Remove contractions to reduce rsquo for next regex
	temp_xhtml = regex.sub(r"[\p{Letter}]’[\p{Letter}]", " ", temp_xhtml, flags=regex.MULTILINE)

	# Remove all runs of ldquo that are likely to spill to the next <p>
	replacement_count = 1
	while replacement_count > 0:
		(temp_xhtml, replacement_count) = regex.subn(r"“[^“”]+?$", " ", temp_xhtml, flags=regex.MULTILINE)

	# Match problem `‘` using regex, and if found, get the actual node text from the dom to return.
	typos = []
	for match in regex.findall(r"""<p id="lint-([0-9]+?)">.*‘[\p{Letter}\s]""", temp_xhtml):
		for node in dom_copy.xpath(f"/html/body//p[@id='lint-{match}' and re:test(., '‘[A-Za-z\\s]')]"):
			typos.append(node.inner_text())

	if typos:
		messages.append(LintMessage("y-007", "Possible typo: [text]‘[/] not within [text]“[/]. Hints: Should [text]‘[/] be replaced with [text]“[/]? Is there a missing closing quote? Is this a nested quote that should be preceded by [text]“[/]? Are quotes in close proximity correctly closed?", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for single quotes when there should be double quotes in an interjection in dialog
	typos = [node.to_string() for node in dom.xpath("//p[re:test(., '“[^”]+?’⁠—[^”]+?—“')]")]
	if typos:
		messages.append(LintMessage("y-008", "Possible typo: dialog interrupted by interjection but with incorrect closing quote.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for dialog starting with a lowercase letter. Only check the first child text node of <p>, because other first children might be valid lowercase, like <m:math> or <b>;
	# exclude <p> inside or preceded by <blockquote>; and exclude <p> inside endnotes, as definitions may start with lowercase letters.
	typos = [node.to_string() for node in dom.xpath("/html/body//p[not(ancestor::blockquote or ancestor::li[contains(@epub:type, 'endnote')]) and not(preceding-sibling::*[1][name()='blockquote'])][re:test(./node()[1], '^“[a-z]')]")]
	if typos:
		messages.append(LintMessage("y-009", "Possible typo: dialog begins with lowercase letter.", se.MESSAGE_TYPE_WARNING, filename, typos))

	typos = [node.to_string() for node in dom.xpath("//p[not(ancestor::blockquote) and not(following-sibling::*[1][name() = 'blockquote' or contains(@class, 'continued')]) and re:test(., ',”$')]")]
	if typos:
		messages.append(LintMessage("y-010", "Possible typo: comma ending dialogue.", se.MESSAGE_TYPE_WARNING, filename, typos))

	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '’{2,}')]")]
	if typos:
		messages.append(LintMessage("y-011", "Possible typo: two or more [text]’[/] in a row.", se.MESSAGE_TYPE_WARNING, filename, typos))

	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '”[a-z]')]")]
	if typos:
		messages.append(LintMessage("y-012", "Possible typo: [text]”[/] directly followed by letter.", se.MESSAGE_TYPE_WARNING, filename, typos))

  	# Check for comma/period outside rsquo; ensure no rsquo following the punctuation to exclude elided false positives, e.g. ‘That was somethin’.’
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '‘[^”’]+?’[\\.,](?!⁠? ⁠?…)(?![^‘]*’)')]")]
	if typos:
		messages.append(LintMessage("y-013", "Possible typo: punctuation not within [text]’[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for period before dialog tag; try to exclude abbrevations that close a quotation, like `“<abbr>Mr.</abbr>”`.
	typos = [node.to_string() for node in dom.xpath("/html/body//p[(re:test(., '\\.”\\s[a-z\\s]*?(\\bsaid|[a-z]+ed)') or re:test(., '\\.”\\s(s?he|they?|and)\\b')) and not(.//abbr[following-sibling::node()[re:test(., '^”')]])]")]
	if typos:
		messages.append(LintMessage("y-014", "Possible typo: Unexpected [text].[/] at the end of quotation. Hint: If a dialog tag follows, should this be [text],[/]?", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for mis-curled &lsquo; or &lsquo; without matching &rsquo;
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '‘[A-Za-z][^“’]+?”')]")]
	if typos:
		messages.append(LintMessage("y-015", "Possible typo: mis-curled [text]‘[/] or missing [text]’[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for two periods in a row, almost always a typo for one period or a hellip
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '\\.\\.[^\\.]')]")]
	if typos:
		messages.append(LintMessage("y-016", "Possible typo: consecutive periods ([text]..[/]).", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for ldquo followed by space
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '“\\s+[^‘’]')]")]
	if typos:
		messages.append(LintMessage("y-017", "Possible typo: [text]“[/] followed by space.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for lsquo followed by space
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '‘\\s+[^“’]')]")]
	if typos:
		messages.append(LintMessage("y-018", "Possible typo: [text]‘[/] followed by space.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for closing rdquo without opening ldquo. We ignore blockquotes because they usually have unique quote formatting.
	# Remove tds in case rdquo means "ditto mark"
	typos = regex.findall(r"”[^“‘]+?”", regex.sub(r"<td>[”\s]+?(<a .+?epub:type=\"noteref\">.+?</a>)?</td>", "", file_contents), flags=regex.DOTALL)

	# We create a filter to try to exclude nested quotations
	# Remove tags in case they're enclosing punctuation we want to match against at the end of a sentence.
	typos = [match for match in typos if not regex.search(r"(?:[\.!\?;…—]|”\s)’\s", se.formatting.remove_tags(match))]

	# Try some additional matches before adding the lint message
	# Search for <p> tags that have an ending closing quote but no opening quote; but exclude <p>s that are preceded by a <blockquote>
	# or that have a <blockquote> ancestor, because that may indicate that the opening quote is elsewhere in the quotation.
	for node in dom.xpath("//p[re:test(., '^[^“]+”') and not(./preceding-sibling::*[1][name() = 'blockquote']) and not(./ancestor::*[re:test(@epub:type, 'z3998:(poem|verse|song|hymn)')]) and not(./ancestor::blockquote)]"):
		typos.append(node.to_string()[-20:])

	if typos:
		messages.append(LintMessage("y-019", "Possible typo: [text]”[/] without opening [text]“[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for ,.
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., ',\\.')]")]
	if typos:
		messages.append(LintMessage("y-020", "Possible typo: consecutive comma-period ([text],.[/]).", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for single quotes instead of double quotes
	typos = [node.to_string() for node in dom.xpath("/html/body//p[not(contains(@class, 'continued') or ancestor::blockquote or ancestor::*[re:test(@epub:type, 'z3998:(verse|song|poem|hymn)')]) and re:test(., '^[^“]+?‘')]")]
	if typos:
		messages.append(LintMessage("y-021", "Possible typo: Opening [text]‘[/] without preceding [text]“[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for two quotations in one paragraph
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '^“[^”]+?”\\s“[^”]+?”$')]")]
	if typos:
		messages.append(LintMessage("y-022", "Possible typo: consecutive quotations without intervening text, e.g. [text]“…” “…”[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for incorrectly nested quotation marks
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '^“[^‘”]+“') and not(.//br)]")]
	if typos:
		messages.append(LintMessage("y-023", "Possible typo: two opening quotation marks in a run. Hint: Nested quotes should switch between [text]“[/] and [text]‘[/]", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for dashes instead of em-dashes
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '\\s[a-z]+-(the|there|is|and|they|when)\\s')]")]
	if typos:
		messages.append(LintMessage("y-024", "Possible typo: dash before [text]the/there/is/and/they/when[/] probably should be em-dash.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for comma not followed by space but followed by quotation mark
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '[a-z],[“”‘’][a-z]', 'i')]")]
	if typos:
		messages.append(LintMessage("y-025", "Possible typo: comma without space followed by quotation mark.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for punctuation missing before conjunctions. Ignore <p> with an <i> child starting in a conjunction, as those are probably book titles or non-English languages
	typos = [node.to_string() for node in dom.xpath(f"/html/body//p[not(parent::hgroup) and re:test(., '\\b[a-z]+\\s(But|And|For|Nor|Yet|Or)\\b[^’\\.\\?\\-{se.WORD_JOINER}]') and not(./i[re:test(., '^(But|And|For|Nor|Yet|Or)\\b')])]")]
	if typos:
		messages.append(LintMessage("y-026", "Possible typo: no punctuation before conjunction [text]But/And/For/Nor/Yet/Or[/].", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for extra closing single quote at the end of dialog
	typos = [node.to_string() for node in dom.xpath("/html/body//p[re:test(., '^“[^‘]+”\\s*’$')]")]
	if typos:
		messages.append(LintMessage("y-027", "Possible typo: Extra [text]’[/] at end of paragraph.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for `<abbr>` preceded or followed by text. Ignore compass directions followed by `ly`, like S.S.W.ly
	typos = [node.to_string() for node in dom.xpath("/html/body//abbr[(preceding-sibling::node()[1])[re:test(., '[A-Za-z]$')] or (following-sibling::node()[1])[re:test(., '^[A-Za-z](?<!s\\b)') and not((./preceding-sibling::abbr[1])[contains(@epub:type, 'se:compass')] and re:test(., '^ly\\b'))]]")]
	if typos:
		messages.append(LintMessage("y-028", "Possible typo: [xhtml]<abbr>[/] directly preceded or followed by letter.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for misapplied italics. Ignore 's' because the plural is too common.
	typos = [node.to_string() for node in dom.xpath("/html/body//*[(name() = 'i' or name() = 'em') and ./following-sibling::node()[1][re:test(., '^[a-z]\\b', 'i') and not(re:test(., '^s\\b'))]]")]
	if typos:
		messages.append(LintMessage("y-029", "Possible typo: Italics followed by a letter.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for lowercase letters starting quotations after a preceding period
	typos = dom.xpath("/html/body//p/child::text()[re:test(., '\\.\\s[‘“][a-z]')]")
	if typos:
		messages.append(LintMessage("y-030", "Possible typo: Lowercase quotation following a period. Check either that the period should be a comma, or that the quotation should start with a capital.", se.MESSAGE_TYPE_WARNING, filename, typos))

	# Check for missing punctuation in continued quotations
	# ” said Bob “
	nodes = dom.xpath("/html/body//p[re:test(., '”\\s(?:said|[A-Za-z]{2,}ed)\\s[A-Za-z]+?(?<!\\bthe)(?<!\\bto)(?<!\\bwith)(?<!\\bfrom)(?<!\\ba\\b)(?<!\\bis)\\s“') or re:test(., '[^\\.]”\\s(\\bhe\\b|\\bshe\\b|I|[A-Z][a-z]+?)\\s(?:said|[A-Za-z]{2,}ed)\\s“') or re:test(., ',” (?:said|[A-Za-z]{2,}ed) [A-Za-z]+? [A-Za-z]+?ly “')]")
	if nodes:
		messages.append(LintMessage("y-031", "Possible typo: Dialog tag missing punctuation.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for italics having epub:type that run in to preceding or following characters
	# Ignore things like <i>Newspaper</i>s
	nodes = dom.xpath("/html/body//i[@epub:type and ( (following-sibling::node()[1][re:test(., '^[a-z]', 'i') and not(re:test(., '^(s|es|er)'))]) or preceding-sibling::node()[1][re:test(., '[a-z]$')]) ]")
	if nodes:
		messages.append(LintMessage("y-032", "Possible typo: Italics running into preceding or following characters.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	# Check for three-em-dashes not preceded by a space
	nodes = dom.xpath(f"/html/body//p[re:test(., '[^>“(\\s{se.WORD_JOINER}]{se.WORD_JOINER}?⸻')]")
	if nodes:
		messages.append(LintMessage("y-033", "Possible typo: Three-em-dash obscuring an entire word, but not preceded by a space.", se.MESSAGE_TYPE_WARNING, filename, [node.to_string() for node in nodes]))

	return messages

def _lint_image_metadata_checks(self, has_images: bool) -> list:
	"""
	Process metadata checks on an image file

	INPUTS
	self
	has_images: Flag indicating whether the ebook has images

	OUTPUTS
	A list of LintMessage objects
	"""

	messages = []

	# Check for some accessibility metadata regarding images
	has_visual_accessmode = len(self.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessMode' and text() = 'visual']")) > 0
	has_accessibility_feature_alt = len(self.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'alternativeText']")) > 0
	has_wat_role = len(self.metadata_dom.xpath("/package/metadata/meta[(@property='role') and text() = 'wat']")) > 0

	if has_images:
		if not has_visual_accessmode:
			messages.append(LintMessage("m-028", "Images found in ebook, but no [attr]schema:accessMode[/] property set to [val]visual[/] in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		if not has_accessibility_feature_alt:
			messages.append(LintMessage("m-029", "Images found in ebook, but no [attr]schema:accessibilityFeature[/] property set to [val]alternativeText[/] in metadata.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		if not has_wat_role:
			messages.append(LintMessage("m-040", "Images found in ebook, but no [attr]role[/] property set to [val]wat[/] in metadata for the writer of the alt text.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	if not has_images:
		if has_visual_accessmode:
			messages.append(LintMessage("m-038", "[attr]schema:accessMode[/] property set to [val]visual[/] in metadata, but no images in ebook.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

		if has_accessibility_feature_alt:
			messages.append(LintMessage("m-039", "[attr]schema:accessibilityFeature[/] property set to [val]alternativeText[/] in metadata, but no images in ebook.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	return messages

def _lint_process_ignore_file(self, skip_lint_ignore: bool, allowed_messages: list, messages: list) -> list:
	"""
	Parse a lint ignore file if pressent and if applicable remove its ignored messages

	INPUTS
	self
	skip_lint_ignore: Flag indicating whether the lint ignore file should be respected
	messages: The list of LintMessages that have been generated so far
	allowed_messages: A list of messages from the lint ignore file to allow for this run

	OUTPUTS
	A list of LintMessage objects
	"""

	# This is a dict with where keys are the path and values are a list of code dicts.
	# Each code dict has a key "code" which is the actual code, and a key "used" which is a
	# bool indicating whether or not the code has actually been caught in the linting run.
	ignored_codes: Dict[str, List[Dict]] = {}

	# First, check if we have an se-lint-ignore.xml file in the ebook root. If so, parse it. For an example se-lint-ignore file, see semos://1.0.0/2.3
	lint_ignore_path = self.path / "se-lint-ignore.xml"
	if not skip_lint_ignore and lint_ignore_path.exists():
		lint_config = self.get_dom(lint_ignore_path)

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
						if child.tag == "code" and child.text.strip() not in allowed_messages:
							ignored_codes[path].append({"code": child.text.strip(), "used": False})

						if child.tag == "reason" and child.text.strip() != "":
							has_reason = True

					if not has_reason:
						messages.append(LintMessage("m-046", "Missing or empty [xml]<reason>[/] element.", se.MESSAGE_TYPE_ERROR, lint_ignore_path))

		if has_illegal_path:
			messages.append(LintMessage("m-047", "Ignoring [path]*[/] is too general. Target specific files if possible.", se.MESSAGE_TYPE_WARNING, lint_ignore_path))

	# Done parsing ignore list

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

					except ValueError:
						# This gets raised if the message has already been removed by a previous rule.
						# For example, chapter-*.xhtml gets t-001 removed, then subsequently *.xhtml gets t-001 removed.
						pass
					except Exception as ex:
						raise se.InvalidInputException(f"Invalid path in [path][link=file://{lint_ignore_path}]se-lint-ignore.xml[/][/] rule: [path]{path}[/].") from ex

		# Check for unused ignore rules
		unused_codes: List[str] = []
		for path, codes in ignored_codes.items():
			for code in codes:
				if not code["used"]:
					unused_codes.append(f"{path}, {code['code']}")

		if unused_codes:
			messages.append(LintMessage("m-048", f"Unused [path][link=file://{lint_ignore_path}]se-lint-ignore.xml[/][/] rule.", se.MESSAGE_TYPE_ERROR, lint_ignore_path, unused_codes))

	return messages


def lint(self, skip_lint_ignore: bool, allowed_messages: Optional[List[str]] = None) -> list:
	"""
	Check this ebook for some common SE style errors.

	INPUTS
	self
	skip_lint_ignore: Flag indicating whether ignore file should be used
	allowed_messages: Optional list of messages from lint ignore file to allow this run

	OUTPUTS
	A list of LintMessage objects.
	"""

	local_css_path = self.content_path / "css/local.css"
	messages: List[LintMessage] = []
	typography_messages: List[LintMessage] = []
	cover_svg_title = ""
	titlepage_svg_title = ""
	xhtml_css_classes: Dict[str, int] = {}
	headings: List[tuple] = []
	double_spaced_files: List[Path] = []
	unused_selectors: List[str] = []
	id_attrs: List[str] = []
	abbr_elements_requiring_css: List[se.easy_xml.EasyXmlElement] = []
	glossary_usage = []
	short_story_count = 0
	missing_styles: List[str] = []
	directories_not_url_safe = []
	files_not_url_safe = []
	id_values = {}
	duplicate_id_values = []
	local_css = {
		"has_poem_style": False,
		"has_verse_style": False,
		"has_song_style": False,
		"has_hymn_style": False,
		"has_lyrics_style": False,
		"has_elision_style": False,
		"has_dedication_style": False,
		"has_epigraph_style": False
	}
	ebook_flags = {
		"has_cover_source": False,
		"has_frontmatter": False,
		"has_glossary_search_key_map": False,
		"has_halftitle": False,
		"has_subtitle": bool(self.metadata_dom.xpath("/package/metadata/meta[@property='title-type' and text()='subtitle']")),
		"has_images": False,
		"has_multiple_transcriptions": False,
		"has_multiple_page_scans": False,
		"has_other_sources": False
	}

	# Cache the browser default stylesheet for later use
	with importlib_resources.open_text("se.data", "browser.css", encoding="utf-8") as css:
		self._file_cache["default"] = css.read() # pylint: disable=protected-access

	# Check that the spine has all the expected files in the book
	missing_spine_files = files_not_in_spine(self)
	if missing_spine_files:
		for missing_spine_file in missing_spine_files:
			messages.append(LintMessage("f-007", "File not listed in [xml]<spine>[/].", se.MESSAGE_TYPE_ERROR, missing_spine_file))

	# Get the ebook language for later use
	try:
		language = self.metadata_dom.xpath("/package/metadata/dc:language")[0].text
	except se.InvalidXmlException as ex:
		raise ex
	except Exception as ex:
		raise se.InvalidSeEbookException(f"Missing [xml]<dc:language>[/] element in [path][link=file://{self.metadata_file_path}]{self.metadata_file_path.name}[/][/].") from ex

	# Check local.css for various items, for later use
	try:
		self.local_css = self.get_file(local_css_path)
	except Exception as ex:
		raise se.InvalidSeEbookException(f"Couldn’t open [path]{local_css_path}[/].") from ex

	# cssutils prints warnings/errors to stdout by default, so shut it up here
	cssutils.log.enabled = False

	# Get the css rules and selectors from helper function
	local_css_rules, duplicate_selectors = _get_selectors_and_rules(self)

	if duplicate_selectors:
		messages.append(LintMessage("c-009", "Duplicate CSS selectors. Duplicates are only acceptable if overriding S.E. base styles.", se.MESSAGE_TYPE_WARNING, local_css_path, list(set(duplicate_selectors))))

	# Store a list of CSS selectors, and duplicate it into a list of unused selectors, for later checks
	# We use a regex to remove pseudo-elements like ::before, because we want the *selectors* to see if they're unused.
	local_css_selectors = [regex.sub(r"::[\p{Lowercase_Letter}\-]+", "", selector) for selector in local_css_rules]
	unused_selectors = local_css_selectors.copy()

	# Iterate over rules to do some other checks
	abbr_with_whitespace = []
	for selector, rules in local_css_rules.items():
		if "z3998:poem" in selector:
			local_css["has_poem_style"] = True

		if "z3998:verse" in selector:
			local_css["has_verse_style"] = True

		if "z3998:song" in selector:
			local_css["has_song_style"] = True

		if "z3998:hymn" in selector:
			local_css["has_hymn_style"] = True

		if "z3998:lyrics" in selector:
			local_css["has_lyrics_style"] = True

		if "span.elision" in selector:
			local_css["has_elision_style"] = True

		if "dedication" in selector:
			local_css["has_dedication_style"] = True

		if "epigraph" in selector:
			local_css["has_epigraph_style"] = True

		if "abbr" in selector and "nowrap" in rules:
			abbr_with_whitespace.append(selector)

		if regex.search(r"\[\s*xml\s*\|", selector, flags=regex.IGNORECASE) and "@namespace xml \"http://www.w3.org/XML/1998/namespace\";" not in self.local_css:
			messages.append(LintMessage("c-003", "[css]\\[xml|attr][/] selector in CSS, but no XML namespace declared ([css]@namespace xml \"http://www.w3.org/XML/1998/namespace\";[/]).", se.MESSAGE_TYPE_ERROR, local_css_path))

	messages = messages + _lint_css_checks(self, local_css_path, abbr_with_whitespace)

	missing_files = []
	if self.is_se_ebook:
		root_files = os.listdir(self.path)
		expected_root_files = ["images", "src", "LICENSE.md"]
		illegal_files = [root_file for root_file in root_files if root_file not in expected_root_files and root_file != "se-lint-ignore.xml"] # se-lint-ignore.xml is optional
		missing_files = [expected_root_file for expected_root_file in expected_root_files if expected_root_file not in root_files and expected_root_file != "LICENSE.md"] # We add more to this later on. LICENSE.md gets checked later on, so we don't want to add it twice

		# If we have illegal files, check if they are tracked in Git.
		# If they are, then they're still illegal.
		# If not, ignore them for linting purposes.
		if illegal_files:
			try:
				illegal_files = self.repo.git.ls_files(illegal_files).split("\n")
				if illegal_files and illegal_files[0] == "":
					illegal_files = []
			except Exception:
				# If we can't initialize Git, then just pass through the list of illegal files
				pass

		for illegal_file in illegal_files:
			messages.append(LintMessage("f-001", "Illegal file or directory.", se.MESSAGE_TYPE_ERROR, Path(illegal_file)))

	# Check for repeated punctuation
	nodes = self.metadata_dom.xpath("/package/metadata/*[re:test(., '[,;]{2,}.{0,20}')]")
	if nodes:
		messages.append(LintMessage("t-008", "Repeated punctuation.", se.MESSAGE_TYPE_WARNING, self.metadata_file_path, [node.to_string() for node in nodes]))

	# Set some variables for later
	transcription_source_count = 0
	page_scan_source_count = 0
	other_source_count = 0
	sources = self.metadata_dom.xpath("/package/metadata/dc:source")
	for source in sources:
		if regex.search(r"(gutenberg\.org|wikisource\.org|fadedpage\.com|gutenberg\.net\.au|gutenberg\.ca)", source.inner_text()):
			transcription_source_count = transcription_source_count + 1
		elif regex.search(r"(hathitrust\.org|/archive\.org|books\.google\.com|google\.com/books)", source.inner_text()):
			page_scan_source_count = page_scan_source_count + 1
		else:
			other_source_count = other_source_count + 1

	ebook_flags["has_multiple_transcriptions"] = transcription_source_count >= 2
	ebook_flags["has_multiple_page_scans"] = page_scan_source_count >= 2
	ebook_flags["has_other_sources"] = other_source_count > 0

	messages = messages + _lint_metadata_checks(self)
	# Check for double spacing (done here so double_spaced_files doesn't have to be passed to function)
	if self.metadata_dom.xpath(f"/package/metadata/*[re:test(., '[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}')]"):
		double_spaced_files.append(self.metadata_file_path)

	# Check for malformed URLs
	messages = messages + _get_malformed_urls(self.metadata_dom, self.metadata_file_path)

	# Make sure some static files are unchanged
	if self.is_se_ebook:
		try:
			with importlib_resources.path("se.data.templates", "LICENSE.md") as license_file_path:
				if not filecmp.cmp(license_file_path, self.path / "LICENSE.md"):
					messages.append(LintMessage("f-003", f"File does not match [path][link=file://{license_file_path}]{license_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.path / "LICENSE.md"))
		except Exception:
			missing_files.append("LICENSE.md")

		try:
			with importlib_resources.path("se.data.templates", "core.css") as core_css_file_path:
				if not filecmp.cmp(core_css_file_path, self.content_path / "css/core.css"):
					messages.append(LintMessage("f-004", f"File does not match [path][link=file://{core_css_file_path}]{core_css_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.content_path / "css/core.css"))
		except Exception:
			missing_files.append("css/core.css")

		try:
			with importlib_resources.path("se.data.templates", "logo.svg") as logo_svg_file_path:
				if not filecmp.cmp(logo_svg_file_path, self.content_path / "images/logo.svg"):
					messages.append(LintMessage("f-005", f"File does not match [path][link=file://{logo_svg_file_path}]{logo_svg_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.content_path / "images/logo.svg"))
		except Exception:
			missing_files.append("images/logo.svg")

		try:
			with importlib_resources.path("se.data.templates", "uncopyright.xhtml") as uncopyright_file_path:
				if not filecmp.cmp(uncopyright_file_path, self.content_path / "text/uncopyright.xhtml"):
					messages.append(LintMessage("f-006", f"File does not match [path][link=file://{uncopyright_file_path}]{uncopyright_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.content_path / "text/uncopyright.xhtml"))
		except Exception:
			missing_files.append("text/uncopyright.xhtml")

		try:
			with importlib_resources.path("se.data.templates", "se.css") as core_css_file_path:
				if not filecmp.cmp(core_css_file_path, self.content_path / "css/se.css"):
					messages.append(LintMessage("f-014", f"File does not match [path][link=file://{self.path / 'src/epub/css/se.css'}]{core_css_file_path}[/][/].", se.MESSAGE_TYPE_ERROR, self.content_path / "css/se.css"))
		except Exception:
			missing_files.append("css/se.css")

	# Before we start, walk the files in spine order to build a tree of sections and heading levels.
	section_tree: List[EbookSection] = _build_section_tree(self)
	# This block is useful for pretty-printing section_tree should we need to debug it in the future
	# def dump(item, char):
	#	print(f"{char} {item.section_id} ({item.depth}) {item.has_header}")
	#	for child in item.children:
	#		dump(child, f"	{char}")
	# for section in section_tree:
	#	dump(section, "")
	# exit()

	# Now iterate over individual files for some checks
	# We use os.walk() and not Path.glob() so that we can ignore `.git` and its children
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

			if filename.stem != "LICENSE":
				if filename.stem == "cover.source":
					ebook_flags["has_cover_source"] = True
				else:
					url_safe_filename = se.formatting.make_url_safe(filename.stem) + filename.suffix
					if filename.name != url_safe_filename:
						files_not_url_safe.append(filename)

			if "-0" in filename.name:
				messages.append(LintMessage("f-009", "Illegal leading [text]0[/] in filename.", se.MESSAGE_TYPE_ERROR, filename))

			if filename.suffix in BINARY_EXTENSIONS or filename.name == "core.css":
				if filename.suffix in (".jpg", ".jpeg", ".tif", ".tiff", ".png"):
					messages = messages + _lint_image_checks(self, filename)
				continue

			# Read the file and start doing some serious checks!
			try:
				file_contents = self.get_file(filename)
			except UnicodeDecodeError:
				# This is more to help developers find weird files that might choke `se lint`, hopefully unnecessary for end users
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
				svg_dom = self.get_dom(filename)
				messages = messages + _lint_svg_checks(self, filename, file_contents, svg_dom, root)
				if self.cover_path and filename.name == self.cover_path.name:
					# For later comparison with titlepage
					cover_svg_title = svg_dom.xpath("/svg/title/text()", True).replace("The cover for ", "") # <title> can appear on any element in SVG, but we only want to check the root one
				elif filename.name == "titlepage.svg":
					# For later comparison with cover
					titlepage_svg_title = svg_dom.xpath("/svg/title/text()", True).replace("The titlepage for ", "") # <title> can appear on any element in SVG, but we only want to check the root one

			if filename.suffix == ".xml":
				xml_dom = self.get_dom(filename)

				if xml_dom.xpath("/search-key-map") and filename.name != "glossary-search-key-map.xml":
					messages.append(LintMessage("f-013", "Glossary search key map must be named [path]glossary-search-key-map.xml[/].", se.MESSAGE_TYPE_ERROR, filename))

				# Make sure that everything in glossaries are in the rest of the text
				# We’ll check the files later, and log any errors at the end
				if filename.name == "glossary-search-key-map.xml":
					ebook_flags["has_glossary_search_key_map"] = True
					# Map the glossary to tuples of the values and whether they’re used (initially false)
					glossary_usage = list(map(lambda node: (node.get_attr("value"), False), xml_dom.xpath(".//*[@value]")))

			if filename.suffix == ".xhtml":
				# Read file contents into a DOM for querying
				dom = self.get_dom(filename, True)

				# Apply stylesheets.
				# First apply the browser default stylesheet
				dom.apply_css(self.get_file(Path("default")), "default")

				# Apply any CSS files in the DOM
				for node in dom.xpath("/html/head/link[@rel='stylesheet']"):
					css_filename = (filename.parent / node.get_attr("href")).resolve()
					dom.apply_css(self.get_file(css_filename), str(css_filename))

				messages = messages + _get_malformed_urls(dom, filename)

				# Extract ID attributes for later checks
				id_attrs = id_attrs + dom.xpath("//*[name() != 'section' and name() != 'article' and name() != 'figure' and name() != 'nav']/@id")

				# Add to the short story count for later checks
				short_story_count += len(dom.xpath("/html/body//article[contains(@epub:type, 'se:short-story')]"))

				# Check for ID attrs that don't match the filename.
				# We simply check if there are *any* ids that match, because we can have multiple IDs--for example, works that are part of a volume or subchapters with IDs
				# Ignore <body>s with more than 2 <article>s as those are probably short story collections
				nodes = dom.xpath("/html/body[count(./article) < 2]//*[(name() = 'section' or name() = 'article') and @id]")

				if nodes and filename.stem not in [node.get_attr("id") for node in nodes]:
					messages.append(LintMessage("f-015", "Filename doesn’t match [attr]id[/] attribute of primary [xhtml]<section>[/] or [xhtml]<article>[/]. Hint: [attr]id[/] attributes don’t include the file extension.", se.MESSAGE_TYPE_ERROR, filename))

				# Check for unused selectors
				if dom.xpath("/html/head/link[contains(@href, 'local.css')]"):
					for selector in local_css_selectors:
						try:
							if dom.css_select(selector):
								unused_selectors.remove(selector)
						except lxml.cssselect.ExpressionError:
							# This gets thrown on some selectors not yet implemented by lxml, like *:first-of-type
							unused_selectors.remove(selector)
							continue
						except Exception as ex:
							raise se.InvalidCssException(f"Couldn’t parse CSS in or near this line: [css]{selector}[/]. Exception: {ex}")

				# Update our list of local.css selectors to check in the next file
				local_css_selectors = list(unused_selectors)

				# Done checking for unused selectors.

				# Check if this is a frontmatter file, but exclude the titlepage, imprint, and toc
				if dom.xpath("/html//*[contains(@epub:type, 'frontmatter') and not(descendant-or-self::*[re:test(@epub:type, '\\b(titlepage|imprint|toc)\\b')])]"):
					ebook_flags["has_frontmatter"] = True

				# Do we have a half title?
				# Sometimes the half title might not be a section, like in Cane by Jean Toomer
				if dom.xpath("/html/body//*[contains(@epub:type, 'halftitlepage')]"):
					ebook_flags["has_halftitle"] = True

				# Add new CSS classes to global list
				if filename.name not in IGNORED_FILENAMES:
					for node in dom.xpath("//*[@class]"):
						for css_class in node.get_attr("class").split():
							if css_class in xhtml_css_classes:
								xhtml_css_classes[css_class] += 1
							else:
								xhtml_css_classes[css_class] = 1

				for node in dom.xpath("/html/body//*[@id]/@id"):
					if node in id_values:
						duplicate_id_values.append(node)
					else:
						id_values[node] = True

				# Get the title of this file to compare against the ToC later.
				# We ignore the ToC file itself.
				# Also ignore files that have more than 3 top-level sections or articles, as these are probably compilation works that will have unique titles.
				if not dom.xpath("/html/body/nav[contains(@epub:type, 'toc')]") and not dom.xpath("/html/body[count(./section) + count(./article) > 3]"):
					try:
						header_text = dom.xpath("/html/head/title/text()")[0]
					except Exception:
						header_text = ""

					if header_text != "":
						headings.append((header_text, str(filename)))

				# Check for double spacing
				matches = regex.search(fr"[{se.NO_BREAK_SPACE}{se.HAIR_SPACE} ]{{2,}}", file_contents)
				if matches:
					double_spaced_files.append(filename)

				# Collect certain abbr elements to check that required styles are included, but not in the colophon
				if not dom.xpath("/html/body/*[contains(@epub:type, 'colophon')]"):
					# For now, temperature, acronym, and era are the only abbrs with required styles
					abbr_elements_requiring_css += dom.xpath("/html/body//abbr[re:test(@epub:type, '\\b(se:temperature|se:era|z3998:acronym)\\b')]")

				# Check and log missing glossary keys
				if ebook_flags["has_glossary_search_key_map"] and filename.name not in IGNORED_FILENAMES:
					source_text = dom.xpath("/html/body")[0].inner_text()
					if dom.xpath("/html/body//section[contains(@epub:type, 'glossary')]"):
						nodes = dom.xpath("/html/body//dd[contains(@epub:type, 'glossdef')]")
						source_text = " ".join([node.inner_text() for node in nodes])
					for glossary_index, glossary_value in enumerate(glossary_usage):
						if glossary_value[1] is False and regex.search(glossary_value[0], source_text, flags=regex.IGNORECASE):
							glossary_usage[glossary_index] = (glossary_value[0], True)

				# Test against word boundaries to not match `halftitlepage`
				if dom.xpath("/html/body/section[re:test(@epub:type, '\\btitlepage\\b')]"):
					special_file = "titlepage"
					# Check if the <title> element is set correctly, but only if there's no heading content.
					# If there's heading content, then <title> should match the expected generated value from the heading content.
					if dom.xpath("/html[not(./body//*[re:test(name(), '^h(group|[1-6])$')]) and ./head/title[text()!='Titlepage']]"):
						messages.append(LintMessage("s-025", "Titlepage [xhtml]<title>[/] elements must contain exactly: [text]Titlepage[/].", se.MESSAGE_TYPE_ERROR, filename))

				elif dom.xpath("/html/body/section[contains(@epub:type, 'colophon')]"):
					special_file = "colophon"
				elif dom.xpath("/html/body/section[contains(@epub:type, 'imprint')]"):
					special_file = "imprint"
				elif dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]"):
					special_file = "endnotes"
				elif dom.xpath("/html/body/nav[contains(@epub:type, 'loi')]"):
					special_file = "loi"
				else:
					special_file = None

				if special_file in SPECIAL_FILES:
					messages = messages + _lint_special_file_checks(self, filename, dom, file_contents, ebook_flags, special_file)

				missing_styles = missing_styles + _update_missing_styles(filename, dom, local_css)

				messages = messages + _lint_xhtml_css_checks(filename, dom, local_css_path)

				messages = messages + _lint_xhtml_metadata_checks(self, filename, dom)

				messages = messages + _lint_xhtml_syntax_checks(self, filename, dom, file_contents, ebook_flags, language, section_tree)

				(typography_messages, missing_files) = _lint_xhtml_typography_checks(filename, dom, file_contents, special_file, ebook_flags, missing_files, self)
				if typography_messages:
					messages = messages + typography_messages

				messages = messages + _lint_xhtml_xhtml_checks(filename, dom, file_contents)

				messages = messages + _lint_xhtml_typo_checks(filename, dom, file_contents, special_file)

	if self.cover_path and cover_svg_title != titlepage_svg_title:
		messages.append(LintMessage("s-028", f"[path][link=file://{self.cover_path}]{self.cover_path.name}[/][/] and [path][link=file://{self.path / 'images/titlepage.svg'}]titlepage.svg[/][/] [xhtml]<title>[/] elements don’t match.", se.MESSAGE_TYPE_ERROR, self.cover_path))

	if ebook_flags["has_frontmatter"] and not ebook_flags["has_halftitle"]:
		messages.append(LintMessage("s-020", "Frontmatter found, but no half title page. Half title page is required when frontmatter is present.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	if self.is_se_ebook and not ebook_flags["has_cover_source"]:
		missing_files.append("images/cover.source.jpg")

	# check for classes used but not in CSS, and classes only used once
	missing_selectors = []
	single_use_css_classes = []

	for css_class, count in xhtml_css_classes.items():
		if css_class not in IGNORED_CLASSES:
			if f".{css_class}" not in self.local_css:
				missing_selectors.append(css_class)

		if count == 1 and css_class not in IGNORED_CLASSES and not regex.match(r"^i[0-9]+$", css_class):
			# Don't count ignored classes OR i[0-9] which are used for poetry styling
			single_use_css_classes.append(css_class)

	if missing_selectors:
		messages.append(LintMessage("x-013", f"CSS class found in XHTML, but not in [path][link=file://{local_css_path}]local.css[/][/].", se.MESSAGE_TYPE_ERROR, local_css_path, missing_selectors))

	if single_use_css_classes:
		messages.append(LintMessage("c-008", "CSS class only used once. Can a clever selector be crafted instead of a single-use class? When possible classes should not be single-use style hooks.", se.MESSAGE_TYPE_WARNING, local_css_path, single_use_css_classes))

	# We have a list of ID attributes in the ebook. Now iterate over all XHTML files again to ensure each one has been used
	# Only run this check if we actually have ID attributes to inspect
	if id_attrs:
		id_attrs = list(set(id_attrs))
		unused_id_attrs = deepcopy(id_attrs)
		sorted_filenames: List[str] = []

		# Href links are mostly found in endnotes, so if there's an endnotes file process it first
		# to try to speed things up a little
		for file_path in self.content_path.glob("**/*"):
			if file_path.suffix in (".xhtml", ".xml"):
				dom = self.get_dom(file_path)
				if dom.xpath("/html/body/section[contains(@epub:type, 'glossary') or contains(@epub:type, 'endnotes')]") or dom.xpath("/search-key-map"):
					sorted_filenames.insert(0, file_path)
				else:
					sorted_filenames.append(file_path)

		for filename in sorted_filenames:
			xhtml = self.get_file(filename)

			for attr in id_attrs:
				# We use a simple `in` check instead of xpath because it's an order of magnitude faster on
				# really big ebooks with lots of IDs like Pepys.
				if f"#{attr}\"" in xhtml:
					try:
						unused_id_attrs.remove(attr)
					except ValueError:
						# We get here if we try to remove a value that has already been removed
						pass

			# Reduce the list of ID attrs to check in the next pass, a time saver for big ebooks
			id_attrs = deepcopy(unused_id_attrs)

		if unused_id_attrs:
			messages.append(LintMessage("x-018", "Unused [xhtml]id[/] attribute.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, natsorted(unused_id_attrs)))

	if files_not_url_safe:
		try:
			files_not_url_safe = self.repo.git.ls_files([str(f.relative_to(self.path)) for f in files_not_url_safe]).split("\n")
			if files_not_url_safe and files_not_url_safe[0] == "":
				files_not_url_safe = []
		except Exception:
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

			# Git doesn't store directories, only files. So the above output will be a list of files within a badly-named dir.
			# To get the dir name, get the parent of the file that Git outputs.
			for index, filepath in enumerate(directories_not_url_safe):
				directories_not_url_safe[index] = str(Path(filepath).parent.name)

			# Remove duplicates
			directories_not_url_safe = list(set(directories_not_url_safe))
		except Exception:
			# If we can't initialize Git, then just pass through the list of illegal files
			pass

		for filepath in directories_not_url_safe:
			filepath = Path(filepath)
			url_safe_filename = se.formatting.make_url_safe(filepath.stem)
			messages.append(LintMessage("f-008", f"Filename is not URL-safe. Expected: [path]{url_safe_filename}[/].", se.MESSAGE_TYPE_ERROR, filepath))

	if duplicate_id_values:
		duplicate_id_values = natsorted(list(set(duplicate_id_values)))
		messages.append(LintMessage("x-017", "Duplicate value for [attr]id[/] attribute.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, duplicate_id_values))

	# Check our headings against the ToC and landmarks
	headings = list(set(headings))
	toc_dom = self.get_dom(self.toc_path)
	toc_headings = []
	toc_entries = toc_dom.xpath("/html/body/nav[@epub:type='toc']//a")

	# Match ToC headings against text headings
	for node in toc_entries:
		# Remove # anchors after filenames (for books like Aesop's fables)
		entry_file = self.content_path / regex.sub(r"#.+$", "", node.get_attr("href"))
		toc_headings.append((node.inner_text(), str(entry_file)))

	for heading in headings:
		# Some compilations, like Songs of a Sourdough, have their title in the half title, so check against that before adding an error
		# Ignore the half title page, because its text may differ in collections with only one file, like Father Goriot or The Path to Rome
		if heading not in toc_headings and Path(heading[1]).name != 'halftitlepage.xhtml' and (heading[0], str(self.path / "src/epub/text/halftitlepage.xhtml")) not in toc_headings:
			messages.append(LintMessage("m-045", f"Heading [text]{heading[0]}[/] found, but not present for that file in the ToC.", se.MESSAGE_TYPE_ERROR, Path(heading[1])))

	for element in abbr_elements_requiring_css:
		# All abbr elements have an epub:type because we selected them based on epub:type in the xpath
		for value in element.get_attr("epub:type").split():
			if f"[epub|type~=\"{value}\"]" not in self.local_css:
				missing_styles.append(element.to_tag_string())

	messages = messages + _lint_image_metadata_checks(self, ebook_flags["has_images"])

	if missing_styles:
		messages.append(LintMessage("c-006", f"Semantic found, but missing corresponding style in [path][link=file://{local_css_path}]local.css[/][/].", se.MESSAGE_TYPE_ERROR, local_css_path, sorted(set(missing_styles))))

	for double_spaced_file in double_spaced_files:
		messages.append(LintMessage("t-001", "Double spacing found. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)", se.MESSAGE_TYPE_ERROR, double_spaced_file))

	if missing_files:
		messages.append(LintMessage("f-002", "Missing expected file or directory.", se.MESSAGE_TYPE_ERROR, self.metadata_file_path, missing_files))

	if unused_selectors:
		messages.append(LintMessage("c-002", "Unused CSS selectors.", se.MESSAGE_TYPE_ERROR, local_css_path, unused_selectors))

	if short_story_count and not self.metadata_dom.xpath("//meta[@property='se:subject' and text() = 'Shorts']"):
		messages.append(LintMessage("m-027", "[val]se:short-story[/] semantic inflection found, but no [val]se:subject[/] with the value of [text]Shorts[/].", se.MESSAGE_TYPE_ERROR, self.metadata_file_path))

	if ebook_flags["has_glossary_search_key_map"]:
		entries = []
		for glossary_value in glossary_usage:
			if glossary_value[1] is False:
				entries.append(glossary_value[0])

		if entries:
			messages.append(LintMessage("m-070", "Glossary entry not found in the text.", se.MESSAGE_TYPE_ERROR, self.content_path / "glossary-search-key-map.xml", entries))

	if not allowed_messages:
		allowed_messages = []

	messages = _lint_process_ignore_file(self, skip_lint_ignore, allowed_messages, messages)

	messages = natsorted(messages, key=lambda x: ((str(x.filename.name) if x.filename else "") + " " + x.code), alg=ns.PATH)

	return messages
