#!/usr/bin/env python3

import unicodedata
import regex

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
