#!/usr/bin/env python3
"""
Defines functions useful for formatting code or text according to SE standards, for calculating
several text-level statistics like reading ease, and for adding semantics.
"""

import html.entities
import math
import string
import unicodedata
from pathlib import Path

import regex
import roman
import tinycss2
from bs4 import BeautifulSoup, NavigableString, Tag
from lxml import etree
from titlecase import titlecase as pip_titlecase
#from se.vendor.titlecase import titlecase as pip_titlecase

import se


# This list of phrasing tags is not intended to be exhaustive. The list is only used
# to resolve the uncommon situation where there is no plain text in a paragraph. The
# span and br tags are explicitly omitted because of how they are used in poetry formatting,
# which differs from the normal formatting.

PHRASING_TAGS = [
	"{http://www.w3.org/1999/xhtml}a",
	"{http://www.w3.org/1999/xhtml}abbr",
	"{http://www.w3.org/1999/xhtml}b",
	"{http://www.w3.org/1999/xhtml}cite",
	"{http://www.w3.org/1999/xhtml}em",
	"{http://www.w3.org/1999/xhtml}i",
	"{http://www.w3.org/1999/xhtml}strong",
]

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
	xhtml = regex.sub(r"(?<!\<abbr\>)Bros\.", r"<abbr>Bros.</abbr>", xhtml)
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
	xhtml = regex.sub(r"(?<!\<abbr[^\>]*?\>)(P\.(?:P\.)?S\.(?:S\.)?)", r"""<abbr class="initialism">\1</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Co\.", r"<abbr>Co.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Inc\.", r"<abbr>Inc.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)Ltd\.", r"<abbr>Ltd.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)St\.", r"<abbr>St.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)MS(S?)\.", r"""<abbr class="initialism">MS\1.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)([Vv])iz\.", r"<abbr>\1iz.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)etc\.", r"\1<abbr>etc.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)([Cc])f\.", r"\1<abbr>\2f.</abbr>", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)p\.([\s0-9])", r"\1<abbr>p.</abbr>\2", xhtml)
	xhtml = regex.sub(r"(\b)(?<!\<abbr\>)ed\.", r"\1<abbr>ed.</abbr>", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="initialism"\>)([Ii])\.e\.""", r"""<abbr class="initialism">\1.e.</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="initialism"\>)([Ee])\.g\.""", r"""<abbr class="initialism">\1.g.</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="initialism"\>)\bN\.?B\.\b""", r"""<abbr class="initialism">N.B.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)(Jan\.|Feb\.|Mar\.|Apr\.|Jun\.|Jul\.|Aug\.|Sep\.|Sept\.|Oct\.|Nov\.|Dec\.)", r"<abbr>\1</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)No\.(\s+[0-9]+)", r"<abbr>No.</abbr>\1", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="degree"\>)PhD""", r"""<abbr class="degree">PhD</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="initialism"\>)I\.?O\.?U\.?\b""", r"""<abbr class="initialism">I.O.U.</abbr>""", xhtml)
	xhtml = regex.sub(r"""\b(?<!\<abbr class="era"\>)A\.?D""", r"""<abbr class="era">AD</abbr>""", xhtml)
	xhtml = regex.sub(r"""\b(?<!\<abbr class="era"\>)B\.?C""", r"""<abbr class="era">BC</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="time( eoc)?"\>)([ap])\.\s?m\.""", r"""<abbr class="time">\2.m.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!\<abbr\>)([Vv])s\.", r"<abbr>\1s.</abbr>", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="name"\>)Thos\.""", r"""<abbr class="name">Thos.</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="name"\>)Jas\.""", r"""<abbr class="name">Jas.</abbr>""", xhtml)
	xhtml = regex.sub(r"""(?<!\<abbr class="name"\>)Chas\.""", r"""<abbr class="name">Chas.</abbr>""", xhtml)

	# Wrap £sd shorthand
	xhtml = regex.sub(r"([0-9½¼⅙⅚⅛⅜⅝]+)([sd⅞]\.)", r"\1<abbr>\2</abbr>", xhtml)

	# Guess at adding eoc (End Of Clause) class
	xhtml = regex.sub(r"""<abbr>([\p{Letter}\.]+?\.)</abbr></p>""", r"""<abbr class="eoc">\1</abbr></p>""", xhtml)
	xhtml = regex.sub(r"""<abbr class="(.+?)">([\p{Letter}\.]+?\.)</abbr></p>""", r"""<abbr class="\1 eoc">\2</abbr></p>""", xhtml)
	xhtml = regex.sub(r"""<abbr>etc\.</abbr>(\s+[\p{Uppercase_Letter}])""", r"""<abbr class="eoc">etc.</abbr>\1""", xhtml)
	xhtml = regex.sub(r"""<abbr>etc\.</abbr>(”?)</p>""", r"""<abbr class="eoc">etc.</abbr>\1</p>""", xhtml)

	# We may have added eoc classes twice, so remove duplicates here
	xhtml = regex.sub(r"""<abbr class="(.*) eoc(\s+eoc)+">""", r"""<abbr class="\1 eoc">""", xhtml)

	# Clean up nesting errors
	xhtml = regex.sub(r"""<abbr class="eoc"><abbr>([^<]+)</abbr></abbr>""", r"""<abbr class="eoc">\1</abbr>""", xhtml)
	xhtml = regex.sub(r"""class="eoc eoc""", r"""class="eoc""", xhtml)

	# Get Roman numerals >= 2 characters
	# We only wrap these if they're standalone (i.e. not already wrapped in a tag) to prevent recursion in multiple runs
	xhtml = regex.sub(r"([^\p{Letter}>])([ixvIXV]{2,})(\b|st\b|nd\b|rd\b|th\b)", r"""\1<span epub:type="z3998:roman">\2</span>\3""", xhtml)

	# Get Roman numerals that are X or V and single characters.  We can't do I for obvious reasons.
	xhtml = regex.sub(r"""([^\p{Letter}>\"])([vxVX])(\b|st\b|nd\b|rd\b|th\b)""", r"""\1<span epub:type="z3998:roman">\2</span>\3""", xhtml)

	# Add abbrevations around some SI measurements
	xhtml = regex.sub(r"([0-9]+)\s*([cmk][mgl])\b", fr"\1{se.NO_BREAK_SPACE}<abbr>\2</abbr>", xhtml)

	# Add abbrevations around Imperial measurements
	xhtml = regex.sub(r"([0-9]+)\s*(ft|in|yd|mi|pt|qt|gal|oz|lbs)\.?\b", fr"\1{se.NO_BREAK_SPACE}<abbr>\2.</abbr>", xhtml)

	# Tweak some other Imperial measurements
	xhtml = regex.sub(r"([0-9]+)\s*m\.?p\.?h\.?", fr"\1{se.NO_BREAK_SPACE}<abbr>mph</abbr>", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([0-9]+)\s*h\.?p\.?", fr"\1{se.NO_BREAK_SPACE}<abbr>hp</abbr>", xhtml, flags=regex.IGNORECASE)

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
	xhtml = regex.sub(r"[\p{Letter}0-9][\-\'\,\.\/][\p{Letter}0-9]", "aa", xhtml, flags=regex.IGNORECASE | regex.DOTALL)

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

def _indent(tree, space="\t"):
	"""
	Indent an lxml tree using the given space characters.
	"""

	if len(tree) > 0:
		level = 0
		indentation = "\n" + level * space
		_indent_children(tree, 1, space, [indentation, indentation + space])
	else:
		tree.text = "\n"

def _indent_children(elem, level, one_space, indentations, has_child_tails=False):
	"""
	Recursive helper function implementing indent levels for lxml tree.
	"""

	# Reuse indentation strings for speed.
	if len(indentations) <= level:
		indentations.append(indentations[-1] + one_space)

	# Start a new indentation level for the first child.
	child_indentation = indentations[level]

	# Check if any children have tail content
	if not has_child_tails:
		if len(elem) > 0 and elem.text and not regex.match(r"^[\n\t ]+$", elem.text):
			has_child_tails = True
		else:
			for child in elem:
				if child.tail and not regex.match(r"^\n\s*$", child.tail):
					has_child_tails = True
					break

	# If elem text is empty, start a new indentation level
	if not elem.text or regex.match(r"^[\n\t ]+$", elem.text):
		if has_child_tails:
			elem.text = ""
		else:
			elem.text = child_indentation
	else:
		_unwrap_text(elem, remove_trailing_space=False)

	# Recursively indent all children.
	for child in elem:
		if len(child) > 0:
			if has_child_tails:
				next_level = level
			else:
				next_level = level + 1
			_indent_children(child, next_level, one_space, indentations, has_child_tails)

		next_child = child.getnext()

		# Remove line wraps from child text (except meta tags)
		if child.text and not regex.match(r"^[\n\t ]+$", child.text):
			if child.tag is etree.Comment:
				child.text = regex.sub(r" *\n\s*", child_indentation, child.text)
			elif child.tag != "{http://www.idpf.org/2007/opf}meta":
				_unwrap_text(child, remove_trailing_space=True)

		# Handle different cases for indentation in child tail content
		if not child.tail or regex.match(r"^\n\s*$", child.tail):
			if next_child is None:
				if has_child_tails:
					child.tail = ""
				else:
					child_indentation = indentations[level - 1]
					child.tail = child_indentation
			elif child.tag == "{http://www.w3.org/1999/xhtml}br":
				if has_child_tails:
					child_indentation = indentations[level - 1]
				child.tail = child_indentation
			elif not has_child_tails and next_child.tag == "{http://www.w3.org/1999/xhtml}br":
				child.tail = child_indentation
			elif not has_child_tails and not child.tail and next_child.tag in PHRASING_TAGS:
				child.tail = ""
			elif has_child_tails:
				child.tail = ""
			else:
				child.tail = child_indentation
		else:
			# Remove line wraps in child tail
			_unwrap_tail(child, remove_trailing_space=next_child is None)
			# Add special indentation for br tag with non-empty tail
			if child.tag == "{http://www.w3.org/1999/xhtml}br":
				child_indentation = indentations[level - 1]
				child.tail = child_indentation + child.tail

def _unwrap_text(elem: etree.Element, remove_trailing_space: bool):
	"""
	Remove line wraps from text content of element.
	"""
	elem.text = regex.sub(r"^\n\s*", "", elem.text)
	if remove_trailing_space:
		elem.text = regex.sub(r"\n\s*$", "", elem.text)
	elem.text = regex.sub(r" *\n\s*", " ", elem.text)

def _unwrap_tail(elem: etree.Element, remove_trailing_space: bool):
	"""
	Remove line wraps from tail content of element.
	"""
	if elem.tag == "{http://www.w3.org/1999/xhtml}br":
		elem.tail = regex.sub(r"^\n\s*", "", elem.tail)
	else:
		elem.tail = regex.sub(r"^\n\s*", " ", elem.tail)
	if remove_trailing_space:
		elem.tail = regex.sub(r"\n\s*$", "", elem.tail)
	elem.tail = regex.sub(r" *\n\s*", " ", elem.tail)

def format_xml_file(filename: Path) -> None:
	"""
	Pretty-print well-formed XML and save to file.
	Detects if the filename is XHTML, SVG, OPF, or plain XML and adjusts formatting accordingly.

	INPUTS
	filename: A file containing well-formed XML

	OUTPUTS
	None.
	"""

	with open(filename, "r+", encoding="utf-8") as file:
		xml = file.read()

		if filename.suffix == ".xhtml":
			processed_xml = se.formatting.format_xhtml(xml)
		elif filename.suffix == ".svg":
			processed_xml = se.formatting.format_svg(xml)
		elif filename.suffix == ".opf":
			processed_xml = se.formatting.format_opf(xml)
		else:
			processed_xml = se.formatting.format_xml(xml)
		if processed_xml != xml:
			file.seek(0)
			file.write(processed_xml)
			file.truncate()

def _format_style_elements(tree: etree.ElementTree):
	"""
	Find <style> elements in an XML etree, and pretty-print the CSS inside of them.
	The passed tree is modified in-place.

	INPUTS
	tree: An XML etree.

	OUTPUTS
	None.
	"""

	try:
		for node in tree.xpath("//svg:style", namespaces={"xhtml": "http://www.w3.org/1999/xhtml", "svg": "http://www.w3.org/2000/svg"}):
			css = format_css(node.text)

			# Get the <style> element's indentation
			indent = node.xpath("preceding-sibling::text()[1]")[0].replace("\n", "")

			# Indent the CSS one level deeper than the <style> element
			css = ''.join(indent + "\t" + line + "\n" for line in css.splitlines())
			css = css.strip("\n")
			css = regex.sub(r"^\s+$", "", css, flags=regex.MULTILINE) # Remove indents from lines that are just white space

			node.text = "\n" + css + "\n" + indent
	except se.InvalidCssException as ex:
		raise ex
	except Exception as ex:
		raise se.InvalidCssException(f"Couldn’t parse CSS. Exception: {ex}")

def _format_xml_str(xml: str) -> etree.ElementTree:
	"""
	Given a string of well-formed XML, return a pretty-printed etree.

	INPUTS
	xml: A string of well-formed XML.

	OUTPUTS
	An etree representing the pretty-printed XML.
	"""

	tree = etree.fromstring(str.encode(xml))
	canonical_bytes = etree.tostring(tree, method="c14n")
	tree = etree.fromstring(canonical_bytes)
	_indent(tree, space="\t")

	return tree

def _xml_tree_to_string(tree: etree.ElementTree) -> str:
	"""
	Given an XML etree, return a string representing the etree's XML.

	INPUTS
	tree: An XML etree.

	OUTPUTS
	A string representing the etree's XML.
	"""

	xml = """<?xml version="1.0" encoding="utf-8"?>\n""" + etree.tostring(tree, encoding="unicode") + "\n"

	# Normalize unicode characters
	xml = unicodedata.normalize("NFC", xml)

	return xml

def format_xml(xml: str) -> str:
	"""
	Pretty-print well-formed XML.

	INPUTS
	xml: A string of well-formed XML.

	OUTPUTS
	A string of pretty-printed XML.
	"""

	try:
		tree = _format_xml_str(xml)
	except Exception as ex:
		raise se.InvalidXmlException(f"Couldn’t parse XML file. Exception: {ex}")

	return _xml_tree_to_string(tree)

def format_xhtml(xhtml: str) -> str:
	"""
	Pretty-print well-formed XHTML.

	INPUTS
	xhtml: A string of well-formed XHTML

	OUTPUTS
	A string of pretty-printed XHTML.
	"""

	# Epub3 doesn't allow named entities, so convert them to their unicode equivalents
	# But, don't unescape the content.opf long-description accidentally
	xhtml = regex.sub(r"&#?\w+;", _replace_character_references, xhtml)

	# Remove unnecessary doctypes which can cause xmllint to hang
	xhtml = regex.sub(r"<!DOCTYPE[^>]+?>", "", xhtml, flags=regex.DOTALL)

	# Remove white space between opening/closing tag and text nodes
	# We do this first so that we can still format line breaks after <br/>
	# Exclude comments
	xhtml = regex.sub(r"(<(?:[^!/][^>]*?[^/]|[a-z])>)\s+([^\s<])", r"\1\2", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([^\s>])\s+(</[^>]+?>)", r"\1\2", xhtml, flags=regex.IGNORECASE)

	try:
		tree = _format_xml_str(xhtml)
	except Exception as ex:
		raise se.InvalidXhtmlException(f"Couldn’t parse XHTML file. Exception: {ex}")

	# Lowercase attribute names
	for node in tree.xpath("//*[attribute::*[re:test(local-name(), '[A-Z]')]]", namespaces=se.XHTML_NAMESPACES):
		for key, value in node.items(): # Iterate over attributes
			node.attrib.pop(key) # Remove the attribute
			node.attrib[key.lower()] = value # Re-add the attribute, lowercased

	# Lowercase tag names
	for node in tree.xpath("//*[re:test(local-name(), '[A-Z]')]", namespaces=se.XHTML_NAMESPACES):
		node.tag = node.tag.lower()

	# Format <style> elements
	_format_style_elements(tree)

	# Remove white space between non-tags and <br/>
	xhtml = regex.sub(r"([^>\s])\s+<br/>", r"\1<br/>", _xml_tree_to_string(tree))

	return xhtml

def format_opf(xml: str) -> str:
	"""
	Pretty-print well-formed OPF XML.

	INPUTS
	xml: A string of well-formed OPF XML

	OUTPUTS
	A string of pretty-printed XML.
	"""

	# Replace html entities in the long description so we can clean it too.
	# We re-establish them later. Don't use html.unescape because that will unescape
	# things like &amp; which would make an invalid XML document. (&amp; may appear in translator info,
	# or other parts of the metadata that are not the long description.
	xml = xml.replace("&lt;", "<")
	xml = xml.replace("&gt;", ">")
	xml = xml.replace("&amp;amp;", "&amp;") # Unescape escaped ampersands, which appear in the long description only

	# Canonicalize and format XML
	try:
		tree = _format_xml_str(xml)
	except Exception as ex:
		raise se.InvalidXmlException(f"Couldn’t parse OPF file. Exception: {ex}")

	# Format the long description, then escape it
	for node in tree.xpath("/opf:package/opf:metadata/opf:meta[@property='se:long-description']", namespaces={"opf": "http://www.idpf.org/2007/opf"}):
		# Convert the node contents to escaped text.
		xhtml = node.text # This preserves the initial newline and indentation

		if xhtml is None:
			xhtml = ""

		for child in node:
			xhtml += etree.tostring(child, encoding="unicode")

		# After composing the string, lxml adds namespaces to every tag. The only way to remove them is with regex.
		xhtml = regex.sub(r"\sxmlns(:.+?)?=\"[^\"]+?\"", "", xhtml)

		# Remove the children so that we can replace them with the escaped xhtml
		for child in node:
			node.remove(child)

		node.text = xhtml

	return _xml_tree_to_string(tree)

def format_svg(svg: str) -> str:
	"""
	Pretty-print well-formed SVG XML.

	INPUTS
	svg: A string of well-formed SVG XML.

	OUTPUTS
	A string of pretty-printed SVG XML.
	"""

	try:
		tree = _format_xml_str(svg)
	except Exception as ex:
		raise se.InvalidXmlException(f"Couldn’t parse SVG file. Exception: {ex}")

	# Make sure viewBox is correctly-cased
	for node in tree.xpath("/svg:svg", namespaces={"svg": "http://www.w3.org/2000/svg"}):
		for key, value in node.items(): # Iterate over attributes
			if key.lower() == "viewbox":
				node.attrib.pop(key) # Remove the attribute
				node.attrib["viewBox"] = value # Re-add the attribute, correctly-cased
				break

	# Format <style> elements
	_format_style_elements(tree)

	return _xml_tree_to_string(tree)

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
			raise se.InvalidCssException("Couldn’t parse CSS. Exception: {token.message}")

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
			raise se.InvalidCssException("Couldn’t parse CSS. Exception: {token.message}")

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
	output = regex.sub(r"(@[\p{Letter}]+) \(", "\\1(", output)

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

	return regex.sub(r"</?[\p{Letter}]+[^>]*?>", "", text, flags=regex.DOTALL)

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

	# For some reason, pip_titlecase() doesn't do anything if the string is mostly (but not all) uppercase.
	# For example "STOPPING BY WOODS ON a SNOWY EVENING" would not be changed by pip_titlecase()
	# So, convert to all lowercase first.
	text = text.lower()

	text = pip_titlecase(text)

	# We make some additional adjustments here

	# Lowercase HTML tags that titlecase might have screwed up. We just lowercase the entire contents of the tag, including attributes,
	# since they're typically lowercased anyway. (Except for things like `alt`, but we won't be titlecasing images!)
	text = regex.sub(r"<(/?)([^>]+?)>", lambda result: "<" + result.group(1) + result.group(2).lower() + ">", text)

	# Uppercase Roman numerals, but only if they are valid Roman numerals
	try:
		text = regex.sub(r"(\s)([ivxlcdm]+)(\s|$)", lambda result: result.group(1) + result.group(2).upper() + result.group(3) if roman.fromRoman(result.group(2).upper()) else result.group(2), text, flags=regex.IGNORECASE)
	except roman.InvalidRomanNumeralError:
		pass

	# Lowercase "and" and "or", even if preceded by punctuation
	text = regex.sub(r"([^\p{Letter}]) (And|Or)\b", lambda result: result.group(1) + " " + result.group(2).lower(), text)

	# pip_titlecase capitalizes *all* prepositions preceded by parenthesis; we only want to capitalize ones that *aren't the first word of a subtitle*
	# OK: From Sergeant Bulmer (of the Detective Police) to Mr. Pendril
	# OK: Three Men in a Boat (To Say Nothing of the Dog)
	text = regex.sub(r"\((For|Of|To)(.*?)\)(.+?)", lambda result: "(" + result.group(1).lower() + result.group(2) + ")" + result.group(3), text)

	# Uppercase words preceded by en or em dash
	text = regex.sub(fr"([—–]{se.WORD_JOINER}?)([\p{{Lowercase_Letter}}])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Lowercase "and", if it's not the very first word, and not preceded by an em-dash
	text = regex.sub(r"(?<!^)\bAnd\b", r"and", text)

	# Lowercase "in", if followed by a semicolon (but not words like "inheritance")
	text = regex.sub(r"\b; In\b", "; in", text)

	# Lowercase th', sometimes used poetically
	text = regex.sub(r"\b Th’ \b", " th’ ", text)

	# Uppercase words that begin compound words, like "to-night" (which might appear in poetry)
	text = regex.sub(r" ([\p{Lowercase_Letter}])([\p{Lowercase_Letter}]+\-)", lambda result: " " + result.group(1).upper() + result.group(2), text)

	# Lowercase "from", "with", as long as they're not the first word and not preceded by a parenthesis
	text = regex.sub(r"(?<!^)(?<!\()\b(From|With)\b", lambda result: result.group(1).lower(), text)

	# Capitalise the first word after an opening quote or italicisation that signifies a work
	text = regex.sub(r"(‘|“|<i.*?epub:type=\".*?se:.*?\".*?>)([\p{Lowercase_Letter}])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Lowercase "the" if preceded by "vs."
	text = regex.sub(r"(?:vs\.) The\b", "vs. the", text)

	# Lowercase "de", "von", "van", "le", as in "Charles de Gaulle", "Werner von Braun", etc., and if not the first word and not preceded by an &ldquo;
	text = regex.sub(r"(?<!^|“)\b(De|Von|Van|Le)\b", lambda result: result.group(1).lower(), text)

	# Uppercase word following "Or,", since it is probably a subtitle
	text = regex.sub(r"\bOr, ([\p{Lowercase_Letter}])", lambda result: "Or, " + result.group(1).upper(), text)

	# Uppercase word following ":", except "or, ", which indicates a kind of subtitle
	text = regex.sub(r": ([\p{Lowercase_Letter}])(?!r, )", lambda result: ": " + result.group(1).upper(), text)

	# Uppercase words after an initial contraction, like O'Keefe or L'Affaire. But only if there's at least 3 letters
	# after, to prevent catching things like I'm or E're
	text = regex.sub(r"\b([\p{Uppercase_Letter}]’)([\p{Lowercase_Letter}])([\p{Letter}]{2,})", lambda result: result.group(1) + result.group(2).upper() + result.group(3), text)

	# Uppercase letter after Mc
	text = regex.sub(r"\bMc([\p{Lowercase_Letter}])", lambda result: "Mc" + result.group(1).upper(), text)

	# Uppercase first letter after beginning contraction
	text = regex.sub(r"(\s|^)(’[\p{Lowercase_Letter}])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Uppercase first letter
	text = regex.sub(r"^(\p{Lowercase_Letter}])", lambda result: result.group(1).upper(), text)

	# Lowercase 'by'
	text = regex.sub(r"(\s)By(\s|%)", lambda result: result.group(1) + "by" + result.group(2), text)

	# Lowercase leading "d', as in "Marie d'Elle"
	text = regex.sub(r"(?:\b|^)D’([\p{Letter}])", lambda result: "d’" + result.group(1).upper(), text)

	# # Uppercase letter after leading "L', as in "L'Affaire"
	# text = regex.sub(r"(?:\b|^)L’([\p{Letter}])", lambda result: "L’" + result.group(1).upper(), text)

	# Uppercase some known initialisms
	text = regex.sub(r"(\s|^)(sos|md)(?:\b|$)", lambda result: result.group(1) + result.group(2).upper(), text, flags=regex.IGNORECASE)
	text = regex.sub(r"(\s)(bc|ad)(?:\b|$)", lambda result: result.group(1) + result.group(2).upper(), text, flags=regex.IGNORECASE)

	# Lowercase À (as in À La Carte) unless it's the first word
	text = regex.sub(r"(?<!^)\bÀ\b", "à", text)

	# Uppercase initialisms
	text = regex.sub(r"(\s)(([\p{Letter}]\.)+)", lambda result: result.group(1) + result.group(2).upper(), text)

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
	text = regex.sub(r"[^0-9\p{Letter}]", " ", text, flags=regex.IGNORECASE)

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

		# Strip any endnote references first
		for endnote_tag in h_element.select("[id^='noteref']"):
			endnote_tag.decompose()

		# semos://1.0.0/5.3.2.2
		# Header is just a Roman numeral
		if h_element.has_attr("epub:type") and "z3998:roman" in h_element["epub:type"]:
			title = f"Chapter {roman.fromRoman(h_element.text.upper())}"

		# Otherwise, iterate over the h# children to determine how we should generate the title
		else:
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
