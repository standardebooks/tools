#!/usr/bin/env python3
"""
Defines functions useful for formatting code or text according to SE standards, for calculating
several text-level statistics like reading ease, and for adding semantics.
"""

from copy import deepcopy
import html.entities
import math
import string
import unicodedata
from pathlib import Path
from typing import Dict, Union, List, Tuple, Optional

import regex
import roman
import tinycss2
from lxml import etree
from titlecase import titlecase as pip_titlecase
from unidecode import unidecode

import se
from se.easy_xml import EasyXmlTree, EasyXmlElement


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
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mr\.", r"""<abbr epub:type="z3998:name-title">Mr.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mrs\.", r"""<abbr epub:type="z3998:name-title">Mrs.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Ms\.", r"""<abbr epub:type="z3998:name-title">Ms.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Dr\.", r"""<abbr epub:type="z3998:name-title">Dr.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Drs\.", r"""<abbr epub:type="z3998:name-title">Drs.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Prof\.", r"""<abbr epub:type="z3998:name-title">Prof.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Rev\.", r"""<abbr epub:type="z3998:name-title">Rev.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Hon\.", r"""<abbr epub:type="z3998:name-title">Hon.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Lieut\.", r"""<abbr epub:type="z3998:name-title">Lieut.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Fr\.", r"""<abbr epub:type="z3998:name-title">Fr.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Lt\.", r"""<abbr epub:type="z3998:name-title">Lt.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Capt\.", r"""<abbr epub:type="z3998:name-title">Capt.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Pvt\.", r"""<abbr epub:type="z3998:name-title">Pvt.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Esq\.", r"""<abbr epub:type="z3998:name-title">Esq.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Bros\.", r"<abbr>Bros.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mt\.", r"<abbr>Mt.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))MM\.", r"""<abbr epub:type="z3998:name-title">MM.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mme\.", r"""<abbr epub:type="z3998:name-title">Mme.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mmes\.", r"""<abbr epub:type="z3998:name-title">Mmes.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mon\.", r"""<abbr epub:type="z3998:name-title">Mon.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mlle\.", r"""<abbr epub:type="z3998:name-title">Mlle.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mdlle\.", r"""<abbr epub:type="z3998:name-title">Mdlle.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Mlles\.", r"""<abbr epub:type="z3998:name-title">Mlles.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Messrs\.", r"""<abbr epub:type="z3998:name-title">Messrs.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Messers\.", r"""<abbr epub:type="z3998:name-title">Messers.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Vv])ol(s?)\.", r"<abbr>\1ol\2.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Cc])hap\. ([0-9])", r"<abbr>\1hap.</abbr> \2", xhtml) # The number allows us to avoid phrases like `Hello, old chap.`
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>)|\.)(P\.(?:P\.)?S\.(?:S\.)?\B)", r"""<abbr epub:type="z3998:initialism">\1</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Co\.", r"<abbr>Co.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Inc\.", r"<abbr>Inc.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Ltd\.", r"<abbr>Ltd.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))St\.", r"<abbr>St.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Gg])ov\.", r"<abbr>\1ov.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Col\.", r"""<abbr epub:type="z3998:name-title">Col.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))MS(S?)\.", r"""<abbr>MS\1.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Vv])iz\.", r"<abbr>\1iz.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))etc\.", r"<abbr>etc.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))inst\.", r"""<abbr xml:lang="la">inst.</abbr>""", xhtml) # `inst.` is short for `instante mense` but it is not italicized
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Cc])f\.", r"<abbr>\1f.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))ed\.", r"<abbr>ed.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))(Jan\.|Feb\.|Mar\.|Apr\.|Jun\.|Jul\.|Aug\.|Sep\.|Sept\.|Oct\.|Nov\.|Dec\.)", r"<abbr>\1</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))No\.(\s+[0-9]+)", r"<abbr>No.</abbr>\1", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Vv])s\.", r"<abbr>\1s.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Ff])f\.", r"<abbr>\1f.</abbr>", xhtml) # ff. typically used in footnotes, means "and following"
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Ll])ib\.", r"<abbr>\1ib.</abbr>", xhtml) # Lib. = Liber = Book
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Ii])\.e\.", r"""<abbr epub:type="z3998:initialism">\1.e.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([Ee])\.g\.", r"""<abbr epub:type="z3998:initialism">\1.g.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))\bN\.?B\.\B", r"""<abbr epub:type="z3998:initialism">N.B.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))Ph\.?\s*D\.?", r"""<abbr epub:type="z3998:name-title">Ph. D.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))(?:IOU(?:\.|\b)|I\.O\.U\.)", r"""<abbr epub:type="z3998:initialism">I.O.U.</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))\b([1-4]D)\b", r"""<abbr epub:type="z3998:initialism">\1</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))(Thos\.|Jas\.|Chas\.|Wm\.)", r"""<abbr epub:type="z3998:given-name">\1</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([ap])\.\s?m\.", r"<abbr>\1.m.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([0-9]{1,2})\s?[Aa]\.?\s?[Mm](?:\.|\b)", r"\1 <abbr>a.m.</abbr>", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))([0-9]{1,2})\s?[Pp]\.?\s?[Mm](?:\.|\b)", r"\1 <abbr>p.m.</abbr>", xhtml)
	# this should be placed after the am/pm test, to prevent tagging just the p. in "p. m."
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))p(p?)\.([\s0-9])", r"<abbr>p\1.</abbr>\2", xhtml)
	# keep a period after TV that terminates a clause
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))T\.?V\.([”’]?</p>|\s+[“‘]?[\p{Uppercase_Letter}])", r"""<abbr epub:type="z3998:initialism">TV</abbr>.\1""", xhtml)
	# otherwise, get rid of any periods in TV
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))(?:TV\b|T\.V\.\B)", r"""<abbr epub:type="z3998:initialism">TV</abbr>""", xhtml)
	# keep a period after AD/BC that terminates a clause
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))A\.?D\.([”’]?</p>|\s+[“‘]?[\p{Uppercase_Letter}])", r"""<abbr epub:type="se:era">AD</abbr>.\1""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))B\.?C\.([”’]?</p>|\s+[“‘]?[\p{Uppercase_Letter}])", r"""<abbr epub:type="se:era">BC</abbr>.\1""", xhtml)
	# otherwise, get rid of any periods in AD/BC
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))(?:AD\b|A\.D\.\B)", r"""<abbr epub:type="se:era">AD</abbr>""", xhtml)
	xhtml = regex.sub(r"(?<!(?:\.|\B|\<abbr[^>]*?\>))(?:BC\b|B\.C\.\B)", r"""<abbr epub:type="se:era">BC</abbr>""", xhtml)

	# Wrap £sd shorthand
	xhtml = regex.sub(r"([0-9½¼¾⅙⅚⅛⅜⅝⅞]+)([sd]\.)", r"\1<abbr>\2</abbr>", xhtml)

	# add eoc (End Of Clause) class
	xhtml = regex.sub(r"<abbr>etc\.</abbr>([”’]?(?:</p>|\s+[“‘]?[\p{Uppercase_Letter}]))", r"""<abbr class="eoc">etc.</abbr>\1""", xhtml)
	xhtml = regex.sub(r"""<abbr( epub:type="[^"]+")?>([^<]+\.)</abbr>([”’]?</p>)""", r"""<abbr class="eoc"\1>\2</abbr>\3""", xhtml)

	# We may have added eoc classes twice, so remove duplicates here
	xhtml = regex.sub(r"""<abbr class="(.*) eoc(\s+eoc)+">""", r"""<abbr class="\1 eoc">""", xhtml)

	# Clean up nesting errors
	xhtml = regex.sub(r"""<abbr class="eoc"><abbr>([^<]+)</abbr></abbr>""", r"""<abbr class="eoc">\1</abbr>""", xhtml)
	xhtml = regex.sub(r"""class="eoc eoc""", r"""class="eoc""", xhtml)

	# Get Roman numerals >= 2 characters
	# We only wrap these if they're standalone (i.e. not already wrapped in a tag) to prevent recursion in multiple runs
	# Ignore "numerals" followed by a dash, as they are more likely something like `x-ray` or `v-shaped`
	# Note that `j` may occur only at the end of a numeral as an old-fashioned terminal `i`, like int `ij` (2), `vij` (7)
	xhtml = regex.sub(r"([^\p{Letter}>])([ixvIXV]{2,}j?)(\b[^\-]|st\b|nd\b|rd\b|th\b)", r"""\1<span epub:type="z3998:roman">\2</span>\3""", xhtml)

	# Get Roman numerals that are X or V and single characters. We can't do I for obvious reasons.
	xhtml = regex.sub(r"""([^\p{Letter}>\"])([vxVX])(\b[^\-]|st\b|nd\b|rd\b|th\b)""", r"""\1<span epub:type="z3998:roman">\2</span>\3""", xhtml)

	# We can assume a lowercase i is always a Roman numeral unless followed by ’
	xhtml = regex.sub(r"""([^\p{Letter}<>/\"])i\b(?!’)""", r"""\1<span epub:type="z3998:roman">i</span>""", xhtml)

	# Fix obscured names starting with I, V, or X
	xhtml = regex.sub(fr"""<span epub:type="z3998:roman">([IVX])</span>{se.WORD_JOINER}⸺""", fr"""\1{se.WORD_JOINER}⸺""", xhtml)

	# Add abbrevations around some SI measurements
	xhtml = regex.sub(r"([0-9]+)\s*([cmk][mgl])\b", fr"\1{se.NO_BREAK_SPACE}<abbr>\2</abbr>", xhtml)

	# Add abbrevations around Imperial measurements
	xhtml = regex.sub(r"(?<![\$£0-9,])([0-9½¼⅙⅚⅛⅜⅝⅞]+)\s*(ft|yd|mi|pt|qt|gal|oz|lbs)\.?\b", fr"\1{se.NO_BREAK_SPACE}<abbr>\2.</abbr>", xhtml)

	# Handle `in.` separately to require a period, because with an optional period there are too many false positives
	xhtml = regex.sub(r"(?<![\$£0-9,])([0-9½¼⅙⅚⅛⅜⅝⅞]+)\s*in\.(\b|\s)", fr"\1{se.NO_BREAK_SPACE}<abbr>in.</abbr>", xhtml)

	# Fix some possible errors introduced by the above
	xhtml = regex.sub(fr"((?:[Nn]o\.|[Nn]umber)\s[0-9]+){se.NO_BREAK_SPACE}<abbr>in\.</abbr>", r"\1 in", xhtml)

	# Tweak some other Imperial measurements
	xhtml = regex.sub(r"([0-9]+)\s*m\.?p\.?h\.?", fr"\1{se.NO_BREAK_SPACE}<abbr>mph</abbr>", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([0-9]+)\s*h\.?p\.?", fr"\1{se.NO_BREAK_SPACE}<abbr>hp</abbr>", xhtml, flags=regex.IGNORECASE)

	# We may have added HTML tags within title tags. Remove those here
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

	# Add a full stop to sentences that don’t end in punctuation
	# This is primarily for free-form poetry like Mina Loy’s, where the
	# reading score can end up being extremely low without this.
	xhtml = regex.sub(r"([A-Za-z])(<\/span>\n)*\s*</p>", r"\1.\2</p>", xhtml)

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
	xhtml = regex.sub(r"<title[^>]*?>.+?</title>", " ", xhtml)
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

	This function excludes ", ', &, >, and < (&amp;, &lt;, and &gt;), since
	un-escaping them would create an invalid document.
	"""

	entity = match_object.group(0).lower()

	retval = entity

	# Explicitly whitelist the six (nine) essential character references
	try:
		if entity in ["&gt;", "&lt;", "&amp;", "&quot;", "&apos;", "&#62;", "&#60;", "&#38;", "&#x3e;", "&#x3c;", "&#x26;"]:
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
				if (child.tail and not regex.match(r"^[\n\t ]+$", child.tail)):
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

		# Remove line wraps and extra whitespace from child text (except meta tags)
		if child.text and not regex.match(r"^[\n\t ]+$", child.text):
			if child.tag is etree.Comment:
				child.text = regex.sub(r" *\n[\n\t ]*", child_indentation, child.text)
			elif child.tag != "{http://www.idpf.org/2007/opf}meta":
				_unwrap_text(child, remove_trailing_space=True)
				child.text = regex.sub(r"[\t ]+", " ", child.text)

		# Handle different cases for indentation in child tail content
		if not child.tail or regex.match(r"^[\n\t ]+$", child.tail):
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
				if not child.tail or next_child.tag == "{http://www.w3.org/1999/xhtml}br":
					child.tail = ""
				else:
					child.tail = " "
			else:
				child.tail = child_indentation
		else:
			# Remove line wraps and extra whitespace in child tail
			_unwrap_tail(child, remove_trailing_space=next_child is None)
			child.tail = regex.sub(r"[\t ]+", " ", child.tail)
			# Add special indentation for br tag with non-empty tail
			if child.tag == "{http://www.w3.org/1999/xhtml}br":
				child_indentation = indentations[level - 1]
				child.tail = child_indentation + child.tail

def _unwrap_text(elem: etree.Element, remove_trailing_space: bool):
	"""
	Remove line wraps from text content of element.
	"""
	elem.text = regex.sub(r"^\n[\n\t ]*", "", elem.text)
	if remove_trailing_space:
		elem.text = regex.sub(r"\n[\n\t ]*$", "", elem.text)
	elem.text = regex.sub(r" *\n[\n\t ]*", " ", elem.text)

def _unwrap_tail(elem: etree.Element, remove_trailing_space: bool):
	"""
	Remove line wraps from tail content of element.
	"""
	if elem.tag == "{http://www.w3.org/1999/xhtml}br":
		elem.tail = regex.sub(r"^\n[\n\t ]*", "", elem.tail)
	else:
		elem.tail = regex.sub(r"^\n[\n\t ]*", " ", elem.tail)
	if remove_trailing_space:
		elem.tail = regex.sub(r"\n[\n\t ]*$", "", elem.tail)
	elem.tail = regex.sub(r" *\n[\n\t ]*", " ", elem.tail)

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
			indent = node.xpath("./preceding-sibling::text()[1]")[0].replace("\n", "")

			# Indent the CSS one level deeper than the <style> element
			css = "".join(indent + "\t" + line + "\n" for line in css.splitlines())
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

	# huge_tree allows XML files of arbitrary size, like Ulysses S. Grant
	custom_parser = etree.XMLParser(huge_tree=True)
	tree = etree.fromstring(str.encode(xml), parser=custom_parser)
	canonical_bytes = etree.tostring(tree, method="c14n")
	tree = etree.fromstring(canonical_bytes, parser=custom_parser)
	_indent(tree, space="\t")

	# Remove white space around attribute values
	for node in tree.xpath("//*[attribute::*[re:test(., '^\\s+') or re:test(., '\\s+$')]]", namespaces={"re": "http://exslt.org/regular-expressions"}):
		for attribute in node.keys():
			value = node.get(attribute)
			value = regex.sub(r"^\s+", "", value)
			value = regex.sub(r"\s+$", "", value)
			node.set(attribute, value)

	return tree

def _xml_tree_to_string(tree: etree.ElementTree, doctype: Optional[str] = None) -> str:
	"""
	Given an XML etree, return a string representing the etree's XML.

	INPUTS
	tree: An XML etree.

	OUTPUTS
	A string representing the etree's XML.
	"""

	xml = """<?xml version="1.0" encoding="utf-8"?>\n""" + etree.tostring(tree, encoding="unicode", doctype=doctype) + "\n"

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

	# Pull out the doctype if there is one, as etree seems to eat it
	doctypes = regex.search(r"<!doctype[^>]+?>", xml, flags=regex.IGNORECASE)

	return _xml_tree_to_string(tree, doctypes.group(0) if doctypes else None)

def format_xhtml(xhtml: str) -> str:
	"""
	Pretty-print well-formed XHTML.

	INPUTS
	xhtml: A string of well-formed XHTML

	OUTPUTS
	A string of pretty-printed XHTML.
	"""

	namespaces = {"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops", "re": "http://exslt.org/regular-expressions"} # re enables regular expressions in xpath

	# Epub3 doesn't allow named entities, so convert them to their unicode equivalents
	# But, don't unescape the metadata file long-description accidentally
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
	for node in tree.xpath("//*[attribute::*[re:test(local-name(), '[A-Z]')]]", namespaces=namespaces):
		for key, value in node.items(): # Iterate over attributes
			node.attrib.pop(key) # Remove the attribute
			node.attrib[key.lower()] = value # Re-add the attribute, lowercased

	# Sort classes alphabetically, except the "eoc" class always comes last
	for node in tree.xpath("//*[re:test(@class, '\\s')]", namespaces=namespaces):
		# Sort class elements
		classes = regex.split(r"\s+", node.get("class"))
		classes = sorted(classes, key=str.lower)

		# Move eoc to the end, if it exists
		if "eoc" in classes:
			classes += [classes.pop(classes.index("eoc"))]

		# Set the new class value
		node.set("class", " ".join(classes))

	# Lowercase tag names
	for node in tree.xpath("//*[re:test(local-name(), '[A-Z]')]", namespaces=namespaces):
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

		# Make some easy fixes
		xhtml = regex.sub(r"<p>\s+", "<p>", xhtml)
		xhtml = regex.sub(r"\s+</p>", "</p>", xhtml)

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

			if token.lower_value == "currentcolor": # special case
				output += "currentColor"
			else:
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
			elif token.value in ("<", ">", "+", "-", "/"):
				output += " " + token.value + " "
			elif token.value in ("|", "|=", "^=", "~=", "*=", "||"):
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

	# Removing spaces after : may mess up media queries like:
	# `@media all and (prefers-color-scheme: dark)` -> `@media all and (prefers-color-scheme:dark)`
	# Here we try to re-add spaces after a : if it's within a paren block.
	# We could do this during parsing but we would need to peek ahead to the next item in the loop which
	# is too much trouble right now.
	output = regex.sub(r"\(([^\"\s]+?):([^\"\s]+?)", r"(\1: \2", output)

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

	tokens = tinycss2.parse_declaration_list(content)

	# Hold on to your butts...
	# When we alpha-sort declarations, we want to keep comments that are on the same
	# line attached to that declaration after it's reordered.
	# To do this, first create a list of sorted_declarations that is list of tuples.
	# The first tuple value is the declaration itself, and the second is a comment on the same line, if it exists.
	# While we do this, remove those same-line comments from our master list of tokens,
	# so that we don't process them twice later when we iterate over the master list again.
	sorted_declarations = []
	i = 0
	while i < len(tokens):
		if tokens[i].type == "declaration":
			if i + 1 < len(tokens) and tokens[i + 1].type == "comment":
				sorted_declarations.append((tokens[i], tokens[i + 1]))
				tokens.pop(i + 1) # Remove from the master list

			# Use regex to test if the token is on the same line, i.e. if the intervening white space doesn't include a newline
			elif i + 2 < len(tokens) and tokens[i + 1].type == "whitespace" and regex.match(r"[^\n]+", tokens[i + 1].value) and tokens[i + 2].type == "comment":
				sorted_declarations.append((tokens[i], tokens[i + 2]))
				tokens.pop(i + 1) # Remove from the master list
				tokens.pop(i + 1)

			else:
				# Special case in alpha-sorting: Sort -epub-* properties as if -epub- didn't exist
				# Note that we modify token.name, which DOESN'T change token.lower_name; and we use token.name
				# for sorting, but token.lower_name for output, so we don't have to undo this before outputting
				tokens[i].name = regex.sub(r"^-([a-z]+?)-(.+)", r"\2-\1-\2", tokens[i].name)
				sorted_declarations.append((tokens[i], None))

		i = i + 1

	# Actually sort declaration tokens and their associated comments, if any
	sorted_declarations.sort(key = lambda x : x[0].name)

	# Now, sort the master token list using an intermediary list, output_tokens
	# This will iterate over all tokens, including non-declaration tokens. If we encounter a declaration,
	# pull the nth declaration out of our sorted list instead.

	output_tokens = []
	current_declaration_number = 0
	for token in tokens:
		if token.type == "error":
			raise se.InvalidCssException("Couldn’t parse CSS. Exception: {token.message}")

		# Append the declaration to the output based on its sorted index.
		# This will sort declarations but keep things like comments before and after
		# declarations in the expected order.
		if token.type == "declaration":
			output_tokens.append(sorted_declarations[current_declaration_number])
			current_declaration_number = current_declaration_number + 1
		else:
			output_tokens.append((token, None))

	# tokens is now a alpha-sorted list of tuples of (token, comment)
	tokens = output_tokens

	for token in tokens:
		comment = None
		if isinstance(token, tuple):
			comment = token[1]
			token = token[0]

		if token.type == "error":
			raise se.InvalidCssException("Couldn’t parse CSS. Exception: {token.message}")

		if token.type == "declaration":
			output += ("\t" * indent_level) + token.lower_name + ": "

			output += _format_css_component_list(token.value)

			if token.important:
				output += " !important"

			output += ";"

			if comment:
				output += " /* " + comment.value.strip() + " */"

			output += "\n"

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
	return "%d%s" % (value, "tsnrhtdd"[(math.floor(value / 10) % 10 != 1) * (value % 10 < 4) * value % 10::4]) # pylint: disable=consider-using-f-string

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

	# Replace all white space except hair spaces and non-breaking spaces with a space character
	text = regex.sub(fr"[^\S{se.HAIR_SPACE}{se.NO_BREAK_SPACE}]+", " ", text)

	text = pip_titlecase(text)

	# We make some additional adjustments here

	# Lowercase HTML tags that titlecase might have screwed up. We just lowercase the entire contents of the tag, including attributes,
	# since they're typically lowercased anyway. (Except for things like `alt`, but we won't be titlecasing images!)
	text = regex.sub(r"<(/?)([^>]+?)>", lambda result: "<" + result.group(1) + result.group(2).lower() + ">", text)

	# Uppercase Roman numerals, but only if they are valid Roman numerals and they are not `MIX` (which is much more likely to be an English word than a Roman numeral)
	# or `DI` which may be an Italian word. May be preceded by a space or parenthesis.
	try:
		text = regex.sub(r"([\s\(])([ivxlcdm]+)(\b)", lambda result: result.group(1) + result.group(2).upper() + result.group(3) if result.group(2).upper() not in ("MIX", "DI") and roman.fromRoman(result.group(2).upper()) else result.group(1) + result.group(2), text, flags=regex.IGNORECASE)
	except roman.InvalidRomanNumeralError:
		pass

	# Lowercase `and`, `or` even if preceded by punctuation
	text = regex.sub(r"([^\p{Letter}]) (And|Or)\b", lambda result: result.group(1) + " " + result.group(2).lower(), text)

	# pip_titlecase capitalizes *all* prepositions preceded by parenthesis; we only want to capitalize ones that *aren't the first word of a subtitle*
	# OK: From Sergeant Bulmer (of the Detective Police) to Mr. Pendril
	# OK: Three Men in a Boat (To Say Nothing of the Dog)
	text = regex.sub(r"\((For|Of|To)(.*?)\)(.+?)", lambda result: "(" + result.group(1).lower() + result.group(2) + ")" + result.group(3), text)

	# Uppercase words preceded by en or em dash
	text = regex.sub(fr"([—–]{se.WORD_JOINER}?)([\p{{Lowercase_Letter}}])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Lowercase `and`, if it's not the very first word, and not preceded by an em-dash
	text = regex.sub(r"(?<!^)\b(And|Nor)\b", lambda result: result.group(1).lower(), text)

	# Lowercase `the`, if preceded by a dash (like `Puss-in-Boots` or `Jack-in-the-Box`)
	text = regex.sub(r"\b(-)(In|The|Sur|Of|Au)\b", lambda result: result.group(1) + result.group(2).lower(), text)

	# Lowercase "in", if followed by a semicolon (but not words like "inheritance")
	text = regex.sub(r"\b; In\b", "; in", text)

	# Lowercase `th’`, sometimes used poetically
	text = regex.sub(r"\b Th’ \b", " th’ ", text)

	# Lowercase `o’`
	text = regex.sub(r" O’ ", " o’ ", text)

	# Uppercase words that begin compound words, like `to-night` (which might appear in poetry)
	text = regex.sub(r" ([\p{Lowercase_Letter}])([\p{Lowercase_Letter}]+\-)", lambda result: " " + result.group(1).upper() + result.group(2), text)

	# Lowercase `from`, `with`, as long as they're not the first word and not preceded by a parenthesis
	text = regex.sub(r"(?<!^)(?<!\()\b(From|With)\b", lambda result: result.group(1).lower(), text)

	# Capitalise the first word after an opening quote or italicisation that signifies a work
	text = regex.sub(r"(‘|“|<i.*?epub:type=\".*?se:.*?\".*?>)([\p{Lowercase_Letter}])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Lowercase `the` if preceded by `vs.`
	text = regex.sub(r"(?:vs\.) The\b", "vs. the", text)

	# Lowercase `de`, `von`, `van`, `le`, `du` as in `Charles de Gaulle`, `Werner von Braun`, etc., and if not the first word and not preceded by an &ldquo;
	text = regex.sub(r"(?<!^|“)\b(Von|Van Der|Van|Le|\b[aA] La|\b[àÀ] La|Des|De La|De|Du|Di|Del)\b", lambda result: result.group(1).lower(), text)

	# Uppercase word following `Or,`, since it is probably a subtitle
	text = regex.sub(r"\bOr, ([\p{Lowercase_Letter}])", lambda result: "Or, " + result.group(1).upper(), text)

	# Uppercase word following `:`, except `or, `, which indicates a kind of subtitle
	text = regex.sub(r": ([\p{Lowercase_Letter}])(?!r, )", lambda result: ": " + result.group(1).upper(), text)

	# Uppercase words after an initial contraction, like `O'Keefe` or `L'Affaire`. But only if there's at least 3 letters
	# after, to prevent catching things like `I'm` or `E're`
	text = regex.sub(r"\b([\p{Uppercase_Letter}]’)([\p{Lowercase_Letter}])([\p{Letter}]{2,})", lambda result: result.group(1) + result.group(2).upper() + result.group(3), text)

	# Uppercase letter after `Mc`
	text = regex.sub(r"\bMc([\p{Lowercase_Letter}])", lambda result: "Mc" + result.group(1).upper(), text)

	# Uppercase first letter after beginning contraction
	text = regex.sub(r"(\s|^)(’[\p{Lowercase_Letter}])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Uppercase first letter
	text = regex.sub(r"^(\p{Lowercase_Letter}])", lambda result: result.group(1).upper(), text)

	# Lowercase `by`
	text = regex.sub(r"(\s)By(\s|%)", lambda result: result.group(1) + "by" + result.group(2), text)

	# Lowercase leading `d’`, as in `Marie d’Elle`
	text = regex.sub(r"(?:\b|^)D’([\p{Letter}])", lambda result: "d’" + result.group(1).upper(), text)

	# # Uppercase letter after leading `L'`, as in `L'Affaire`
	# text = regex.sub(r"(?:\b|^)L’([\p{Letter}])", lambda result: "L’" + result.group(1).upper(), text)

	# Uppercase `l’` as in `l’Affaire`, but not if it's a the first letter
	text = regex.sub(r"(?<!^)L’([\p{Letter}])", lambda result: "l’" + result.group(1), text)

	# Uppercase leading `A-` as in `A-Breaking`
	text = regex.sub(r"(\s)a\-([\p{Uppercase_Letter}])", lambda result: result.group(1) + "A-" + result.group(2), text)

	# Uppercase some known initialisms
	text = regex.sub(r"(\s|^)(sos|md)(?:\b|$)", lambda result: result.group(1) + result.group(2).upper(), text, flags=regex.IGNORECASE)
	text = regex.sub(r"(\s)(bc|ad)(?:\b|$)", lambda result: result.group(1) + result.group(2).upper(), text, flags=regex.IGNORECASE)

	# Lowercase `À` (as in `À La Carte`) unless it's the first word
	text = regex.sub(r"(?<!^)\bÀ\b", "à", text)

	# Uppercase initialisms
	text = regex.sub(r"\b(([\p{Letter}]\.)+)", lambda result: result.group(1).upper(), text)

	# Uppercase No. as in Number
	text = regex.sub(r"\b(no\.\s+)", lambda result: result.group(1).upper(), text)

	# Lowercase V. as in versus in a legal case
	text = regex.sub(r"\b(V\.\s+)", lambda result: result.group(1).lower(), text)

	# Lowercase `mm` (millimeters, as in `50 mm gun`) unless it's followed by a period in which case it's likely `Mm.` (Monsieurs)
	text = regex.sub(r"(\s)MM(\s|$)", r"\1mm\2", text)

	# Lowercase `al-` (as in the Arabic definite article) unless it’s the first word
	text = regex.sub(r"(?<!^)\bAl-", "al-", text)

	# Fix html entities
	text = text.replace("&Amp;", "&amp;")

	# Lowercase etc.
	text = text.replace("Etc.", "etc.")

	# Lowercase some special cases.
	text = text.replace("A.B.C. Of", "A.B.C. of")
	text = regex.sub(r"((A|P)\.M\.) To", r"\1 to", text)

	# More special cases
	text = regex.sub(r"des Moines", "Des Moines", text)

	# Like `Will-o’-the-Wisp`
	text = regex.sub(r"(?<=-)(O’|The)-", lambda result: result.group(1).lower() + "-", text)

	# Fix non-breaking spaces - we can assume that they’re intentionally used in names
	# If `titlecase` is fixed we can remove this, see https://github.com/ppannuto/python-titlecase/issues/95
	text = regex.sub(fr"{se.NO_BREAK_SPACE}([a-z])", lambda result: " " + result.group(1).upper(), text)

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
	text = unidecode(text)

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

	# First, remove periods from epub:type.	 We can't remove periods in the entire selector because there might be class selectors involved
	epub_type = regex.search(r"\"[^\"]+?\"", selector)
	if epub_type:
		selector = selector.replace(epub_type.group(), epub_type.group().replace(".", "-"))

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

	# Replace shorthand CSS with longhand properties, another ADE screwup
	css = regex.sub(r"margin:\s*([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\1;\n\tmargin-bottom: \\1;\n\tmargin-left: \\1;", css)
	css = regex.sub(r"margin:\s*([^\s]+?)\s+([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\2;\n\tmargin-bottom: \\1;\n\tmargin-left: \\2;", css)
	css = regex.sub(r"margin:\s*([^\s]+?)\s+([^\s]+?)\s+([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\2;\n\tmargin-bottom: \\3;\n\tmargin-left: \\2;", css)
	css = regex.sub(r"margin:\s*([^\s]+?)\s+([^\s]+?)\s+([^\s]+?)\s+([^\s]+?)\s*;", "margin-top: \\1;\n\tmargin-right: \\2;\n\tmargin-bottom: \\3;\n\tmargin-left: \\4;", css)

	# Replace some more poorly-supported CSS attributes
	css = css.replace("all-small-caps;", "small-caps;\n\ttext-transform: lowercase;")
	css = regex.sub(r"text-align:\s*initial\s*;", "text-align: left;", css)

	# Include `all and` in @media queries, otherwise RMSDK will dump the entire stylesheet
	css = regex.sub(r"@media\s*\(", "@media all and (", css)

	# Replace CSS namespace selectors with classes
	# For example, p[epub|type~="z3998:salutation"] becomes p.epub-type-z3998-salutation
	for line in regex.findall(r"\[[a-z]+\|[a-z]+(?:\~\=\"[^\"]*?\")?\]", css):
		fixed_line = namespace_to_class(line)
		css = css.replace(line, fixed_line)

	return css


def generate_title(xhtml: Union[str, EasyXmlTree]) -> str:
	"""
	Generate the value for the <title> tag of a string of XHTML, based on the rules in the SE manual.

	INPUTS
	xhtml: A string of XHTML

	OUTPUTS
	A string representing the title for the document
	"""

	try:
		if isinstance(xhtml, str):
			dom = EasyXmlTree(xhtml)
		else:
			dom = deepcopy(xhtml)
	except Exception as ex:
		raise se.InvalidXhtmlException(f"Couldn’t parse XHTML file. Exception: {ex}")

	# Titlepages are the exception
	if dom.xpath("/html/body//section[re:test(@epub:type, '\\btitlepage\\b')]"):
		return "Titlepage"

	title = ""

	# Do we have an hgroup element in the first <section> or <article> to process?
	# Only match hgroups that do not have a ancestor containing an h# or header (which presumably contains an h# element). Note
	# how we exclude <header>s that contain an <hgroup> otherwise we would match ourselves!
	hgroup_elements = dom.xpath("/html/body/*[re:test(name(), '(article|section|nav)')][1]//hgroup[not(ancestor::*[./*[re:test(name(), '^h[1-6]$') or (name() = 'header' and not(./hgroup))]])]")
	if hgroup_elements:
		hgroup_element = hgroup_elements[0]

		# Strip any endnote references first
		for node in hgroup_element.xpath("//*[contains(@epub:type, 'noteref')]"):
			node.remove()

		closest_parent_sections = hgroup_element.xpath("./ancestor::*[name() = 'section' or name() = 'article'][1]")

		if closest_parent_sections:
			closest_parent_section = closest_parent_sections[0]
		else:
			raise se.InvalidSeEbookException("No [xhtml]<section>[/] or [xhtml]<article>[/] element for [xhtml]<hgroup>[/].")

		# If the closest parent <section> or <article> is a part, division, or volume, then keep all <hgroup> children
		closest_parent_section_epub_type = closest_parent_section.get_attr("epub:type")
		if not closest_parent_section_epub_type or (closest_parent_section_epub_type and ("part" not in closest_parent_section_epub_type and "division" not in closest_parent_section_epub_type and "volume" not in closest_parent_section_epub_type)):
			# Else, if the closest parent <section> or <article> is a halftitlepage, then discard <hgroup> subtitles
			if closest_parent_section_epub_type and "halftitlepage" in closest_parent_section_epub_type:
				for node in hgroup_element.xpath("./*[contains(@epub:type, 'subtitle')]"):
					node.remove()

			# Else, if the first child of the <hgroup> is a title, then also discard <hgroup> subtitles
			# Note the concat() so that matching for `title` doesn't match `subtitle`
			elif hgroup_element.xpath("./*[1][contains(concat(' ', @epub:type, ' '), ' title ')]"):
				for node in hgroup_element.xpath("./*[contains(@epub:type, 'subtitle')]"):
					node.remove()

		# Then after processing <hgroup>, the title becomes the 1st <hgroup> child;
		# if there is a 2nd <hgroup> child after processing, add a colon and space, then the text of the 2nd <hgroup> child.
		try:
			title = regex.sub(r"\s+", " ", hgroup_element.xpath("./*[1]")[0].inner_text())
		except Exception as ex:
			raise se.InvalidSeEbookException("Couldn’t find title in [xhml]<hgroup>[/].") from ex

		subtitle = hgroup_element.xpath("./*[2]")
		if subtitle:
			subtitle_text = subtitle[0].inner_text()
			title += f": {subtitle_text}"

	else:
		# No hgroups, so try to find the first h# element. The title becomes that element's inner text.
		h_elements = dom.xpath("/html/body/*[re:test(name(), '(article|section|nav)')][1]//*[re:test(name(), '^h[1-6]')][1]")

		if h_elements:
			h_element = h_elements[0]

			# Strip any endnote references first
			for node in h_element.xpath("//*[contains(@epub:type, 'noteref')]"):
				node.remove()

			title = h_element.inner_text()

		else:
			# No <h#> elements found. Try to get the title from the epub:type of the deepest <section> or <article> that has no <section> or <article> siblings. (Note the parenthesis
			# to match against `last()`).
			# This is to catch cases of <section>s nested for recomposability, so that we don't get "Part 1" instead of "Epigraph" (of part 1)
			top_level_wrappers = dom.xpath("(/html/body//*[name() = 'section' or name() = 'article' and count(preceding-sibling::*) + count(following-sibling::*) = 0])[last()]")

			if top_level_wrappers:
				top_level_wrapper = top_level_wrappers[0]

				# Only guess the title if there is a single value for epub:type
				if top_level_wrapper.get_attr("epub:type"):
					# Get the first non-namespaced value as the title
					for value in top_level_wrapper.get_attr("epub:type").split(" "):
						if value == "z3998:frontispiece":
							title = "Frontispiece"
							break

						if ":" not in value:
							title = titlecase(value.replace("-", " "))
							break

	# Remove odd spaces and word joiners
	title = regex.sub(fr"[{se.NO_BREAK_SPACE}]", " ", title)
	title = regex.sub(fr"[{se.WORD_JOINER}{se.ZERO_WIDTH_SPACE}]", "", title)

	# Collapse spaces possibly introduced by white-space nodes
	# This matches all white space EXCEPT hair space; note the double negation with uppercase \S
	# See https://stackoverflow.com/questions/3548949/how-can-i-exclude-some-characters-from-a-class
	title = regex.sub(fr"[^\S{se.HAIR_SPACE}]+", " ", title)

	# Unescape ampersands since we are returning a plain string, not XML
	title = title.replace("&amp;", "&")

	return title

def _get_flattened_children(node: EasyXmlElement, allow_header: bool) -> List[EasyXmlElement]:
	"""
	Helper function for find_unexpected_ids().

	Get a flat list of children that are not headers or sectioning elements,
	and return a list of those nodes.
	In other words, input like this:
	<section>
		<p></p>
		<blockquote>
			<p></p>
		</blockquote>
		<p></p>
	</section>

	Would result in this flat list:
	p
	blockquote
	p
	p
	"""

	result = []
	sectioning_elements = ["section", "article", "figure", "nav", "hgroup"]

	if not allow_header:
		sectioning_elements.append("header")

	for child in node.children:
		is_endnote = False
		is_glossdef = False
		if child.get_attr("epub:type"):
			is_endnote = regex.search(r"\bendnote\b", child.get_attr("epub:type"))
			is_glossdef = "glossdef" in child.get_attr("epub:type")

		if child.tag not in sectioning_elements and not is_endnote and not is_glossdef:
			result.append(child)
			result = result + _get_flattened_children(child, allow_header)

	return result

def find_unexpected_ids(dom: EasyXmlTree) -> List[Tuple[EasyXmlElement, str]]:
	"""
	Given a DOM tree, return a list of tuples containing nodes and their expected ID attributes.
	Only nodes with unexpected IDs are returned.

	INPUTS
	dom: An EasyXmlTree

	OUTPUTS
	A list of tuples of (node, expected_id)
	"""

	dom_copy = deepcopy(dom)
	replacements = []

	# Remove noterefs as they have their own ID rules
	for node in dom_copy.xpath("/html/body//*[contains(@epub:type, 'noteref')]"):
		node.remove()

	# IDs are set to `{closest_parent_sectioning_element_id}-{tag_name}-{n}`.
	# Lines of poetry are set to `{closest_poem_sectioning_element_id}-line-{n}`.
	# Notes:
	# 1. Endnotes count as their own sectioning elements for the purposes of assigning IDs
	# 2. Exclude glossaries, as IDs there should be related to the glossterm somehow
	# 3. Exclude <p> children of <hgroup> as they are really titles and not <p> per se
	line_number = 0
	endnote_number = 0
	container_poem_section_id = ""
	for section in dom_copy.xpath("/html/body//*[@id and (name() = 'section' or name() = 'article' or re:test(@epub:type, '\\bendnote\\b'))]"):
		counts: Dict[str, int] = {}
		is_poem = bool(section.xpath("./ancestor-or-self::*[contains(@epub:type, 'z3998:poem')]"))
		section_id = section.get_attr("id")
		allow_header = not is_poem

		section_epub_type = section.get_attr("epub:type")
		if section_epub_type:
			# If this section is a poem or an endnotes container, reset the counters
			if "z3998:poem" in section_epub_type:
				line_number = 0
				container_poem_section_id = section_id
				allow_header = False

			if "endnotes" in section_epub_type:
				endnote_number = 0

			# If this section is an endnote, increment the note number and check the ID right now
			if regex.search(r"\bendnote\b", section.get_attr("epub:type")):
				endnote_number = endnote_number + 1
				expected_id = f"note-{endnote_number}"

				if section_id != expected_id:
					replacements.append((section, expected_id))

		for node in _get_flattened_children(section, allow_header):
			if node.tag in counts:
				counts[node.tag] = counts[node.tag] + 1
			else:
				counts[node.tag] = 1

			# If the line is a line of poetry, increment the line count
			if is_poem and node.tag == "span" and node.parent.tag == "p":
				line_number = line_number + 1

			id_attr = node.get_attr("id")
			# If the element has an ID attribute and it's not an endnote node (i.e. <li epub:type="endnote">)
			if id_attr:
				expected_id = id_attr

				# <dt>s have an id attribute set to their defining word
				if node.tag == "dt":
					dfn = node.xpath("./dfn")
					if dfn:
						expected_id = make_url_safe(dfn[0].inner_text())

				# All other elements
				else:
					expected_id = f"{section_id}-{node.tag}-{counts[node.tag]}"

					if is_poem and node.tag == "span" and node.parent.tag == "p":
						expected_id = f"{container_poem_section_id}-line-{line_number}"

				if id_attr != expected_id:
					replacements.append((node, expected_id))

	return replacements
