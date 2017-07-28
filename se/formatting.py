#!/usr/bin/env python3

import unicodedata
import regex
import se
from titlecase import titlecase as pip_titlecase

def remove_tags(text):
	return regex.sub(r"</?([a-z]+)[^>]*?>", "", text, flags=regex.DOTALL)

def titlecase(text):
	text = pip_titlecase(text)

	# We make some additional adjustments here

	# Lowercase HTML tags that titlecase might have screwed up. We just lowercase the entire contents of the tag, including attributes,
	# since they're typically lowercased anyway. (Except for things like `alt`, but we won't be titlecasing images!)
	text = regex.sub(r"<(/?)([^>]+?)>", lambda result: "<" + result.group(1) + result.group(2).lower() + ">", text)

	# If etc. is the last word in the title, leave it lowercased
	text = regex.sub(r" Etc\.$", " etc.", text)

	# Lowercase "de" and "von", as in "Charles de Gaulle"
	text = regex.sub(r"\b(De|Von)\b", lambda result: result.group(1).lower(), text)

	# Lowercase "and", even if preceded by punctuation
	text = regex.sub(r"([^a-zA-Z]) (And|Or)", lambda result: result.group(1) + " " + result.group(2).lower(), text)

	# Lowercase "and", if followed by a word-joiner
	regex_string = r"\bAnd{}".format(se.WORD_JOINER)
	text = regex.sub(regex_string, "and{}".format(se.WORD_JOINER), text)

	# Lowercase "from", "with", as long as they're not the first word and not preceded by a parenthesis
	text = regex.sub(r"(?<!^)(?<!\()\b(From|With)\b", lambda result: result.group(1).lower(), text)

	# Lowercase "the" if preceded by "vs."
	text = regex.sub(r"(?:vs\.) The\b", "vs. the", text)

	return text

def make_url_safe(text):
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
