#!/usr/bin/env python3

import math
import unicodedata
import regex
import se
from titlecase import titlecase as pip_titlecase


def remove_tags(text: str) -> str:
	"""
	Remove all HTML tags from a string.

	INPUTS
	text: Text that may have HTML tags

	OUTPUTS
	A string with all HTML tags removed
	"""

	return regex.sub(r"</?([a-z]+)[^>]*?>", "", text, flags=regex.DOTALL)

def ordinal(number: str) -> str:
	"""
	Given an string representing an integer, return a string of the integer followed by its ordinal, like "nd" or "rd".

	INPUTS
	number: A string representing an integer like "1" or "2"

	OUTPUTS
	A string of the integer followed by its ordinal, like "1st" or "2nd"
	"""

	number = int(number)
	return "%d%s" % (number, "tsnrhtdd"[(math.floor(number / 10) % 10 != 1) * (number % 10 < 4) * number % 10::4])

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
	text = regex.sub(r"([^a-zA-Z]) (And|Or)", lambda result: result.group(1) + " " + result.group(2).lower(), text)

	# pip_titlecase capitalizes *all* prepositions preceded by parenthesis; we only want to capitalize ones that *aren't the first word of a subtitle*
	# OK: From Sergeant Bulmer (of the Detective Police) to Mr. Pendril
	# OK: Three Men in a Boat (To Say Nothing of the Dog)
	text = regex.sub(r"\((For|Of|To)(.*?)\)(.+?)", lambda result: "(" + result.group(1).lower() + result.group(2) + ")" + result.group(3), text)

	# Lowercase "and", if followed by a word-joiner
	regex_string = r"\bAnd{}".format(se.WORD_JOINER)
	text = regex.sub(regex_string, "and{}".format(se.WORD_JOINER), text)

	# Lowercase "in", if followed by a semicolon
	text = regex.sub(r"\b; In", "; in", text)

	# Lowercase "from", "with", as long as they're not the first word and not preceded by a parenthesis
	text = regex.sub(r"(?<!^)(?<!\()\b(From|With)\b", lambda result: result.group(1).lower(), text)

	# Capitalise the first word after an opening quote or italicisation that signifies a work
	text = regex.sub(r"(‘|“|<i.*?epub:type=\".*?se:.*?\".*?>)([a-z])", lambda result: result.group(1) + result.group(2).upper(), text)

	# Lowercase "the" if preceded by "vs."
	text = regex.sub(r"(?:vs\.) The\b", "vs. the", text)

	# Lowercase "de", "von", "van", "le", as in "Charles de Gaulle", "Werner von Braun", etc., and if not the first word
	text = regex.sub(r"(?<!^)\b(De|Von|Van|Le)\b", lambda result: result.group(1).lower(), text)

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

	#1. Convert accented characters to unaccented characters
	text = regex.sub(r"\p{M}", "", unicodedata.normalize("NFKD", text))

	#2. Trim
	text = text.strip()

	#3. Convert title to lowercase
	text = text.lower()

	#4. Remove apostrophes
	text = text.replace("'", "")

	#5. Convert any non-digit, non-letter character to a space
	text = regex.sub(r"[^0-9a-z]", " ", text, flags=regex.IGNORECASE)

	#6. Convert any instance of one or more space to a dash
	text = regex.sub(r"\s+", "-", text)

	#7. Remove trailing dashes
	text = regex.sub(r"\-+$", "", text)

	return text
