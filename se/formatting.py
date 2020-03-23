#!/usr/bin/env python3
"""
Defines functions useful for formatting code or text according to SE standards, for calculating
several text-level statistics like reading ease, and for adding semantics.
"""

import math
import unicodedata
import html.entities
import os
from pathlib import Path
import subprocess
import shutil
import string
from bs4 import BeautifulSoup, NavigableString, Tag
import regex
import roman
import tinycss2
from titlecase import titlecase as pip_titlecase
import se


def semanticate(xhtml: str) -> str:
	"""
	Add semantics to well-formed XHTML

	INPUTS
	xhtml: A string of well-formed XHTML

	OUTPUTS
	A string of XHTML with semantics added.
	"""

	# Some common abbreviations
	xhtml = regex.sub(r"(?<!\<abbr\>)Mr\.", r"<abbr>Mr.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mrs\.", r"<abbr>Mrs.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Ms\.", r"<abbr>Ms.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Dr\.", r"<abbr>Dr.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Drs\.", r"<abbr>Drs.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Prof\.", r"<abbr>Prof.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Rev\.", r"<abbr>Rev.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Hon\.", r"<abbr>Hon.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Lieut\.", r"<abbr>Lieut.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Fr\.", r"<abbr>Fr.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Lt\.", r"<abbr>Lt.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Capt\.", r"<abbr>Capt.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Pvt\.", r"<abbr>Pvt.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Esq\.", r"<abbr>Esq.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mt\.", r"<abbr>Mt.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)MM\.", r"<abbr>MM.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mme\.", r"<abbr>Mme.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mmes\.", r"<abbr>Mmes.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mon\.", r"<abbr>Mon.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mlle\.", r"<abbr>Mlle.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mdlle\.", r"<abbr>Mdlle.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Mlles\.", r"<abbr>Mlles.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Messrs\.", r"<abbr>Messrs.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Messers\.", r"<abbr>Messers.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr[^\>]*?\>)P\.S\.", r"<abbr>P.S.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Co\.", r"<abbr>Co.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Inc\.", r"<abbr>Inc.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Ltd\.", r"<abbr>Ltd.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)St\.", r"<abbr>St.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)MS(S?)\.", r"<abbr>MS\1.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)([Vv])iz\.", r"<abbr>\1iz.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)etc\.", r"\1<abbr>etc.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)([Cc])f\.", r"\1<abbr>\2f.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)p\.([\s0-9])", r"\1<abbr>p.</abbr>\2", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)ed\.", r"\1<abbr>ed.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)([Ii])\.e\.", r"<abbr>\1.e.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)([Ee])\.g\.", r"<abbr>\1.g.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)([Ll])b\.", r"\1<abbr>\2b.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)([Ll])bs\.", r"\1<abbr>\2bs.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)([Oo])z\.", r"\1<abbr>\2z.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)(Jan\.|Feb\.|Mar\.|Apr\.|Jun\.|Jul\.|Aug\.|Sep\.|Sept\.|Oct\.|Nov\.|Dec\.)", r"<abbr>\1</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)No\.(\s+[0-9]+)", r"<abbr>No.</abbr>\1", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="degree"\>)PhD""", r"""<abbr class="degree">PhD</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="initialism"\>)IOU""", r"""<abbr class="initialism">IOU</abbr>""", xhtml)
	xhtml = regex.sub(r"""\b(?<!\<abbr class="era"\>)A\.?D""", r"""<abbr class="era">AD</abbr>""", xhtml)
	xhtml = regex.sub(r"""\b(?<!\<abbr class="era"\>)B\.?C""", r"""<abbr class="era">BC</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="time( eoc)?"\>)([ap])\.\s?m\.""", r"""<abbr class="time">\2.m.</abbr>""", xhtml)

	# Guess at adding eoc (End Of Clause) class
	xhtml = regex.sub(r"""<abbr>([a-zA-Z\.]+?\.)</abbr></p>""", r"""<abbr class="eoc">\1</abbr></p>""", xhtml)
	xhtml = regex.sub(r"""<abbr class="(.+?)">([a-zA-Z\.]+?\.)</abbr></p>""", r"""<abbr class="\1 eoc">\2</abbr></p>""", xhtml)
	xhtml = regex.sub(r"""<abbr>etc\.</abbr>(\s+[A-Z])""", r"""<abbr class="eoc">etc.</abbr>\1""", xhtml)

	# We may have added eoc classes twice, so remove duplicates here
	xhtml = regex.sub(r"""<abbr class="(.*) eoc(\s+eoc)+">""", r"""<abbr class="\1 eoc">""", xhtml)

	# Clean up nesting errors
	xhtml = regex.sub(r"""<abbr class="eoc"><abbr>([^<]+)</abbr></abbr>""", r"""<abbr class="eoc">\1</abbr>""", xhtml)

	# Get Roman numerals >= 2 characters
	# We only wrap these if they're standalone (i.e. not already wrapped in a tag) to prevent recursion in multiple runs
	xhtml = regex.sub(r"([^a-zA-Z>])([ixvIXV]{2,})(\b|st\b|nd\b|rd\b|th\b)", r"""\1<span epub:type="z3998:roman">\2</span>\3""", xhtml)

	# Get Roman numerals that are X or V and single characters.  We can't do I for obvious reasons.
	xhtml = regex.sub(r"""([^a-zA-Z>\"])([vxVX])(\b|st\b|nd\b|rd\b|th\b)""", r"""\1<span epub:type="z3998:roman">\2</span>\3""", xhtml)

	# We may have added HTML tags within title tags.  Remove those here
	matches = regex.findall(r"<title>.+?</title>", xhtml)
	if matches:
		xhtml = regex.sub(r"<title>.+?</title>", f"<title>{se.formatting.remove_tags(matches[0])}</title>", xhtml)

	return xhtml

def get_flesch_reading_ease(xhtml: str) -> float:
	"""
	Get the Flesch reading ease of some XHTML.

	INPUTS
	text: A string of XHTML to calculate the reading ease of.

	OUTPUTS
	A float representing the Flesch reading ease of the text.
	"""

	# Remove HTML tags
	text = regex.sub(r"<title>.+?</title>", " ", xhtml)
	text = regex.sub(r"<.+?>", " ", text, flags=regex.DOTALL)

	# Remove non-sentence-ending punctuation from source text
	included_characters = list(string.whitespace) + list(string.digits) + [":", ";", ".", "?", "!"]
	processed_text = regex.sub(r"[—–\n]", " ", text.lower())
	processed_text = "".join(c for c in processed_text if c.isalpha() or c in included_characters).strip()

	# Remove accents
	processed_text = "".join(c for c in unicodedata.normalize("NFD", processed_text) if unicodedata.category(c) != "Mn")

	# Get word count
	word_count = se.formatting.get_word_count(processed_text)
	if word_count <= 0:
		word_count = 1

	# Get average sentence length
	ignore_count = 0
	sentences = regex.split(r" *[\.\?!]['\"\)\]]* *", processed_text)
	for sentence in sentences:
		if se.formatting.get_word_count(sentence) <= 2:
			ignore_count = ignore_count + 1
	sentence_count = len(sentences) - ignore_count

	if sentence_count <= 0:
		sentence_count = 1

	average_sentence_length = round(float(word_count) / float(sentence_count), 1)

	# Get average syllables per word
	syllable_count = 0
	for word in processed_text.split():
		syllable_count += _get_syllable_count(word)

	average_syllables_per_word = round(float(syllable_count) / float(word_count), 1)

	return round(206.835 - float(1.015 * average_sentence_length) - float(84.6 * average_syllables_per_word), 2)

def _get_syllable_count(word: str) -> int:
	"""
	Helper function to get the syllable count of a word.
	"""

	# See http://eayd.in/?p=232
	exception_add = ["serious", "crucial"]
	exception_del = ["fortunately", "unfortunately"]

	co_one = ["cool", "coach", "coat", "coal", "count", "coin", "coarse", "coup", "coif", "cook", "coign", "coiffe", "coof", "court"]
	co_two = ["coapt", "coed", "coinci"]

	pre_one = ["preach"]

	syls = 0 # Added syllable number
	disc = 0 # Discarded syllable number

	# 1) if letters < 3: return 1
	if len(word) <= 3:
		syls = 1
		return syls

	# 2) if doesn't end with "ted" or "tes" or "ses" or "ied" or "ies", discard "es" and "ed" at the end.
	# if it has only 1 vowel or 1 set of consecutive vowels, discard. (like "speed", "fled" etc.)
	if word[-2:] == "es" or word[-2:] == "ed":
		double_and_triple_1 = len(regex.findall(r"[eaoui][eaoui]", word))
		if double_and_triple_1 > 1 or len(regex.findall(r"[eaoui][^eaoui]", word)) > 1:
			if word[-3:] == "ted" or word[-3:] == "tes" or word[-3:] == "ses" or word[-3:] == "ied" or word[-3:] == "ies":
				pass
			else:
				disc += 1

	# 3) discard trailing "e", except where ending is "le"
	le_except = ["whole", "mobile", "pole", "male", "female", "hale", "pale", "tale", "sale", "aisle", "whale", "while"]

	if word[-1:] == "e":
		if word[-2:] == "le" and word not in le_except:
			pass

		else:
			disc += 1

	# 4) check if consecutive vowels exists, triplets or pairs, count them as one.
	double_and_triple = len(regex.findall(r"[eaoui][eaoui]", word))
	tripple = len(regex.findall(r"[eaoui][eaoui][eaoui]", word))
	disc += double_and_triple + tripple

	# 5) count remaining vowels in word.
	num_vowels = len(regex.findall(r"[eaoui]", word))

	# 6) add one if starts with "mc"
	if word[:2] == "mc":
		syls += 1

	# 7) add one if ends with "y" but is not surrouned by vowel
	if word[-1:] == "y" and word[-2] not in "aeoui":
		syls += 1

	# 8) add one if "y" is surrounded by non-vowels and is not in the last word.
	for i, j in enumerate(word):
		if j == "y":
			if (i != 0) and (i != len(word) - 1): # pylint: disable=consider-using-in
				if word[i - 1] not in "aeoui" and word[i + 1] not in "aeoui":
					syls += 1

	# 9) if starts with "tri-" or "bi-" and is followed by a vowel, add one.
	if word[:3] == "tri" and word[3] in "aeoui":
		syls += 1

	if word[:2] == "bi" and word[2] in "aeoui":
		syls += 1

	# 10) if ends with "-ian", should be counted as two syllables, except for "-tian" and "-cian"
	if word[-3:] == "ian":
	# and (word[-4:] != "cian" or word[-4:] != "tian"):
		if word[-4:] == "cian" or word[-4:] == "tian":
			pass
		else:
			syls += 1

	# 11) if starts with "co-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.
	if word[:2] == "co" and word[2] in "eaoui":

		if word[:4] in co_two or word[:5] in co_two or word[:6] in co_two:
			syls += 1
		elif word[:4] in co_one or word[:5] in co_one or word[:6] in co_one:
			pass
		else:
			syls += 1

	# 12) if starts with "pre-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.
	if word[:3] == "pre" and word[3] in "eaoui":
		if word[:6] in pre_one:
			pass
		else:
			syls += 1

	# 13) check for "-n't" and cross match with dictionary to add syllable.
	negative = ["doesn't", "isn't", "shouldn't", "couldn't", "wouldn't", "doesn’t", "isn’t", "shouldn’t", "couldn’t", "wouldn’t"]

	if word[-3:] == "n't" or word[-3:] == "n’t":
		if word in negative:
			syls += 1
		else:
			pass

	# 14) Handling the exceptional words.
	if word in exception_del:
		disc += 1

	if word in exception_add:
		syls += 1

	# Calculate the output
	return num_vowels - disc + syls

def get_word_count(xhtml: str) -> int:
	"""
	Get the word count from an XHTML string.

	INPUTS
	xhtml: A string of XHTML

	OUTPUTS
	The number of words in the XHTML string.
	"""

	# Remove MathML
	xhtml = regex.sub(r"<(m:)?math.+?</(m:)?math>", " ", xhtml)

	# Remove HTML tags
	xhtml = regex.sub(r"<title>.+?</title>", " ", xhtml)
	xhtml = regex.sub(r"<.+?>", " ", xhtml, flags=regex.DOTALL)

	# Replace some formatting characters
	xhtml = regex.sub(r"[…–—― ‘’“”\{\}\(\)]", " ", xhtml, flags=regex.IGNORECASE | regex.DOTALL)

	# Remove word-connecting dashes, apostrophes, commas, and slashes (and/or), they count as a word boundry but they shouldn't
	xhtml = regex.sub(r"[a-z0-9][\-\'\,\.\/][a-z0-9]", "aa", xhtml, flags=regex.IGNORECASE | regex.DOTALL)

	# Replace sequential spaces with one space
	xhtml = regex.sub(r"\s+", " ", xhtml, flags=regex.IGNORECASE | regex.DOTALL)

	# Get the word count
	return len(regex.findall(r"\b\w+\b", xhtml, flags=regex.IGNORECASE | regex.DOTALL))

def _replace_character_references(match_object) -> str:
	"""Replace most XML character references with literal characters.

	This function excludes &, >, and < (&amp;, &lt;, and &gt;), since
	un-escaping them would create an invalid document.
	"""

	entity = match_object.group(0).lower()

	retval = entity

	# Explicitly whitelist the three (nine) essential character references
	try:
		if entity in ["&gt;", "&lt;", "&amp;", "&#62;", "&#60;", "&#38;", "&#x3e;", "&#x3c;", "&#x26;"]:
			retval = entity
		# Convert base 16 references
		elif entity.startswith("&#x"):
			retval = chr(int(entity[3:-1], 16))
		# Convert base 10 references
		elif entity.startswith("&#"):
			retval = chr(int(entity[2:-1]))
		# Convert named references
		else:
			retval = html.entities.html5[entity[1:]]
	except (ValueError, KeyError):
		pass

	return retval

def format_xhtml_file(filename: Path, single_lines: bool = False, is_metadata_file: bool = False, is_endnotes_file: bool = False, is_colophon_file: bool = False) -> None:
	"""
	Pretty-print well-formed XHTML and save to file.

	INPUTS
	filename: A file containing well-formed XHTML
	single_lines: True to collapse hard-wrapped line breaks, like those found at Project Gutenberg, to single lines
	is_metadata_file: True if the passed XHTML is an SE content.opf metadata file
	is_endnotes_file: True if the passed XHTML is an SE endnotes file

	OUTPUTS
	None.
	"""

	with open(filename, "r+", encoding="utf-8") as file:
		xhtml = file.read()

		processed_xhtml = se.formatting.format_xhtml(xhtml, single_lines, is_metadata_file, is_endnotes_file, is_colophon_file)

		if processed_xhtml != xhtml:
			file.seek(0)
			file.write(processed_xhtml)
			file.truncate()

def format_xhtml(xhtml: str, single_lines: bool = False, is_metadata_file: bool = False, is_endnotes_file: bool = False, is_colophon_file: bool = False) -> str:
	"""
	Pretty-print well-formed XHTML.

	INPUTS
	xhtml: A string of well-formed XHTML
	single_lines: True to collapse hard-wrapped line breaks, like those found at Project Gutenberg, to single lines
	is_metadata_file: True if the passed XHTML is an SE content.opf metadata file
	is_endnotes_file: True if the passed XHTML is an SE endnotes file

	OUTPUTS
	A string of pretty-printed XHTML.
	"""

	which_xmllint = shutil.which("xmllint")
	if which_xmllint:
		xmllint_path = Path(which_xmllint)
	else:
		raise se.MissingDependencyException("Couldn’t locate `xmllint`. Is it installed?")

	env = os.environ.copy()
	env["XMLLINT_INDENT"] = "\t"

	if single_lines:
		xhtml = xhtml.replace("\n", " ")
		xhtml = regex.sub(r"\s{2,}", " ", xhtml) # Use this instead of \s+, because \s+ will replace special white space (like hair space or nbsp) with a regular space.

	if is_metadata_file:
		# Replace html entities in the long description so we can clean it too.
		# We re-establish them later.
		xhtml = xhtml.replace("&lt;", "<")
		xhtml = xhtml.replace("&gt;", ">")
	else:
		# Epub3 doesn't allow named entities, so convert them to their unicode equivalents
		# But, don't unescape the content.opf long-description accidentally
		xhtml = regex.sub(r"&#?\w+;", _replace_character_references, xhtml)

	# Remove unnecessary doctypes which can cause xmllint to hang
	xhtml = regex.sub(r"<!DOCTYPE[^>]+?>", "", xhtml, flags=regex.DOTALL)

	# Remove spaces and newlines before <br/>. We do his before using xmllint, because
	# in some cases (like poetry) we want the <br/>s on separate lines; but in other cases (like
	# line breaks in a flow-level element) we don't.
	xhtml = regex.sub(r"\s*<br/?>(\s*<br/>)?", "<br/>", xhtml, flags=regex.DOTALL)

	# Clean up newlines before <span>s, and white space inside <span>s
	xhtml = regex.sub(r"<span([^>]*)>\s*", "<span\\1>", xhtml, flags=regex.DOTALL)
	xhtml = regex.sub(r"\s*</span>", "</span>", xhtml, flags=regex.DOTALL)

	# Canonicalize XHTML
	# Path arguments must be cast to string for Windows compatibility.
	result = subprocess.run([str(xmllint_path), "--c14n", "-"], input=xhtml.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

	xhtml = result.stdout.decode()
	try:
		error = result.stderr.decode().strip()

		if error:
			raise se.InvalidXhtmlException(f"`xmllint` says:\n{error.replace('-:', 'Line  ')}")
	except UnicodeDecodeError as ex:
		raise se.InvalidEncodingException(f"Invalid encoding; UTF-8 expected. Exception: {ex}")
	except Exception as ex:
		raise se.InvalidXhtmlException(f"Couldn’t parse file. Files must be in XHTML format, which is not the same as HTML. Exception: {ex}")

	# Add the XML header that xmllint stripped during c14n
	xhtml = f"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n{xhtml}"

	xhtml = xhtml.replace("encoding=\"UTF-8\"", "encoding=\"utf-8\"")

	xhtml = unicodedata.normalize("NFC", xhtml)

	# Pretty-print XML
	# Path arguments must be cast to string for Windows compatibility.
	xhtml = subprocess.run([str(xmllint_path), "--format", "-"], input=xhtml.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False).stdout.decode()

	# Remove white space between some tags
	xhtml = regex.sub(r"<p([^>]*?)>\s+([^<\s])", "<p\\1>\\2", xhtml, flags=regex.DOTALL)
	xhtml = regex.sub(r"([^>\s])\s+</p>", "\\1</p>", xhtml, flags=regex.DOTALL)

	# xmllint has problems with removing spacing between some inline HTML5 elements. Try to fix those problems here.
	xhtml = regex.sub(r"</(abbr|cite|i|span|time|em|a|b(?!r))><(abbr|cite|i|span|time|em|a|b(?!r))", "</\\1> <\\2", xhtml)

	# Try to fix inline elements directly followed by an <a> tag, unless that <a> tag is a noteref.
	xhtml = regex.sub(r"</(abbr|cite|i|span|time|em|b)><(a(?! href=\"[^\"]+?\" id=\"noteref\-))", "</\\1> <\\2", xhtml)

	# Two sequential inline elements, when they are the only children of a block, are indented. But this messes up spacing if the 2nd element is a noteref.
	xhtml = regex.sub(r"</(abbr|cite|i|span|time|em|b)>\s+<(a href=\"[^\"]+?\" id=\"noteref\-)", "</\\1><\\2", xhtml, flags=regex.DOTALL)

	# The above regex may have put a space before noterefs. Remove that here.
	xhtml = regex.sub(r"</(abbr|cite|i|span|time|em|a|b)>\s*<a class=\"epub-type-noteref\"", "</\\1><a class=\"epub-type-noteref\"", xhtml)

	# Try to work around an xmllint bug where <br/>\n\s+<span> becomes <br/><span>. Try to put it back on the right indent level here.
	xhtml = regex.sub(r"^(\t+)(.+?)<br/>([^\s\n])", "\\1\\2<br/>\n\\1\\3", xhtml, flags=regex.MULTILINE)

	# Try to fix <cite> tags running next to referrer <a> tags.
	if is_endnotes_file:
		xhtml = regex.sub(r"</cite>(<a href=\"[^\"]+?\" epub:type=\"backlink\")", "</cite> \\1", xhtml)

	if is_colophon_file:
		xhtml = regex.sub(r"\s*<br/>\s*", "<br/>\n\t\t\t", xhtml, flags=regex.DOTALL)

		section_xhtml = regex.findall(r"</header>(.+?)</section>", xhtml, flags=regex.DOTALL)
		if section_xhtml:
			section_xhtml = regex.sub(r"^\s*", "\t\t\t", section_xhtml[0], flags=regex.MULTILINE).strip()
			xhtml = regex.sub(r"</header>(.+?)</section>", f"</header>\n\t\t\t{section_xhtml}\n\t\t</section>", xhtml, flags=regex.DOTALL)

	if single_lines:
		# Attempt to pretty-print CSS, if we have any (like in cover.svg or titlepage.svg).
		css = regex.findall(r"<style type=\"text/css\">([^<]+?)</style>", xhtml, flags=regex.DOTALL)
		if css:
			# Note that we can't (yet) use a generic format_css function, because we rely
			# on the output of the single_lines flag to be structured in a particular way.
			# This algorithm can't handle arbitrarily-formatted CSS.
			css = css[0]

			css = css.replace("{ ", "{\n")
			css = css.replace(" }", "\n}\n\n")
			css = css.replace("; ", ";\n")

			css = regex.sub(r"^\s*(.+?){", "\t\t\\1{", css, flags=regex.MULTILINE)
			css = regex.sub(r"^\s*}", "\t\t}\n", css, flags=regex.MULTILINE)
			css = regex.sub(r"^([^{}]+?)$", "\t\t\t\\1", css, flags=regex.MULTILINE)

			css = f"\t\t{css.strip()}"

			xhtml = regex.sub(r"<style type=\"text/css\">([^<]+?)</style>", f"<style type=\"text/css\">\n{css}\n\t</style>", xhtml, flags=regex.DOTALL)

		# Attempt to pretty-print the long description, which has special formatting
		if "&lt;p&gt;" in xhtml:
			xhtml = xhtml.replace(" &lt;p&gt;", "\n\t\t\t&lt;p&gt;")
			xhtml = xhtml.replace("&lt;/p&gt; </meta>", "&lt;/p&gt;\n\t\t</meta>")

	# Clean the long description, if we can find it
	if is_metadata_file:
		long_description = regex.findall(r"<meta id=\"long-description\" property=\"se:long-description\" refines=\"#description\">(.+?)</meta>", xhtml, flags=regex.DOTALL)
		if long_description[0]:
			escaped_long_description = long_description[0].replace("<", "&lt;")
			escaped_long_description = escaped_long_description.replace(">", "&gt;")
			xhtml = xhtml.replace(long_description[0], escaped_long_description)

	# Almost done. Let's clean CSS in <style> elements, like we find in SVG files.
	matches = regex.findall(r"^(\s*)(<style[^>]*?>)(.+?)(</style>)", xhtml, flags=regex.DOTALL | regex.MULTILINE)
	for match in matches:
		css = format_css(match[2])
		# Indent the CSS one level deeper than the <style> element
		css = ''.join(match[0] + "\t" + line + "\n" for line in css.splitlines())
		css = css.strip("\n")
		css = regex.sub(r"^\s+$", "", css, flags=regex.MULTILINE) # Remove indents from lines that are just white space
		xhtml = xhtml.replace(f"{match[0]}{match[1]}{match[2]}{match[3]}", f"{match[0]}{match[1]}\n{css}\n{match[0]}{match[3]}")

	return xhtml

def _format_css_component_list(content: list, in_selector=False, in_paren_block=False) -> str:
	"""
	Helper function for CSS formatting that formats a series of CSS components, like the individual parts of a selector.

	INPUTS
	content: A list of component values generated by the tinycss2 library

	OUTPUTS
	A string of formatted CSS
	"""

	output = ""

	for token in content:
		if token.type == "ident":
			if output.endswith("| ") or output.endswith("|= ") or output.endswith("^= ") or output.endswith("~= ") or output.endswith("*= ") or output.endswith("|| "):
				output = output.rstrip()

			output += token.lower_value

		if token.type == "literal":
			if token.value == ":" and in_paren_block:
				output += token.value + " "
			elif token.value == ";":
				output = output.rstrip() + token.value + (" " if in_paren_block else "\n")
			elif token.value == ",":
				output = output.rstrip() + token.value + (" " if in_paren_block or not in_selector else "\n")
			elif token.value == "=":
				# >= and <= should be surrounded by spaces, but they aren't recognized as separate tokens in tinycss2 yet. These are typically
				# used in media queries.
				if output.endswith("< ") or output.endswith("> "):
					output = output.rstrip() + token.value + " "
				elif not in_paren_block:
					output += " " + token.value + " "
				else:
					output += token.value
			elif token.value == "*":
				if in_paren_block:
					output += " " + token.value + " "
				else:
					output += token.value
			elif token.value == "<" or token.value == ">" or token.value == "+" or token.value == "-" or token.value == "/":
				output += " " + token.value + " "
			elif token.value == "|" or token.value == "|=" or token.value == "^=" or token.value == "~=" or token.value == "*=" or token.value == "||":
				output = output.rstrip() + token.value
			else:
				output += token.value

		if token.type == "dimension":
			if token.representation == "0":
				output += "0"
			else:
				output += token.representation + token.lower_unit

		if token.type == "number":
			output += token.representation

		if token.type == "function":
			output += token.name + "(" + _format_css_component_list(token.arguments, in_selector, True) + ")"

		if token.type == "url":
			output += f"url(\"{token.value}\")"

		if token.type == "percentage":
			if token.representation == "0":
				output += "0"
			else:
				output += token.representation + "%"

		if token.type == "whitespace":
			output += " "

		if token.type == "hash":
			output += f"#{token.value}"

		if token.type == "string":
			output += f"\"{token.value}\""

		if token.type == "() block":
			output += f"({_format_css_component_list(token.content, in_selector, True)})"

		if token.type == "[] block":
			output += f"[{_format_css_component_list(token.content, in_selector, True)}]"

	# Collapse multiple spaces, and spaces at the start of lines
	output = regex.sub(r" +", " ", output)
	output = regex.sub(r"^ ", "", output, flags=regex.MULTILINE)

	# : can be valid as a naked pseudo-class (x y :first-child), or as a connected pseudo-class
	# (x y:first-child) but not like x y: first-child
	if not in_paren_block:
		output = output.replace(": ", ":")

	# Replace naked :pseudo-class selectors with *
	output = output.replace(" :", " *:")

	return output.strip()

def _format_css_rules(content: list, indent_level: int) -> str:
	"""
	Helper function for CSS formatting that formats a list of CSS selectors.

	INPUTS
	content: A list of component values generated by the tinycss2 library

	OUTPUTS
	A string of formatted CSS
	"""

	output = ""

	for token in tinycss2.parse_rule_list(content):
		if token.type == "error":
			raise se.InvalidCssException(token.message)

		if token.type == "qualified-rule":
			output += ("\t" * indent_level) + _format_css_component_list(token.prelude, True).replace("\n", "\n" + ("\t" * indent_level)) + "{\n" + _format_css_declarations(token.content, indent_level + 1) + "\n" + ("\t" * indent_level) + "}\n\n"

		if token.type == "at-rule":
			output += ("\t" * indent_level) + "@" + token.lower_at_keyword + " " + _format_css_component_list(token.prelude, True).replace("\n", " ") + "{\n" + _format_css_rules(token.content, indent_level + 1) + "\n" + ("\t" * indent_level) + "}\n\n"

		if token.type == "comment":
			# House style: If the comment starts with /* End, then attach it to the previous block
			if token.value.strip().lower().startswith("end"):
				output = output.rstrip() + "\n"

			output += ("\t" * indent_level) + "/* " + token.value.strip() + " */\n"

			if token.value.strip().lower().startswith("end"):
				output += "\n"

	return output.rstrip()

def _format_css_declarations(content: list, indent_level: int) -> str:
	"""
	Helper function for CSS formatting that formats a list of CSS properties, like `margin: 1em;`.

	INPUTS
	content: A list of component values generated by the tinycss2 library

	OUTPUTS
	A string of formatted CSS
	"""

	output = ""

	for token in tinycss2.parse_declaration_list(content):
		if token.type == "error":
			raise se.InvalidCssException(token.message)

		if token.type == "declaration":
			output += ("\t" * indent_level) + token.lower_name + ": "

			output += _format_css_component_list(token.value)

			if token.important:
				output += " !important"

			output += ";\n"

		if token.type == "comment":
			output = output.rstrip()
			if output == "":
				output += ("\t" * indent_level) + "/* " + token.value.strip() + " */\n"
			else:
				output += " /* " + token.value.strip() + " */\n"

	return output.rstrip()

def format_css(css: str) -> str:
	"""
	Format a string of CSS to house style.

	INPUTS
	css: A string of well-formed CSS

	OUTPUTS
	A string of formatted CSS
	"""

	css_header = ""
	css_body = ""

	for token in tinycss2.parse_stylesheet(css, skip_comments=False):
		if token.type == "error":
			raise se.InvalidCssException(token.message)

		if token.type == "at-rule":
			# These three (should) occur at the head of the CSS.
			if token.lower_at_keyword == "charset":
				css_header += "@" + token.lower_at_keyword + " \"" + token.prelude[1].value.lower() + "\";\n"

			if token.lower_at_keyword == "namespace":
				css_header += "@" + token.lower_at_keyword + " " + token.prelude[1].value + " \"" + token.prelude[3].value + "\";\n"

			if token.lower_at_keyword == "font-face":
				css_header += "\n@" + token.lower_at_keyword + "{\n" + _format_css_declarations(token.content, 1) + "\n}\n"

			# Unlike the previous items, these occur in the CSS body.
			if token.lower_at_keyword == "supports":
				css_body += "@" + token.lower_at_keyword + _format_css_component_list(token.prelude, False, True) + "{\n" + _format_css_rules(token.content, 1) + "\n}\n\n"

			if token.lower_at_keyword == "media":
				css_body += "@" + token.lower_at_keyword + " " + _format_css_component_list(token.prelude).replace("\n", " ", True) + "{\n" + _format_css_rules(token.content, 1) + "\n}\n\n"

		# Selectors, including their rules.
		# tinycss2 differentiates between selectors and their rules that are at the top level,
		# and selectors and rules in nested blocks (like @supports).
		if token.type == "qualified-rule":
			css_body += _format_css_component_list(token.prelude, True) + "{\n" + _format_css_declarations(token.content, 1) + "\n}\n\n"

		if token.type == "comment":
			# House style: If the comment starts with /* End, then attach it to the previous block
			if token.value.strip().lower().startswith("end"):
				css_body = css_body.rstrip() + "\n"

			css_body += "/* " + token.value.strip() + " */\n"

			if token.value.strip().lower().startswith("end"):
				css_body += "\n"

	output = (css_header + "\n" + css_body).strip() + "\n"

	# Do a quick regex to move parens next to media rules
	output = regex.sub(r"(@[a-z]+) \(", "\\1(", output)

	# Remove empty rules
	output = regex.sub(r"^\t*[^\{\}]+?\{\s*\}\n", "", output, flags=regex.DOTALL|regex.MULTILINE)

	return output

def remove_tags(text: str) -> str:
	"""
	Remove all HTML tags from a string.

	INPUTS
	text: Text that may have HTML tags

	OUTPUTS
	A string with all HTML tags removed
	"""

	return regex.sub(r"</?([a-z]+)[^>]*?>", "", text, flags=regex.DOTALL)

def get_ordinal(number: str) -> str:
	"""
	Given an string representing an integer, return a string of the integer followed by its ordinal, like "nd" or "rd".

	INPUTS
	number: A string representing an integer like "1" or "2"

	OUTPUTS
	A string of the integer followed by its ordinal, like "1st" or "2nd"
	"""

	value = int(number)
	return "%d%s" % (value, "tsnrhtdd"[(math.floor(value / 10) % 10 != 1) * (value % 10 < 4) * value % 10::4])

def titlecase(text: str) -> str:
	"""
	Titlecase a string according to SE house style.

	INPUTS
	text: The string to titlecase

	OUTPUTS
	A titlecased version of the input string
	"""

	text = pip_titlecase(text)

	# We make some additional adjustments here

	# Lowercase HTML tags that titlecase might have screwed up. We just lowercase the entire contents of the tag, including attributes,
	# since they're typically lowercased anyway. (Except for things like `alt`, but we won't be titlecasing images!)
	text = regex.sub(r"<(/?)([^>]+?)>", lambda result: "<" + result.group(1) + result.group(2).lower() + ">", text)

	# Lowercase leading "d', as in "Marie d'Elle"
	text = regex.sub(r"\bD’([A-Z]+?)", "d’\\1", text)

	# Lowercase "and", even if preceded by punctuation
	text = regex.sub(r"([^a-zA-Z]) (And|Or)\b", lambda result: result.group(1) + " " + result.group(2).lower(), text)

	# pip_titlecase capitalizes *all* prepositions preceded by parenthesis; we only want to capitalize ones that *aren't the first word of a subtitle*
	# OK: From Sergeant Bulmer (of the Detective Police) to Mr. Pendril
	# OK: Three Men in a Boat (To Say Nothing of the Dog)
	text = regex.sub(r"\((For|Of|To)(.*?)\)(.+?)", lambda result: "(" + result.group(1).lower() + result.group(2) + ")" + result.group(3), text)

	# Lowercase "and", if followed by a word-joiner
	regex_string = fr"\bAnd{se.WORD_JOINER}"
	text = regex.sub(regex_string, f"and{se.WORD_JOINER}", text)

	# Lowercase "in", if followed by a semicolon (but not words like "inheritance")
	text = regex.sub(r"\b; In\b", "; in", text)

	# Lowercase th', sometimes used poetically
	text = regex.sub(r"\b Th’ \b", " th’ ", text)

	# Uppercase words that begin compound words, like "to-night" (which might appear in poetry)
	text = regex.sub(r" ([a-z])([a-z]+\-)", lambda result: " " + result.group(1).upper() + result.group(2), text)

	# Lowercase "from", "with", as long as they're not the first word and not preceded by a parenthesis
	text = regex.sub(r"(?<!^)(?<!\()\b(From|With)\b", lambda result: result.group(1).lower(), text)

	# Capitalise the first word after an opening quote or italicisation that signifies a work
	text = regex.sub(r"(‘|“|<i.*?epub:type=\".*?se:.*?\".*?>)([a-z])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Lowercase "the" if preceded by "vs."
	text = regex.sub(r"(?:vs\.) The\b", "vs. the", text)

	# Lowercase "de", "von", "van", "le", as in "Charles de Gaulle", "Werner von Braun", etc., and if not the first word and not preceded by an &ldquo;
	text = regex.sub(r"(?<!^|“)\b(De|Von|Van|Le)\b", lambda result: result.group(1).lower(), text)

	# Uppercase word following "Or,", since it is probably a subtitle
	text = regex.sub(r"\bOr, ([a-z])", lambda result: "Or, " + result.group(1).upper(), text)

	# Fix html entities
	text = text.replace("&Amp;", "&amp;")

	# Lowercase etc.
	text = text.replace("Etc.", "etc.")

	return text

def make_url_safe(text: str) -> str:
	"""
	Return a URL-safe version of the input. For example, the string "Mother's Day" becomes "mothers-day".

	INPUTS
	text: A string to make URL-safe

	OUTPUTS
	A URL-safe version of the input string
	"""

	# 1. Convert accented characters to unaccented characters
	text = regex.sub(r"\p{M}", "", unicodedata.normalize("NFKD", text))

	# 2. Trim
	text = text.strip()

	# 3. Convert title to lowercase
	text = text.lower()

	# 4. Remove apostrophes
	text = regex.sub(r"['‘’]", "", text)

	# 5. Convert any non-digit, non-letter character to a space
	text = regex.sub(r"[^0-9a-z]", " ", text, flags=regex.IGNORECASE)

	# 6. Convert any instance of one or more space to a dash
	text = regex.sub(r"\s+", "-", text)

	# 7. Remove trailing dashes
	text = regex.sub(r"\-+$", "", text)

	return text

def namespace_to_class(selector: str) -> str:
	"""
	Helper function to remove namespace selectors from a single selector, and replace them with class names.

	INPUTS
	selector: A single CSS selector

	OUTPUTS
	A string representing the selector with namespaces replaced by classes
	"""

	# First, remove periods from epub:type.  We can't remove periods in the entire selector because there might be class selectors involved
	epub_type = regex.search(r"\"[^\"]+?\"", selector).group()
	if epub_type:
		selector = selector.replace(epub_type, epub_type.replace(".", "-"))

	# Now clean things up
	return selector.replace(":", "-").replace("|", "-").replace("~=", "-").replace("[", ".").replace("]", "").replace("\"", "")

def simplify_css(css: str) -> str:
	"""
	Helper function to simplify a block of CSS for improved cross-ereader compatibility.

	INPUTS
	css: A string containing any number of CSS selectors and rules

	OUTPUTS
	A string representing the simplified CSS
	"""

	# First we replace some more "complex" selectors (like :first-child) with an equivalent class (like .first-child), since ADE doesn't handle them
	# Currently this replacement isn't perfect, because occasionally lxml generates an xpath expression
	# from the css selector that lxml itself can't evaluate, even though the `xpath` binary can!
	# We don't *replace* the selector, we *add* it, because lxml has problems selecting first-child sometimes
	lines = css.splitlines()
	simplified_lines = []
	for line in lines:
		simplified_line = line
		for selector_to_simplify in se.SELECTORS_TO_SIMPLIFY:
			while selector_to_simplify in simplified_line:
				split_selector = regex.split(fr"({selector_to_simplify}(\(.*?\))?)", simplified_line, 1)
				replacement_class = split_selector[1].replace(":", ".").replace("(", "-").replace("n-", "n-minus-").replace("n+", "n-plus-").replace(")", "")
				simplified_line = simplified_line.replace(split_selector[1], replacement_class)
		if simplified_line != line:
			line = simplified_line + ",\n" + line
		simplified_lines.append(line)
	css = "\n".join(simplified_lines)

	css = css.replace("{,", ",")
	css = css.replace(",,", ",")

	# Now replace abbr styles with spans, because ADE screws up with unrecognized elements
	css = css.replace("abbr", "span")

	# Replace shorthand CSS with longhand properties, another ADE screwup
	css = regex.sub(r"margin:\s*([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\1;\n\tmargin-bottom: \\1;\n\tmargin-left: \\1;", css)
	css = regex.sub(r"margin:\s*([^\s]+?)\s+([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\2;\n\tmargin-bottom: \\1;\n\tmargin-left: \\2;", css)
	css = regex.sub(r"margin:\s*([^\s]+?)\s+([^\s]+?)\s+([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\2;\n\tmargin-bottom: \\3;\n\tmargin-left: \\2;", css)
	css = regex.sub(r"margin:\s*([^\s]+?)\s+([^\s]+?)\s+([^\s]+?)\s+([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\2;\n\tmargin-bottom: \\3;\n\tmargin-left: \\4;", css)

	# Replace some more poorly-supported CSS attributes
	css = css.replace("all-small-caps;", "small-caps;\n\ttext-transform: lowercase;")

	# Replace CSS namespace selectors with classes
	# For example, p[epub|type~="z3998:salutation"] becomes p.epub-type-z3998-salutation
	for line in regex.findall(r"\[epub\|type\~\=\"[^\"]*?\"\]", css):
		fixed_line = namespace_to_class(line)
		css = css.replace(line, fixed_line)

	return css


def generate_title(xhtml: str) -> str:
	"""
	Generate the value for the <title> tag of a string of XHTML, based on the rules in the SE manual.

	INPUTS
	xhtml: A string of XHTML

	OUTPUTS
	A string representing the title for the document
	"""

	soup = BeautifulSoup(xhtml, "lxml")
	title = ""

	h_elements = soup.select("h1:first-of-type,h2:first-of-type,h3:first-of-type,h4:first-of-type,h5:first-of-type,h6:first-of-type")

	if h_elements:
		h_element = h_elements[0]

		# se://5.3.2.2
		# Header is just a Roman numeral
		if h_element.has_attr("epub:type") and "z3998:roman" in h_element["epub:type"]:
			title = f"Chapter {roman.fromRoman(h_element.text.upper())}"

		# Otherwise, iterate over the h# children to determine how we should generate the title
		for h_child in h_element.contents:
			if isinstance(h_child, Tag) and h_child.name == "span":
				if h_child.has_attr("epub:type"):
					if "z3998:roman" in h_child["epub:type"]:
						title = f"Chapter {roman.fromRoman(h_child.text.upper())}"

					if "subtitle" in h_child["epub:type"]:
						title += f": {h_child.text}"
				else:
					if len(h_child.contents) > 1:
						for span_child in h_child.contents:
							if isinstance(span_child, Tag) and span_child.name == "span":
								if span_child.has_attr("epub:type") and "z3998:roman" in span_child["epub:type"]:
									title += str(roman.fromRoman(span_child.text.upper()))
								else:
									title += span_child.text
							elif isinstance(span_child, NavigableString) and not span_child.isspace():
								title += span_child
					else:
						title = h_child.text
			elif isinstance(h_child, Tag) and h_child.name == "abbr":
				title += h_child.text
			elif isinstance(h_child, NavigableString) and not h_child.isspace():
				title += h_child
	else:
		# No <h#> elements found. Try to get the title from the epub:type of the top-level <section> or <article>
		top_level_wrappers = soup.select("body > section, body > article")

		if top_level_wrappers:
			top_level_wrapper = top_level_wrappers[0]

			# Only guess the title if there is a single value for epub:type
			if top_level_wrapper.has_attr("epub:type") and " " not in top_level_wrapper["epub:type"]:
				title = titlecase(top_level_wrapper["epub:type"])

	return title.strip()
